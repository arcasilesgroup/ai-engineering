---
spec: spec-148
title: Files-only persistence + obvious-by-default conventions
status: approved
effort: large
summary: "Retire embedded SQLite (state.db) entirely for files-only persistence (JSON records, append-only hash-chained NDJSON audit, Markdown docs), and land the remaining obvious-by-default conventions carried from spec-147 (de-collided skill triggers, one branch-cleanup, deterministic STOP + method-tagged findings, CI-enforced §10.x/naming/suppression DEC-binding, dry-run destructive verbs). Supersedes spec-147 Waves 2b-5; all on PR #532."
supersedes: [spec-147 D-147-09, spec-147 D-147-10, spec-147 D-147-11, spec-147 D-147-12, spec-147 D-147-13, spec-147 D-147-14, spec-147 D-147-15, spec-147 D-147-16, spec-147 D-147-17]
---

# Spec 148 — Files-only persistence + obvious-by-default conventions

## Summary

Two threads land together on PR #532, both serving the "obvious by default" thesis. **(A) Files-only persistence:** `ai-engineering`'s embedded SQLite `state.db` (11 tables, 9 migrations) is over-engineering for its scale — kilobyte data, single-writer, read-whole, mtime-cached — and a cross-OS hot-path liability (Windows WAL holds locks beyond `close()`; two hooks read `state.db` live). Six of eleven tables are already derived/dead/orphaned; the rest already have file counterparts (`decision-store.json`, `ownership-map.json` is even read first today, `framework-events.ndjson`, `gate-findings.json`). This spec retires `state.db` entirely: each datum gets one file SoT (JSON / append-only hash-chained NDJSON / Markdown), the migration runner and `state_db.py` are deleted, and the SQLite-backed `audit query`/`index` are dropped (rollups recomputed over NDJSON). **(B) Obvious-by-default conventions** carried from spec-147 (its Waves 3-5, never executed): de-collide colliding skill triggers, collapse to one branch-cleanup, make the quality-loop STOP deterministic + tag findings by method, and CI-enforce §10.x citation / naming grammar / suppression DEC-binding with dry-run-by-default destructive verbs. This spec supersedes spec-147 Waves 2b-5; spec-147 keeps only its shipped Waves 1 + 2a (on #532).

## Goals

- **G1 — No SQLite anywhere.** `state.db`, `state_db.py`, the migration runner, and migrations `0001`–`0008` are deleted; no framework code imports `sqlite3`. CI asserts the absence.
- **G2 — One file SoT per datum.** decisions → `decision-store.json`; ownership → `ownership-map.json`; risk → decision records (the `risk_acceptances` table is dead, zero writers); install → `install-state.json` (writable, = current `InstallState` Pydantic dump); tool capabilities → `framework-capabilities.json` (rebuilt on demand); events → `framework-events.ndjson`; gate findings → `gate-findings.json`. No dual-write, no derived SQLite cache.
- **G3 — Tamper-evidence stays in the file.** The SHA-256 hash chain lives inside `decision-store.json` and `framework-events.ndjson`; `ai-eng audit verify` verifies both file chains. No SQL table is needed for integrity.
- **G4 — Hooks read files, not SQLite.** `runtime-stop.py`, `runtime-session-end.py`, `session_bootstrap.py` (+ templates) drop all `sqlite3`/`state.db` access; rollups/counts come from NDJSON / JSON. Removes the Windows-WAL hot-path liability.
- **G5 — `audit` reshaped, not broken.** `audit query` + `audit index` removed; `audit tokens`/`replay`/`otel-export` reimplemented as NDJSON scans; `audit verify` unchanged. Existing installs migrate once (export → verify → delete `state.db`).
- **G6 — One obvious surface per task.** No skill trigger phrase routes ambiguously; exactly one branch-cleanup implementation; surface count unchanged (no folds).
- **G7 — Deterministic "done".** The quality-loop STOP verdict is reproducible for an identical diff; every `/ai-verify` finding is tagged `method: deterministic|llm`.
- **G8 — Conventions enforced, not hoped.** CI enforces §10.x citation in skill Workflows, a documented naming grammar, and suppression DEC-binding; destructive CLI verbs default to dry-run/confirm.
- **G9 — Truthful docs + clean reversal.** `docs/persistence-doctrine.md` rewritten to files-only; every `state.db` reference in CLAUDE.md/CANONICAL.md + ~26 skills + ~6 agents updated; mirrors regenerated. Every hard-delete/behavior change in CHANGELOG; no shims; the reversal of spec-123/125/132 is explicit.

## Non-Goals

- **No change to the event NDJSON schema or the hash-chain algorithm** — only storage changes (drop the SQLite `events` projection; keep the NDJSON SoT + `compute_entry_hash`).
- **No removal of Tier-3 config files** (`manifest.yml`, `hooks-manifest.json`, `gate-findings.json`, `suppression-allowlist.yml`).
- **No new query DSL** to replace arbitrary `audit query` SQL — dropped; only fixed NDJSON rollups survive.
- **No skill folds/deletes/new surfaces** — trigger collisions resolved by description edits + cross-references only (surface count stays).
- **No re-introduction of a database "for scale"** within this spec (YAGNI).
- **No touching spec-147 Waves 1/2a** (shipped on #532) — this spec supersedes only spec-147 Waves 2b-5.

## Decisions

### Part A — Files-only persistence

### D-148-01 — Retire SQLite `state.db` entirely (Option A)
Delete `state.db` + the SQLite layer (`state_db.py`, `state/migrations/`, `_runner.py`); persist all state in files (JSON / append-only NDJSON / Markdown).
**Rationale**: Flat files fit our scale (kilobyte, single-writer, read-whole, mtime-cached); SQLite only pays for concurrency/large-indexed/joins we don't have (research [1][2][8][9]) and imposes a cross-OS hot-path liability (Windows WAL, research [10][11][12]). Operator call: SQLite is premature over-engineering here.

### D-148-02 — Per-datum file homes (single SoT, no dual-write)
decisions→`decision-store.json`; ownership→`ownership-map.json` (repo already reads it first); risk→decision records (`risk_acceptances` table is dead); install→`install-state.json`; tool_capabilities→`framework-capabilities.json` (rebuilt on demand); events→`framework-events.ndjson`; gate findings→`gate-findings.json`.
**Rationale**: 6 of 11 tables already derived/dead/orphaned; the rest already have file counterparts. Files-only collapses split-brain + dual-writes to one obvious store per datum.

### D-148-03 — Tamper-evidence lives in the file's hash chain
Keep the SHA-256 chain inside `decision-store.json` + `framework-events.ndjson`; `audit verify` verifies both via `compute_entry_hash`. No SQLite chain table.
**Rationale**: Append-only ≠ tamper-evident, but a canonical-bytes hash chain IS the zero-dependency tamper-evident pattern, O(n) verify (research [5][6][7]); Merkle is overkill at our scale [4]. Deleting `state.db` loses no integrity guarantee.

### D-148-04 — `install-state.json` = current `InstallState` Pydantic dump (resolved OQ)
Reinstate a writable `install-state.json` whose shape is the serialization of the current `InstallState` Pydantic model (the DB already stored `state_json` = a full Pydantic dump); per-step state rides as a list/sidecar.
**Rationale**: One source of shape (the live model), no archaeology of the pre-spec-125 schema, no model↔file drift.

### D-148-05 — Drop SQLite `audit query`/`index`; rollups over NDJSON (resolved OQ)
Remove `ai-eng audit query` (arbitrary SELECT) + `audit index`. Reimplement `audit tokens` (rollups by skill/agent/session), `audit replay` (span tree), and `audit otel-export` as direct `framework-events.ndjson` scans. `audit verify` unchanged.
**Rationale**: The audit found `audit query` is an optional dev surface with no gate/CI/runtime dependents; the stop-hook token rollup is a sum over NDJSON. Keep the useful fixed rollups, drop only the SQL.

### D-148-06 — Hooks drop all SQLite access
`runtime-stop.py`, `runtime-session-end.py` (no vacuum), `session_bootstrap.py` (+ templates) read NDJSON/JSON, never `state.db`.
**Rationale**: Removes the Windows-WAL hot-path locking liability from the stdlib-only, cross-IDE, cross-OS hook surface (research [10][11]); mtime-cached file reads have no locking surface.

### D-148-07 — Collapse repository/service to file-backed wrappers (resolved OQ)
Keep the `DurableStateRepository`/`StateService` port but back it with file IO (not SQLite); callers' imports unchanged.
**Rationale**: Preserves the hexagonal port boundary (§10.8) with a smaller blast radius + easier testing than inlining file IO across ~15 call sites.

### D-148-08 — Installer/update write files, never create `state.db`
`ai-eng install` writes `install-state.json`/`ownership-map.json`/`decision-store.json`/`framework-capabilities.json`; never creates `state.db`. `ai-eng update` reads `ownership-map.json`.
**Rationale**: The installer is the origin of `state.db`; files-only requires it to treat the files as canonical.

### D-148-09 — One-shot export → verify → delete migration (resolved OQ: no `.bak`)
`ai-eng update`: if `state.db` exists, export any DB-only data (chiefly `install_state`/`install_steps` + any unmirrored `decisions`) to file homes, VERIFY the export, then delete `state.db`(+`-wal`/`-shm`) directly. Idempotent; no-op when absent; fail-loud (no delete) if export/verify fails.
**Rationale**: Existing installs hold data only in `state.db`. Export-verify-delete with no backup keeps it clean; the fail-loud verify gate is the safety net (operator chose no `.bak`).

### D-148-10 — Supersede spec-147 Wave 2 SSOT
Supersedes spec-147 D-147-09 (decision-store→state.db) + D-147-10 (gate-findings). The reverted spec-147 A1 reader migration (commit `da1e5686`) is not carried forward.

### Part B — Obvious-by-default conventions (carried from spec-147 Waves 3-5, adapted)

### D-148-11 — De-collide skill triggers (no folds) [was D-147-11]
Assign each contested trigger phrase to exactly one skill, others cross-reference: "write a blog post" (ai-prose vs ai-marketing), "pre-release" (ai-verify/ai-governance/ai-security), "architecture" (ai-explore/ai-explain/ai-onboard), "scan for security issues" (ai-verify/ai-security), "implement it"/"implement this" (ai-build gateway vs ai-code subcomponent). Make `ai-spec-draft` visible in the CLAUDE.md §11 chain as the optional pre-step. No merges; surface count unchanged.
**Rationale**: Anthropic's rule — if a human can't say which skill fires, neither can the agent. Description edits, no behavior loss. Exact phrase→skill assignments settled in `/ai-plan`.

### D-148-12 — One branch-cleanup implementation (hard-rename) [was D-147-12]
`ai-eng maintenance branch-cleanup` becomes a thin delegation to the richer `ai-eng cleanup branches`; CHANGELOG documents the consolidation; an architecture test asserts a single implementation import. No alias shim.
**Rationale**: Two entry points + two orchestration paths for one operation violate "one obvious way"; delegation is the DRY fix.

### D-148-13 — Deterministic STOP authority + method-tagged findings [was D-147-13]
Deterministic tool signals are the sole auto-STOP authority; the LLM acceptance layer is advisory + operator-confirmable. Every `/ai-verify` finding carries `method: deterministic|llm`. The one LLM-judged element (quality.md Step 2d condition 4) becomes deterministic or advisory-only (cannot silently auto-pass/auto-block). Same diff → same STOP verdict.
**Rationale**: Bazel-style hermeticity for "done"; the `method` tag lets callers threshold the two classes. (Exploration: the count-threshold STOP is already deterministic; this is the narrow gap.)

### D-148-14 — CI-enforced §10.x citation in skill Workflows (backfill first) [was D-147-14]
Backfill the ~22 skills with a `## Workflow` lacking a `§10.x` anchor, then add a CI test (modeled on `test_canonical_events_count.py`) asserting every Workflow section cites `§10.\d`.
**Rationale**: A convention enforced by hope isn't a convention; failing-first CI is the poka-yoke.

### D-148-15 — Document + CI-lock the naming grammar (zero renames expected) [was D-147-15]
Codify the already-universal grammar (`ai-` + lowercase-kebab + verb|noun) in `ai-scaffold` + CONSTITUTION.md; CI asserts all skill dirs match. All 53 skills already satisfy it → zero renames; confirm before any rename.
**Rationale**: Names that don't predict behavior force memorized exceptions (Clean Code). Lock the existing pattern.

### D-148-16 — Dry-run-by-default for destructive CLI verbs [was D-147-16]
`cleanup branches` with no mode flag prints a plan + requires confirmation rather than silently activating `merged=True` + deleting. A test asserts a no-flag invocation deletes nothing.
**Rationale**: A destructive default with opt-in `--dry-run` is the inverse of the pit-of-success.

### D-148-17 — Phased suppression DEC-binding [was D-147-17]
Security-rule suppressions (`nosemgrep_hash`) hard-require a DEC at allowlist load (author the DECs for current entries in this PR); the other 50+ `dec_id: ""` entries warn per-entry until expiry 2026-07-10.
**Rationale**: Split the security-critical subset (bind now) from the churny backlog (phase to a dated deadline); hard-blocking all at once is a self-inflicted gate outage.

## Risks

- **install_state/steps reversal is the hardest piece** (High/High): reinstating writable `install-state.json` reverses spec-125; installer + doctor + readiness change. Mitigation: its own wave with the export migration + a focused installer e2e before touching readers.
- **No-`.bak` export migration loses data on a partial/corrupt `state.db`** (Low/High): mitigated by the fail-loud verify gate — `state.db` is deleted ONLY after the export verifiably succeeds.
- **`audit query` removal breaks a hidden dependent** (Low/Med): none gate/CI/runtime-blocking found; CHANGELOG + a fail-loud "removed — use `audit tokens`" stub.
- **~100-110 files + large mirror/test rewrite** (High/Low): wave-by-datum sequencing, each green before next; mirror regen once per wave.
- **Cross-OS hook behavior change** (Med/Med): NDJSON scans replace SQLite reads on the hot path. Mitigation: mtime-cached + tail-N bounded to keep <1s/<5s budgets; cross-OS hook tests.
- **Skill-editing waves overlap (persistence docs + trigger de-collision + §10.x backfill all touch SKILL.md/mirrors)** (Med/Low): sequence the SKILL.md-touching waves to serialize mirror regen.
- **Reversing three shipped specs (123/125/132)** (Med/Low): doctrine rewrite + CHANGELOG record the rationale (scale never materialized) with research citations.

## References

- research: .ai-engineering/runtime/research/sqlite-vs-files-only-persistence-2026-05-21.md
- doc: docs/persistence-doctrine.md (to be rewritten)
- doc: spec-147 (Waves 1/2a shipped on PR #532; Waves 2b-5 superseded here)
- doc: https://twdev.blog/2025/06/fsdb/
- doc: https://dev.to/veritaschain/building-a-tamper-evident-audit-log-with-sha-256-hash-chains-zero-dependencies-h0b
- doc: https://sqlite.org/wal.html
- doc: https://github.com/oven-sh/bun/issues/25964

## Open Questions

- **Exact contested-phrase → skill assignments (D-148-11)**: which skill owns each phrase; settled in `/ai-plan`.
- **`audit otel-export` worth reimplementing over NDJSON vs dropping (D-148-05)**: confirm in `/ai-plan` (low usage).
