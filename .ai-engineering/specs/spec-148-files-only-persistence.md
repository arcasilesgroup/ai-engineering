---
spec: spec-148
title: Files-only persistence — retire state.db
status: draft
effort: large
summary: "Retire embedded SQLite (state.db) entirely in favor of files-only persistence — JSON for small mutable records (decisions/ownership/risk/install), append-only hash-chained NDJSON for the audit/event log, Markdown for docs — eliminating migrations, dual-writes, rebuild caches, and the cross-OS SQLite hot-path liability. Supersedes spec-147 Wave 2 (D-147-09/10)."
supersedes: [spec-147 D-147-09, spec-147 D-147-10]
---

# Spec 148 — Files-only persistence (retire state.db)

## Summary

`ai-engineering` carries an embedded SQLite `state.db` (11 tables, 9 migrations) that is over-engineering for its actual scale and access pattern. The data it holds — decisions, ownership, risk acceptances, install state — is kilobyte-sized, single-writer (one developer's repo), read whole, and already mirrored to files (`decision-store.json`, `ownership-map.json` is even read *before* the DB today, `framework-events.ndjson`, `gate-findings.json`). SQLite only pays for concurrent writers, large indexed datasets, or complex joins — none of which apply — while it imposes migrations, dual-writes, rebuild caches, split-brain reads, and a cross-OS hot-path liability (Windows WAL holds locks beyond `close()`; two hooks read `state.db` live on every Stop/SessionEnd). This spec retires `state.db` entirely (Option A): every datum gets a file home (JSON / append-only NDJSON / Markdown), the audit/event log stays NDJSON with its SHA-256 hash chain for tamper-evidence, and the migration runner, `state_db.py`, and the SQLite-backed `audit query` projection are deleted. This supersedes spec-147 Wave 2 (the decision-store→state.db migration, D-147-09/10): the direction reverses from "consolidate into SQLite" to "files are the single source of truth."

## Goals

- **G1 — No SQLite anywhere.** `state.db`, `state_db.py`, the migration runner, and all migration files (`0001`–`0008`) are deleted. No code imports `sqlite3` for framework state. A CI test asserts the absence.
- **G2 — One file SoT per datum.** decisions → `decision-store.json`; ownership → `ownership-map.json`; risk → decision records in `decision-store.json` (the `risk_acceptances` table is dead — zero writers); install state → `install-state.json` (writable again); tool capabilities → `framework-capabilities.json` (rebuildable from manifest + disk on demand); events → `framework-events.ndjson`; gate findings → `gate-findings.json`. No dual-write, no derived SQLite cache, no rebuild step.
- **G3 — Tamper-evidence stays, in the file.** Decision tamper-evidence remains the SHA-256 hash chain *inside* `decision-store.json` (already verified by `ai-eng audit verify --decisions`); the event chain stays in `framework-events.ndjson`. No SQL table is needed for integrity — the chain lives in the append-only/record file (resolves the spec-147 audit-chain fork by going files-only, not Opt-B SQLite-chain).
- **G4 — Hooks read files, not SQLite.** `runtime-stop.py`, `runtime-session-end.py`, and `session_bootstrap.py` (and their install-template copies) drop all `sqlite3`/`state.db` access; token rollups and decision/risk counts are computed from `framework-events.ndjson` / `decision-store.json`. Removes the Windows-WAL hot-path liability across the multi-IDE, multi-OS hook surface.
- **G5 — `audit` surface reshaped, not silently broken.** The SQLite-backed arbitrary-`SELECT` `ai-eng audit query` and `audit index` are removed; the genuinely-used rollups (`audit tokens` by skill/agent/session, `audit replay`) are reimplemented as direct NDJSON scans. `audit verify` continues to verify the NDJSON + decision-store hash chains (file reads, unchanged).
- **G6 — Docs + surface tell the truth.** `docs/persistence-doctrine.md` is rewritten from the four-tier (SQLite tier-2) model to a files-only model; CLAUDE.md/CANONICAL.md `state.db` references and the ~26 skills + ~6 agents that cite `state.db.decisions` are updated to `decision-store.json`; mirrors regenerated.
- **G7 — Existing installs migrate cleanly, once.** A one-shot `ai-eng update` step exports any data that lives *only* in `state.db` (primarily `install_state`/`install_steps`) to its file home, then deletes `state.db`. Idempotent; no-op when `state.db` is already absent.
- **G8 — Clean reversal.** Every hard-delete and behavior change is documented in CHANGELOG; no backwards-compat shims. The reversal of spec-123/125/132 (which moved these data into SQLite) is explicit.

## Non-Goals

- **No change to the event NDJSON schema or the hash-chain algorithm** — only the *storage* changes (the SQLite `events` projection is dropped; the NDJSON SoT and `compute_entry_hash` stay).
- **No removal of Tier-3 config files** — `manifest.yml`, `hooks-manifest.json`, `gate-findings.json`, `suppression-allowlist.yml` are unaffected.
- **No new query DSL** to replace arbitrary `audit query` `SELECT`. The power-user SQL surface is dropped; only fixed, documented rollups (`tokens`, `replay`) survive as NDJSON scans.
- **No touching spec-147 Waves 1, 2a (shipped on PR #532) or 3, 4, 5.** This spec only supersedes spec-147's Wave 2 SSOT decisions (D-147-09/10).
- **No re-introduction of a database later** "for scale" within this spec — YAGNI; revisit only if a real concurrency/volume requirement appears.

## Decisions

### D-148-01 — Retire SQLite `state.db` entirely (Option A, files-only)

Delete `state.db` and the entire SQLite layer (`state_db.py`, `state/migrations/`, the `_runner.py` migration engine). Persist all framework state in files: JSON for small mutable records, append-only NDJSON for the audit/event log, Markdown for docs.

**Rationale**: At `ai-engineering`'s scale (kilobyte datasets, single-writer, read-whole, mtime-cached) flat files are the better-fit, lower-maintenance design; SQLite only pays for concurrency / large indexed data / complex joins the tool does not have (research [1][2][8][9]). SQLite also imposes a cross-OS hot-path liability — Windows WAL holds locks beyond `close()` and must not touch network shares (research [10][11][12]). The operator's explicit call: SQLite is premature over-engineering here.

### D-148-02 — Per-datum file homes (single SoT, no dual-write)

| Datum | File SoT (after) | Current state (audit) |
|-------|------------------|------------------------|
| decisions | `decision-store.json` | already dual-written; becomes sole SoT |
| ownership | `ownership-map.json` | repo already reads the JSON *first* (split-brain) — files-only removes the DB side |
| risk acceptances | decision records in `decision-store.json` | `risk_acceptances` table has **zero writers** (dead); risk already lives in `decisions` via `details_json` |
| install state | `install-state.json` (writable) | reverses spec-125 which moved it into the DB |
| tool capabilities | `framework-capabilities.json` (rebuilt from manifest + disk on demand) | DB table is a derived projection |
| events | `framework-events.ndjson` | DB `events` table is an explicitly-declared cache of the NDJSON |
| gate findings | `gate-findings.json` | already the canonical write target; DB table is an orphaned placeholder |

**Rationale**: Six of the eleven tables are already pure-derived, dead, or orphaned; the rest already have file counterparts (some already the read path). Files-only collapses the split-brain and dual-writes into one obvious store per datum (DRY / single-SoT).

### D-148-03 — Decision/event tamper-evidence lives in the file's hash chain

Keep the SHA-256 hash chain inside `decision-store.json` (records) and `framework-events.ndjson` (events); `ai-eng audit verify` continues to verify both file chains via `compute_entry_hash`. No SQLite hash-chain table is introduced.

**Rationale**: This resolves the spec-147 audit-chain fork. Append-only ≠ tamper-evident, but a hash chain over canonical bytes *is* the recognized zero-dependency tamper-evident pattern, verified O(n) (research [5][6][7]); Merkle trees are overkill at our scale [4]. The chain belongs in the file, not a SQL table — so deleting `state.db` loses no integrity guarantee.

### D-148-04 — Drop SQLite-backed `audit query`/`index`; reimplement rollups over NDJSON

Remove `ai-eng audit query` (arbitrary `SELECT`) and `ai-eng audit index` (build SQLite projection). Reimplement `audit tokens` (by skill/agent/session) and `audit replay` (span tree) as direct `framework-events.ndjson` scans. `audit verify` is unchanged (file reads). The stop-hook session-token rollup and the `session_bootstrap` decision/risk counts are computed from the NDJSON / `decision-store.json`.

**Rationale**: The internal audit found `audit query` is an optional dev surface — no gate, CI, or non-hook runtime path depends on it; the only live reader (stop-hook token rollup) computes a sum trivially derivable from NDJSON. Arbitrary SQL over events is the one feature genuinely lost; the operator accepted that tradeoff. Fixed rollups cover the real usage.

### D-148-05 — Delete the SQLite code layer; repoint readers/writers to file IO

Delete `state_db.py`, `state/migrations/**`, `_runner.py`. Collapse `DurableStateRepository`/`StateService` to file-backed implementations (or delete them where a direct `read_json_model`/`write_json_model`/NDJSON-append call is clearer). Every reader/writer enumerated in the audit (decisions, ownership, install, capabilities, events) repoints to its file SoT.

**Rationale**: With no DB, the repository/service indirection that existed to wrap SQLite is dead weight; prefer the simplest file IO (KISS). The audit gives the exact call-site inventory.

### D-148-06 — Hooks drop all SQLite access

`runtime-stop.py` (session token rollup), `runtime-session-end.py` (vacuum + `audit index` subprocess), `session_bootstrap.py` (decision/risk counts) — and their `src/ai_engineering/templates/` copies — stop reading `state.db`. Token rollup and counts read files. The SessionEnd vacuum is removed (no DB to vacuum).

**Rationale**: Removes the Windows-WAL hot-path locking liability (research [10][11]) from the stdlib-only, cross-IDE, cross-OS hook surface; a flat-file read with mtime caching has no locking surface. (A Windows-only `gate_cache` flake already surfaced this session.)

### D-148-07 — Rewrite the persistence doctrine + reconcile docs/skills/agents

Rewrite `docs/persistence-doctrine.md` from four-tier (NDJSON / SQLite / config / Markdown) to a three-tier files-only model (append-only NDJSON audit · JSON/YAML records+config · Markdown). Update the `state.db` references in CLAUDE.md/CANONICAL.md (lines 15, 21, 97, 265) and the ~26 skills + ~6 agents that cite `state.db.decisions` → `decision-store.json`. Regenerate all mirrors via `scripts/sync_command_mirrors.py`.

**Rationale**: G2 of the obvious-by-default thesis (spec-147) — every doc claim must resolve to an on-disk fact. After deletion the doctrine and every `state.db.decisions` reference would be false.

### D-148-08 — Installer/update write files, never create `state.db`

`ai-eng install` writes `install-state.json`, `ownership-map.json`, `decision-store.json`, `framework-capabilities.json` and never creates `state.db`. `ai-eng update` reads `ownership-map.json`.

**Rationale**: The installer is the origin of `state.db`; files-only requires it to stop creating the DB and treat the files as canonical.

### D-148-09 — One-shot export-then-delete migration for existing installs

`ai-eng update` runs a single idempotent step: if `state.db` exists, export any data that lives *only* there (chiefly `install_state`/`install_steps`, and any `decisions` rows not already in `decision-store.json`) to the file homes, then delete `state.db` (+ `-wal`/`-shm`). No-op when `state.db` is absent.

**Rationale**: Existing installs carry data in `state.db`. Decisions/ownership/events already have file mirrors; install state may not. One last migration (read DB → write files → delete) ensures no data loss, then the migration machinery is gone. Hard migration, no shim (CHANGELOG documents it).

### D-148-10 — Supersede spec-147 Wave 2 (D-147-09/10)

This spec supersedes spec-147 D-147-09 (decision-store full migration *to* state.db) and D-147-10 (gate-findings SQLite reconciliation). spec-147 retains Waves 1, 2a (delivered, CI-green on PR #532) and Waves 3, 4, 5. The reverted spec-147 A1 reader migration is intentionally not carried forward.

**Rationale**: spec-147 Wave 2 aimed to consolidate decisions *into* SQLite; this spec reverses that direction. Keeping them as separate specs (operator decision) prevents the route change from contaminating the "obvious by default" thesis and lets each version/PR independently.

## Risks

- **install_state/install_steps reversal is the hardest piece** (High likelihood / High impact): reinstating a writable `install-state.json` reverses spec-125; installer pipeline, `doctor`, and readiness readers all change. Mitigation: do install-state first as its own wave with the one-shot export migration (D-148-09) and a focused installer e2e test before touching the read sites.
- **`audit query` removal breaks a hidden dependent** (Low / Med): the audit found none gate/CI/runtime-blocking, but a user's muscle memory may rely on ad-hoc SQL. Mitigation: CHANGELOG calls it out; `audit tokens`/`replay` cover the common rollups; fail-loud "removed — use `audit tokens`" stub for the dropped verb.
- **One-shot export migration loses data on a partial/corrupt `state.db`** (Low / High): a corrupt DB could fail the export. Mitigation: fail-loud (don't delete `state.db` unless the export verifiably succeeded); back up `state.db` to `state.db.bak` before delete for one release.
- **~100-110 files touched; large mirror + test rewrite** (High / Low): mechanical but churny — ~23 SQLite-seeding tests rewritten to files, ~57 string-ref tests updated, doctrine doc rewritten, 26 skills + 6 agents + mirrors regenerated. Mitigation: wave-by-datum sequencing, each wave green before the next; mirror regen once per wave.
- **Cross-OS hook behavior change** (Med / Med): hooks switch from SQLite reads to NDJSON scans on the hot path. Mitigation: keep the reads mtime-cached + bounded (tail-N events) to preserve the <1s/<5s budgets; cross-OS hook tests.
- **Reversing three shipped specs (123/125/132) invites "why did we flip-flop?"** (Med / Low): Mitigation: the doctrine rewrite + CHANGELOG record the rationale (scale never materialized; SQLite was premature) with the research citations.

## References

- research: .ai-engineering/runtime/research/sqlite-vs-files-only-persistence-2026-05-21.md
- doc: .ai-engineering/specs/spec.md (spec-147 — superseded Wave 2)
- doc: docs/persistence-doctrine.md (to be rewritten)
- doc: https://twdev.blog/2025/06/fsdb/ (files-first for small tools)
- doc: https://dev.to/veritaschain/building-a-tamper-evident-audit-log-with-sha-256-hash-chains-zero-dependencies-h0b (NDJSON hash-chain audit)
- doc: https://sqlite.org/wal.html (WAL cross-platform constraints)
- doc: https://github.com/oven-sh/bun/issues/25964 (Windows WAL lock-after-close)

## Open Questions

- **install-state.json shape** (D-148-08): reinstate the exact pre-spec-125 schema, or a new shape aligned with the current `InstallState` Pydantic model? Resolve in `/ai-plan`.
- **`audit query` removal scope** (D-148-04): hard-remove `audit query` + `audit index` and keep `audit tokens`/`replay` over NDJSON — confirm `tokens`/`replay` are worth reimplementing vs also dropping. Operator preference.
- **Export migration retention** (D-148-09): keep `state.db.bak` for one release (safer) vs delete outright (cleaner). Operator preference.
- **DurableStateRepository/StateService fate** (D-148-05): collapse to thin file-backed wrappers (smaller diff, keeps the port) vs delete and inline file IO at call sites (simplest, bigger diff). Resolve in `/ai-plan` after a caller audit.
