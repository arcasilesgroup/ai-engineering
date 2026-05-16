---
title: Harness Persistence Strategy — Doctrine, Tier Boundaries, and the End of Silent Dual-Writes
status: draft
audience: framework-devs+contributors
branch: (proposed) spec-NNN/harness-persistence-strategy
length_estimate: ~7000 words
authoring_style: surface-rearch
principles_required: ["§10.1 KISS", "§10.2 YAGNI", "§10.3 SOLID", "§10.4 DRY", "§10.6 SDD"]
delivery_mode: /ai-autopilot (multi-wave; cross-surface)
mantra: "One canonical store per datum. Caches are rebuildable. No silent dual-writes."
---

# Harness Persistence Strategy — Brief

## 1. Vision

The ai-engineering framework has accumulated five distinct persistence primitives — SQLite (`state.db`), NDJSON (`framework-events.ndjson`), structured JSON (`hooks-manifest.json`, `gate-findings.json`, `manifest.yml`), markdown (specs, LESSONS, CONSTITUTION, CHANGELOG), and runtime-ephemeral state (`.ai-engineering/runtime/`). The current arrangement is internally inconsistent: the same datum (events, decisions, hooks integrity, ownership, install state) frequently lives in two stores simultaneously, with no transactional contract binding them and no contract test catching the drift. The result is silent failure: `_insert_events_row` has been writing to a phantom schema for weeks ([decision_log.py:115](src/ai_engineering/governance/decision_log.py:115)), `hooks_integrity` is a documented runtime ledger that no code path ever populates ([0002_seed_from_json.py:15](src/ai_engineering/state/migrations/0002_seed_from_json.py:15)), and `audit-index.sqlite` persists as a 0-byte file that `runtime-stop.py` opens, fails to query, and silently moves past ([runtime-stop.py:474](.ai-engineering/scripts/hooks/runtime-stop.py:474)). This brief proposes a single doctrine — **One Canonical Store Per Datum** — under which each piece of framework state has exactly one writable home, with derived caches explicitly labelled, rebuildable on demand, and forbidden from masquerading as sources of truth. The doctrine respects the existing Article-III audit-chain immutability constraint (`framework-events.ndjson` stays the canonical, hash-chained ledger per CONSTITUTION.md §13.1), and respects the spec-135 hot-path budget by keeping all SQLite I/O off the PreToolUse/PostToolUse hot paths.

## 2. Scope Boundary

**In scope:**

1. Doctrine document at `docs/persistence-doctrine.md` declaring the tier model, SSOT-PD rule, and rebuild semantics for derived caches.
2. CONSTITUTION.md hard rule referencing the doctrine (Article-III companion).
3. CLAUDE.md §0 bootstrap pointer updated to consult the doctrine, not the broken `state.db.decisions` table.
4. Bug clearance: `_insert_events_row` schema mismatch, `audit-index.sqlite` 0-byte legacy, `runtime-stop.py` dead read, the absent runtime INSERT into `hooks_integrity`.
5. Autopopulation wiring: `/ai-brainstorm` and `/ai-plan` write decisions to `state.db` at approval time; installer wires `install_steps`; `ai-eng ownership import` for CODEOWNERS.
6. Contract tests: every SQL writer validated against the canonical schema; round-trip fixture testing for every dual-store boundary.
7. Spec-135 M6 NDJSON rotation wired to `SessionEnd` (currently unwired per [spec.md:75-79](.ai-engineering/specs/spec.md:75-79)).
8. `state.db.events` repositioned as a rebuildable derived cache, populated only by `ai-eng audit index`, never by hot-path dual-write.

**Explicitly NOT in scope:**

- Removing `framework-events.ndjson` or the hash chain (Article-III hard rule per CONSTITUTION.md §13.1, reinforced by [spec.md:42](.ai-engineering/specs/spec.md:42)).
- Replacing SQLite with a different RDBMS (Postgres, DuckDB, etc.) — SQLite operational profile is correct for the workload.
- Expanding `state.db` to absorb additional concerns (e.g. session history, tool-call traces) — the question is what fits, not what more can be packed in.
- Distributing state across machines — single-host, single-checkout model is preserved.
- Cross-IDE state sharing — every IDE checkout has its own `state.db`; no central store.
- Restructuring the spec lifecycle artifacts under `.ai-engineering/state/specs/*.json` — those are a separate concern owned by `spec_lifecycle.py`.

## 3. Diagnostic Snapshot

The current persistence layer is best described as **partial canonicalization with silent dual-write failure modes**. The evidence:

### 3.1 Five storage primitives, overlapping concerns

The framework writes to all five primitives, but no single document defines which datum belongs where. The shape is reverse-engineered by reading code:

- **SQLite** at `.ai-engineering/state/state.db` with 14 tables (STRICT mode) declared at [0001_initial_schema.py:27](src/ai_engineering/state/migrations/0001_initial_schema.py:27). Current row counts on a typical operator checkout: `_migrations:7`, `install_state:1`, `tool_capabilities:1`, **every other table: 0 rows** (`decisions`, `events`, `gate_findings`, `hooks_integrity`, `install_steps`, `ownership_map`, `risk_acceptances`).
- **NDJSON** at `.ai-engineering/state/framework-events.ndjson` — 1,332 lines on the same checkout, hash-chained via `prev_event_hash` stamped under file lock at [hook-common.py:250](.ai-engineering/scripts/hooks/_lib/hook-common.py:250). Lock file: `.ai-engineering/state/locks/framework-events.lock`. Schema contract: `event_schema.py` referenced at [observability.py:15](src/ai_engineering/state/observability.py:15).
- **JSON structured**: `hooks-manifest.json` (72 hooks with sha256, written by `regenerate-hooks-manifest.py`, read on every `run_hook_safe` via [integrity.py:99](.ai-engineering/scripts/hooks/_lib/integrity.py:99)); `gate-findings.json` (canonical per spec-104 D-104-06 per [state_db.py:57-62](src/ai_engineering/state/state_db.py:57)); `manifest.yml`; `strategic-compact.json`. Several legacy JSONs cited in [state_db.py:63](src/ai_engineering/state/state_db.py:63) as "deprecated fallbacks" (`decision-store.json`, `ownership-map.json`, `install-state.json`, `framework-capabilities.json`) are absent from disk.
- **Markdown** SoT: `.ai-engineering/specs/spec.md`, `.ai-engineering/LESSONS.md`, `CONSTITUTION.md`, `CLAUDE.md`, `CHANGELOG.md`. Human-authored, never programmatically rewritten.
- **Runtime ephemeral** at `.ai-engineering/runtime/`: `event-sidecars/` (oversized event payloads offloaded by content hash per [audit.py:16](.ai-engineering/scripts/hooks/_lib/audit.py:16)), `tool-outputs/`, `checkpoint.json`, `precompact-snapshot.json`, `autopilot/` (current run state). Gitignored.

### 3.2 Duplication map — same datum, multiple stores

For each duplication, the evidence shows that the dual-write path is either silently broken (no error surfaced) or fundamentally one-shot (migration ran once, never reproduces):

**Events live in three stores**:

| Store | Rows / lines | Canonical? | Write path |
|---|---|---|---|
| `framework-events.ndjson` | 1,332 lines (hash-chained) | YES — Article-III | `emit_event` at [hook-common.py:201](.ai-engineering/scripts/hooks/_lib/hook-common.py:201) and `_append_framework_events_locked` at [observability.py:112](src/ai_engineering/state/observability.py:112) |
| `state.db.events` | 0 rows | No — derived | Migration `0003_replay_ndjson` (one-shot, [0003_replay_ndjson.py:144](src/ai_engineering/state/migrations/0003_replay_ndjson.py:144)) + `_insert_events_row` (buggy dual-write) |
| `audit-index.sqlite` | 0 bytes | No — deprecated empty shell | [audit_index.py:24](src/ai_engineering/state/audit_index.py:24) says "removed lazily on first call" — never called |

Migration 0003 was applied at 2026-05-15T14:14:15Z (`_migrations` ledger). Events emitted after that timestamp are NOT in `state.db.events`. The NDJSON and the SQL projection have diverged from first principles.

**Decisions live in three stores**:

| Store | State | Write path |
|---|---|---|
| Spec markdown files | Canonical for authoring | Human-authored |
| `state.db.decisions` | 0 rows | `upsert_decision_rows` at [state_db.py:306](src/ai_engineering/state/state_db.py:306), called by `repository.save_decisions:167`, `installer/service.py:567`, `installer/phases/state.py:123` |
| `decision-store.json` | Absent from disk | `repository.save_decisions` at [repository.py:154-168](src/ai_engineering/state/repository.py:154) STILL CALLS `write_json_model` to this path on every save |

The `repository.save_decisions` path does dual-write: SQL first, then a JSON file that nobody reads and no operator has on disk. The inline comment at [repository.py:158](src/ai_engineering/state/repository.py:158) admits: "the legacy `decision-store.json` mirror remains until the 12 outstanding Decision view-model callers are migrated — tracked in a separate spec." This brief IS that separate spec.

**Hooks integrity lives in two stores, one never written**:

| Store | Contents | Writer |
|---|---|---|
| `hooks-manifest.json` | 72 hooks with sha256 | `regenerate-hooks-manifest.py` (one-shot) |
| `state.db.hooks_integrity` | 0 rows | **No writer exists** |

[0002_seed_from_json.py:15-17](src/ai_engineering/state/migrations/0002_seed_from_json.py:15) explicitly promises: "runtime hook checks land their first rows." But `run_hook_safe` at [hook-common.py:488](.ai-engineering/scripts/hooks/_lib/hook-common.py:488) contains zero INSERT statements to `hooks_integrity`. The verification ledger table is a dead schema with no producer.

**Install state lives in two stores**:

| Store | State | Writer |
|---|---|---|
| `install-state.json` | Absent from disk | Migration 0004 reads once during bootstrap |
| `state.db.install_state` | 1 row (singleton) | Migration 0004, `install_state` upsert calls in installer |

These are synchronized cleanly — the JSON is read once at migration time then removed. This is the only duplication path that does NOT leak.

**Gate findings live in two stores, intentionally**:

| Store | Contents | Canonical? |
|---|---|---|
| `gate-findings.json` | Current session findings | YES per spec-104 D-104-06, consumed by `/ai-commit`, `/ai-pr` |
| `state.db.gate_findings` | 0 rows | No — "structural placeholder only" per [state_db.py:58](src/ai_engineering/state/state_db.py:58) |

`state_db.py:57-62` says explicitly: "the state.db `gate_findings` table is a structural placeholder only ... never read by the orchestrator." The table exists in schema, will never carry data.

**Ownership map**: Both `ownership-map.json` (absent on disk) and `state.db.ownership_map` (0 rows) are empty. `repository.load_ownership` at [repository.py:170](src/ai_engineering/state/repository.py:170) checks JSON existence first and falls back to a default. Two empty stores, no source of truth.

### 3.3 Confirmed bugs in the dual-write paths

**Bug 1: `_insert_events_row` writes to a phantom schema**. [decision_log.py:134-150](src/ai_engineering/governance/decision_log.py:134) constructs an INSERT with columns `(kind, timestamp, component, outcome, correlation_id, project, detail_json)`. The actual `events` table at [0001_initial_schema.py:36-61](src/ai_engineering/state/migrations/0001_initial_schema.py:36) requires `span_id TEXT PRIMARY KEY` (missing), `engine TEXT NOT NULL` (missing), and has NO column named `project`. Every INSERT raises `sqlite3.Error` and is swallowed at [decision_log.py:152-155](src/ai_engineering/governance/decision_log.py:152) by `except sqlite3.Error: return`. The test at [test_decision_log.py:85-98](tests/unit/governance/test_decision_log.py:85) creates a fake `events` table matching the broken INSERT — so the unit test passes against a schema that does not exist in production. This is a textbook silent-drift failure: the writer was updated, the reader was never updated, the test was written against the wrong schema.

**Bug 2: `run_hook_safe` never writes `hooks_integrity`**. The entire body of [hook-common.py:488-569](.ai-engineering/scripts/hooks/_lib/hook-common.py:488) calls `_verify_caller_integrity`, optionally `_emit_integrity_violation` (writes to NDJSON), runs `main_fn()`, emits a heartbeat event to NDJSON, and exits. No SQLite connect. No INSERT. The migration documents the intent; the code does not honor it.

**Bug 3: `0003_replay_ndjson` is a one-shot bootstrap migration**. [0003_replay_ndjson.py:144](src/ai_engineering/state/migrations/0003_replay_ndjson.py:144) is called by `_runner.run_pending` at [_runner.py:193](src/ai_engineering/state/migrations/_runner.py:193) — which only applies migrations not yet recorded in `_migrations`. Once applied, it never runs again. Events emitted after bootstrap accumulate in NDJSON, never project to SQL.

**Bug 4: `audit-index.sqlite` 0-byte zombie**. [audit_index.py:24](src/ai_engineering/state/audit_index.py:24) promises lazy removal on first `build_index` or `open_index_readonly` call. The file persists because neither has been called against the current project root. Worse: [runtime-stop.py:474-485](.ai-engineering/scripts/hooks/runtime-stop.py:474) opens it via `file:{index_path}?mode=ro`, which succeeds (SQLite creates a new in-memory empty DB from the 0-byte file), then the `SELECT FROM session_token_rollup` fails with `OperationalError: no such table`, which `except sqlite3.Error` swallows. The session rollup is dead code on every Stop event.

**Bug 5: Current Claude Code session not emitting**. Last NDJSON event timestamp is 2026-05-15T21:52:14Z; the current Claude Code session is past 22:00. Despite 11 hook events being registered in [.claude/settings.json](.claude/settings.json) (UserPromptSubmit, PreToolUse, PostToolUse, SessionStart, Stop, etc.), no events from this session have landed. Manual invocation of `runtime-session-start.py` succeeds with exit 0 but produces no NDJSON line. Root cause not yet established — likely a Claude Desktop CWD or stdin-passthrough issue. Blocking for any "100% functional state.db" goal because hooks are the production write path.

### 3.4 Hot-path inventory — currently clean, must stay clean

Per CLAUDE.md "Hot-Path Discipline (Claude Code)": pre-commit < 1s, pre-push < 5s. Per-hook budgets at [hook-common.py:396-406](.ai-engineering/scripts/hooks/_lib/hook-common.py:396): PreToolUse 1000 ms, PostToolUse 1000 ms, UserPromptSubmit 1000 ms, SubagentStop 1000 ms, Stop 5000 ms, SessionStart 5000 ms, SessionEnd 5000 ms, PreCompact 5000 ms. Manifest SLOs at [tests/unit/config/test_manifest.py:403](tests/unit/config/test_manifest.py:403) corroborate.

Every registered hot-path hook (PreToolUse, PostToolUse, UserPromptSubmit) currently AVOIDS `state.db`. The only hook that touches SQLite is `runtime-stop.py:474` on the Stop event, and it touches the broken 0-byte `audit-index.sqlite` not `state.db`. Spec-135 D-135-04 ([spec.md:69-73](.ai-engineering/specs/spec.md:69)) endorses mtime-based caching for hot-path scripts specifically to keep SQLite off the hot path. Any proposal that adds SQLite writes to hot-path hooks fights both the current architecture AND the most recently approved spec.

## 4. Architecture

### 4.1 Single Source of Truth Per Datum (SSOT-PD)

The doctrine: **every piece of framework state has exactly one canonical writable store**. All other stores holding the same data are either (a) explicit, named, rebuildable caches, or (b) bugs to remove.

Four tiers, each with a single concern:

```
TIER 1: Append-only audit log (NDJSON + cryptographic chain)
  Canonical for: events, observations, audit trail
  Files:        framework-events.ndjson (hash-chained, Article-III)
                observation-events.ndjson (instinct observations)
  Read pattern: sequential replay, time-range scans
  Write SLA:    < 5 ms per emit (lock-protected append)
  Rotation:     archive at 100k lines OR 50 MB (D-135-05, M6)

TIER 2: Stateful lifecycle (SQLite state.db)
  Canonical for: install_state, install_steps, risk_acceptances, decisions
  Why SQL:       ACID transactions for multi-field updates;
                 expires_at queries for risk lifecycle;
                 PRIMARY KEY uniqueness for decision_id, step_id;
                 FTS for decision rationale search.
  Read pattern: indexed lookups by key, status filters
  Write trigger: explicit operator actions (/ai-brainstorm approval,
                 ai-eng risk accept, installer step completion)
  Hot-path:     NEVER. State.db is cold storage.

TIER 3: Configuration as code (structured JSON + YAML)
  Canonical for: hooks-manifest.json, manifest.yml, gate-findings.json
  Why JSON:     human-editable, git-diffable, no migration cost,
                 read-mostly, review-worthy in PRs.
  Read pattern: load-once-cache (mtime invalidation)
  Write trigger: manual edit (manifest.yml) OR generated script
                 (regenerate-hooks-manifest.py)

TIER 4: Human-authored truth (Markdown)
  Canonical for: specs, LESSONS, CONSTITUTION, CLAUDE.md, CHANGELOG
  Why Markdown: human-readable, diff-friendly, no parser brittleness,
                 PR review surface, no migration cost.
  Read pattern: full-file read, occasionally grep
  Write trigger: human authoring, governance flows
                 (/ai-brainstorm, /ai-plan write spec markdown).

DERIVED CACHES (rebuildable, never canonical):
  state.db.events           ← cache of NDJSON for SQL queries
                              rebuilt via `ai-eng audit index --rebuild`
                              triggered at SessionEnd within budget
  state.db.decisions_fts    ← FTS5 cache of decisions table content
                              maintained by FTS5 triggers (existing)
  state.db.ownership_map    ← cache of CODEOWNERS file
                              rebuilt via `ai-eng ownership import`
```

### 4.2 Strict tier rules

1. **No silent dual-writes.** When the same logical record must exist in two tiers (e.g. a decision exists in spec markdown AND in state.db as a queryable row), exactly one tier is canonical. The other is a derived cache with an explicit, named, idempotent rebuild command. Drift is acceptable between cache rebuilds; freshness is documented; the rebuild is fast enough to run at SessionEnd or on-demand without operator pain.

2. **Audit chain stays on NDJSON.** `framework-events.ndjson` with `prev_event_hash` is the Article-III canonical store. Any proposal that puts events in SQL as canonical violates the hash-chain primitive: SQLite's B-tree storage cannot maintain the linear chain semantics that make tamper-evident replay possible. (See Evidence Catalog §5.B for the cryptographic-chain literature.) The `events` table remains, but as a labelled cache populated only by `ai-eng audit index`.

3. **Hot-path code never writes SQL.** PreToolUse, PostToolUse, UserPromptSubmit, SubagentStop, Notification hooks: NDJSON-only emissions. Stop, SessionStart, SessionEnd, PreCompact, PostCompact hooks: may touch SQL if within budget, but PREFER NDJSON. Contract test enforces this by importing each hot-path hook and asserting it never imports `sqlite3` directly.

4. **Schema authority lives in code, not in DDL.** A canonical Pydantic model defines the shape of every state.db row (Decision, RiskAcceptance, InstallStep, etc.); the migration DDL is derived from it. A contract test round-trips a fixture through the Pydantic model and back to the table and asserts byte-equivalence. This catches the `_insert_events_row` class of bug at CI time, not in production.

5. **Hard deletes, no shims.** Per CONSTITUTION.md §13 / spec-128 sub-d: when a JSON file is deprecated, the writer is REMOVED, not silently kept "for safety." The current `repository.save_decisions` dual-write to absent `decision-store.json` violates this. The brief mandates hard removal of legacy dual-writes; CHANGELOG documents the breakage.

### 4.3 Why this works under spec-135 constraints

spec-135 declares hot-path budgets as inviolable and forbids removing the audit layer ([spec.md:42](.ai-engineering/specs/spec.md:42)). The proposed doctrine:

- Keeps `framework-events.ndjson` as canonical audit (Article-III preserved).
- Keeps `state.db` for cold-storage lifecycle entities (no hot-path SQL).
- Repositions `state.db.events` as a SessionEnd-rebuilt cache (within the 5-second SessionEnd budget, the existing `audit_index.build_index` already supports incremental indexing via `indexed_lines.last_offset`).
- Removes the broken dual-write in `_insert_events_row` entirely.
- Wires the missing NDJSON rotation at SessionEnd (spec-135 M6 follow-through).

The doctrine is therefore additive to spec-135, not in tension with it. The brief proposes filling spec-135's open question at [spec.md:180](.ai-engineering/specs/spec.md:180) ("Does the existing `events` table accept the JSON shape proposed in §4.2, or does it require a migration? `/ai-plan` decides whether the event lives in framework-events.ndjson only (Article-III chain) or both NDJSON and events (queryable).") with: **NDJSON canonical, state.db.events as SessionEnd-rebuilt derived cache. No production write path emits to SQL.**

## 5. Evidence Catalog

| Claim | Evidence |
|---|---|
| NDJSON is canonical audit per Article-III | [CONSTITUTION.md](CONSTITUTION.md) §13.1; [spec.md:42](.ai-engineering/specs/spec.md:42) "Do not remove the auditing layer" |
| `emit_event` writes only NDJSON | [hook-common.py:201](.ai-engineering/scripts/hooks/_lib/hook-common.py:201) — no SQL write in body |
| `_append_framework_events_locked` is the Python-package twin | [observability.py:112](src/ai_engineering/state/observability.py:112) |
| `prev_event_hash` is stamped under lock | [hook-common.py:250](.ai-engineering/scripts/hooks/_lib/hook-common.py:250) inside `with_lock_retry` |
| state.db has 14 STRICT tables | [0001_initial_schema.py:27](src/ai_engineering/state/migrations/0001_initial_schema.py:27) |
| `_insert_events_row` schema mismatch | [decision_log.py:115-157](src/ai_engineering/governance/decision_log.py:115) — INSERT omits span_id PK and engine NOT NULL, includes nonexistent column `project` |
| Silent error swallow on dual-write | [decision_log.py:152-155](src/ai_engineering/governance/decision_log.py:152) `except sqlite3.Error: return` |
| Test asserts against fake schema | [test_decision_log.py:85-98](tests/unit/governance/test_decision_log.py:85) constructs an `events` table not matching production |
| `run_hook_safe` has zero `hooks_integrity` INSERT | [hook-common.py:488-569](.ai-engineering/scripts/hooks/_lib/hook-common.py:488) — full body inspected |
| Migration 0002 documents the intent never implemented | [0002_seed_from_json.py:15-17](src/ai_engineering/state/migrations/0002_seed_from_json.py:15) |
| 0003 is one-shot bootstrap-only | [0003_replay_ndjson.py:144](src/ai_engineering/state/migrations/0003_replay_ndjson.py:144); [_runner.py:193](src/ai_engineering/state/migrations/_runner.py:193) idempotent runner |
| `audit-index.sqlite` is 0 bytes | `ls -la .ai-engineering/state/audit-index.sqlite` confirms; [audit_index.py:24](src/ai_engineering/state/audit_index.py:24) promises lazy delete that never fires |
| `runtime-stop.py` reads zombie file | [runtime-stop.py:474-485](.ai-engineering/scripts/hooks/runtime-stop.py:474) opens `audit-index.sqlite`; `session_token_rollup` SELECT fails silently |
| `gate-findings.json` is canonical per D-104-06 | [state_db.py:57-62](src/ai_engineering/state/state_db.py:57) "state.db gate_findings table is structural placeholder only" |
| `repository.save_decisions` dual-writes to absent JSON | [repository.py:154-168](src/ai_engineering/state/repository.py:154); inline comment confesses "12 outstanding callers" |
| Hot-path budgets declared | [hook-common.py:396-406](.ai-engineering/scripts/hooks/_lib/hook-common.py:396); [test_manifest.py:403](tests/unit/config/test_manifest.py:403) |
| Hot-path discipline declared | CLAUDE.md "Hot-Path Discipline (Claude Code)" section |
| D-135-04 endorses mtime caching off hot path | [spec.md:69-73](.ai-engineering/specs/spec.md:69) |
| D-135-05 NDJSON rotation policy | [spec.md:75-79](.ai-engineering/specs/spec.md:75) — archive at 100k lines or 50 MB |
| Spec-135 open question on persistence | [spec.md:180](.ai-engineering/specs/spec.md:180) — this brief answers it |
| CONSTITUTION.md §13 forbids backwards-compat shims | CLAUDE.md "Hard Rules" §3 |
| `upsert_decision_rows` is the canonical decision writer | [state_db.py:306](src/ai_engineering/state/state_db.py:306) |
| FTS5 over decisions exists | [0001_initial_schema.py](src/ai_engineering/state/migrations/0001_initial_schema.py) `decisions_fts` virtual table |
| Hot-path hooks currently avoid state.db | [.claude/settings.json](.claude/settings.json) — 11 registered events, 0 hooks touch state.db (only `runtime-stop.py` touches SQLite, via the broken legacy index) |

## 6. Roadmap

Five waves, each shippable as a separate PR if dispatched via `/ai-build`. As a bundle: `/ai-autopilot` with milestones M1–M5. Estimated 3–5 weeks end to end.

### M1 — Bug Clearance (1 week)

**Goal:** stop the bleeding. The silent failures are actively misleading the operator.

Tasks:
1. Delete `_insert_events_row` from [decision_log.py:115](src/ai_engineering/governance/decision_log.py:115). The function dual-writes to a phantom schema and contributes no real value; events stay in NDJSON. Remove the call site at `emit_policy_decision`. Update `test_decision_log.py` to assert the NDJSON write only.
2. Delete the 0-byte `.ai-engineering/state/audit-index.sqlite` from the repository. Rewrite [audit_index.py:24-59](src/ai_engineering/state/audit_index.py:24) so the legacy path is gone; `INDEX_REL` points to `state.db` exclusively; `_LEGACY_INDEX_REL` is deleted.
3. Fix [runtime-stop.py:474-485](.ai-engineering/scripts/hooks/runtime-stop.py:474) to read from `state.db` (the post-rebuild events cache) instead of the legacy `audit-index.sqlite`. Wrap in budget check (skip if rebuild not run this session).
4. Investigate why current Claude Code session does not emit hooks — likely passthrough_stdin or CWD resolution. File-evidence diagnostic, fix or document.
5. Add contract test `tests/unit/state/test_sql_writer_schemas.py`: for each SQL writer call site in `src/ai_engineering/` and `.ai-engineering/scripts/hooks/`, parse the INSERT, compare to the canonical schema from `0001_initial_schema.py`. Fail at CI on any column mismatch.

Acceptance gate M1: all five tasks landed; `pytest` green; `ai-eng audit query "SELECT COUNT(*) FROM events"` returns 0 (no dual-write contamination); `_insert_events_row` no longer referenced.

### M2 — Doctrine Landing (1 week)

**Goal:** write the doctrine down, point all entry surfaces at it.

Tasks:
6. Author `docs/persistence-doctrine.md`: four tiers (NDJSON / SQLite / JSON config / Markdown), SSOT-PD rule, rebuild semantics for derived caches, examples per tier.
7. Add CONSTITUTION.md §13.X hard rule referencing the doctrine: "Every datum has exactly one canonical store. Derived caches are explicitly labelled and rebuildable on demand."
8. Update CLAUDE.md §0 bootstrap so the persistence-doctrine pointer replaces the broken "query state.db decisions table" instruction. Cross-link to docs/persistence-doctrine.md.
9. Update mirror surfaces (AGENTS.md, GEMINI.md, .github/copilot-instructions.md) via `scripts/sync_mirrors/core.py` regeneration.
10. Add a glossary entry to docs/persistence-doctrine.md for terms used throughout (SSOT-PD, derived cache, Article-III, hot path, tier).

Acceptance gate M2: doctrine file exists; CONSTITUTION.md amended; CLAUDE.md updated; mirrors regenerated and byte-equivalent.

### M3 — Autopopulation (1 week)

**Goal:** make state.db actually populated for the data that belongs there.

Tasks:
11. `/ai-brainstorm` writes decisions to `state.db.decisions` at spec approval (one INSERT per decision in the approved spec). Cold path — runs once per spec approval, not in any hook hot path.
12. `/ai-plan` similarly upserts decisions if the plan introduces new ones.
13. `ai-eng decision backfill` parses `.ai-engineering/specs/*.md` and `CHANGELOG.md` to populate historical decisions (D-100-XX through D-135-XX) one-shot.
14. Installer wires `install_steps` INSERT after each completed step (cold path — one INSERT per step during install).
15. `ai-eng ownership import` parses CODEOWNERS or `ownership-map.json` (if operator-provided) and populates `state.db.ownership_map`.

Acceptance gate M3: after fresh install + `ai-eng decision backfill`, the relevant tables are populated. `ai-eng decision list` returns rows. Hot path remains untouched.

### M4 — Events as Derived Cache (1 week)

**Goal:** reposition `state.db.events` as explicit rebuildable cache.

Tasks:
16. Update `docs/persistence-doctrine.md` to declare `state.db.events` a derived cache. The Pydantic models and migration files document this.
17. Make `ai-eng audit index` the only writer to `state.db.events`. Remove any other write path.
18. Add `audit_index.rebuild_at_session_end()` invoked from `runtime-session-end.py` within the 5-second SessionEnd budget. Use the existing incremental indexing via `indexed_lines.last_offset` to avoid full rescan.
19. Wire spec-135 M6 NDJSON rotation: `runtime-rotate-throttled.py` invoked at SessionEnd; rotates `framework-events.ndjson` above 100k lines OR 50 MB per D-135-05.
20. Add contract test: after `ai-eng audit index --rebuild`, the row count in `state.db.events` matches the line count of `framework-events.ndjson` minus any malformed lines (sampled to 1k).

Acceptance gate M4: `state.db.events` is populated by SessionEnd rebuild; NDJSON rotation triggers at threshold; the chain integrity check (`ai-eng audit verify-chain`) still passes after rotation.

### M5 — hooks_integrity Strategy (1 week)

**Goal:** decide and execute. Open decision in §9 — the brief proposes Option A (remove the table) and lets `/ai-plan` confirm.

Tasks per Option A (recommended):
21. Drop the `hooks_integrity` table via migration `0008_drop_hooks_integrity`. `hooks-manifest.json` is sufficient evidence; integrity violations already emit to NDJSON as policy_decision events.
22. Remove the table reference from `audit_index` reads and any documentation.
23. Update `0002_seed_from_json.py` docstring to remove the "runtime hook checks land their first rows" promise.

Tasks per Option B (if `/ai-plan` decides differently):
21'. Add `_record_integrity_check()` to `run_hook_safe` that INSERTs only on state transitions (integrity_ok flipped from previous state, or first verification). Buffer to `.ai-engineering/runtime/hooks-integrity-buffer.ndjson`; flush at SessionEnd.
22'. Contract test asserts the buffer ALWAYS flushes within SessionEnd budget.

Acceptance gate M5: either the table is dropped cleanly OR the runtime writer exists with hot-path budget compliance. Whichever path is chosen, no silent gap remains.

## 7. Definition of Done

The brief is "implemented" when all of the following are true on a clean operator checkout:

- `docs/persistence-doctrine.md` exists, is non-empty, and is linked from CLAUDE.md §0 and CONSTITUTION.md.
- `_insert_events_row` and the broken `decision-store.json` dual-write are deleted (`grep -rn "_insert_events_row\|decision-store.json"` returns no production hits, only test fixtures or archived specs).
- `audit-index.sqlite` does not exist anywhere in the repo (legacy 0-byte file removed; `_LEGACY_INDEX_REL` constant deleted).
- `state.db.decisions` is populated after `/ai-brainstorm` approves a spec or `ai-eng decision backfill` runs.
- `state.db.install_steps` is populated after an `ai-eng install` run.
- `state.db.ownership_map` is populated after `ai-eng ownership import`.
- `state.db.events` is rebuilt at SessionEnd; row count matches NDJSON line count minus malformed lines.
- `framework-events.ndjson` rotates automatically at 100k lines or 50 MB threshold.
- `hooks_integrity` is either dropped (Option A) or populated at runtime by `run_hook_safe` (Option B).
- Contract test `test_sql_writer_schemas.py` passes — every SQL INSERT in production code matches the canonical schema.
- No hot-path hook imports `sqlite3` (verified by contract test).
- `ai-eng doctor --check state-db` is a one-liner that reports each table's row count and freshness vs expected.
- CHANGELOG.md documents the removals (per CONSTITUTION.md §13 "hard rename, hard delete").
- `pytest` green; `/ai-verify` returns GO on the resulting PR.

## 8. Quality Stamps

Principles applied (per docs/principles.md):

- **§10.1 KISS** — four tiers with one-line descriptions; the SSOT-PD rule is one sentence. No layered abstraction over the persistence primitives.
- **§10.2 YAGNI** — `hooks_integrity` removal candidate (Option A): if no consumer exists for the data, the table should not exist. Don't preserve dead schema for hypothetical futures.
- **§10.3 SOLID — Single Responsibility** — each tier handles one access pattern (audit, lifecycle, config, prose). No tier doubles as another.
- **§10.4 DRY** — but applied to STORES, not to writers. Two stores with the same datum is DRY violation; one store with multiple writers is acceptable.
- **§10.6 SDD** — every decision in this brief has a §10.x anchor and a file:line citation; spec phase will codify the open decisions as D-NNN-XX rows.

Contracts honored:

- Article-III audit-chain immutability (CONSTITUTION.md §13.1).
- spec-135 hot-path budgets (no SQL on PreToolUse/PostToolUse).
- spec-104 D-104-06 (`gate-findings.json` stays canonical, table stays placeholder).
- spec-128 sub-d hard-rename / no-shim rule.
- CONSTITUTION.md anonymous-content rule (no machine paths leaked).

## 9. Open Decisions

The spec phase (`/ai-brainstorm` → `/ai-plan`) must resolve:

**OD-1: `hooks_integrity` — drop or implement?**

Option A (recommended): drop the table; `hooks-manifest.json` + NDJSON integrity_violation events are sufficient.
Option B: implement the runtime writer with buffer + flush at SessionEnd.

Recommendation: A. The verification ledger has no documented downstream consumer; spec-115 G-1 envisioned it but no skill or agent reads from it today.

**OD-2: `state.db.events` rebuild cadence — SessionEnd only, or also on-demand?**

The brief proposes SessionEnd as the only automatic trigger plus `ai-eng audit index --rebuild` for on-demand. Alternative: scheduled rebuild every N minutes via the `loop` skill. Sufficient evidence does not yet exist on rebuild duration at scale.

**OD-3: `decisions_fts` invalidation strategy.**

The current FTS5 virtual table likely uses SQLite triggers tied to the `decisions` table. The brief leaves the trigger discovery and validation to the spec phase.

**OD-4: `repository.save_decisions` legacy JSON write — remove now or after caller migration?**

The inline comment at [repository.py:158](src/ai_engineering/state/repository.py:158) admits "12 outstanding Decision view-model callers" still expect the JSON. Removing the dual-write before migrating those callers breaks the readers. The brief proposes M1 includes a survey of the 12 callers and either migrates them or punts the JSON removal to M3.

**OD-5: How aggressively should mirror surfaces carry the doctrine?**

Doctrine fits in CLAUDE.md §0; mirrors (AGENTS.md, etc.) per spec-134 sub-005 are supposed to stay lean. Decision: doctrine summary in the canonical block, full doctrine in docs/persistence-doctrine.md, mirrors carry pointer only.

**OD-6: Should the contract test for hot-path hooks be a hard CI gate or a warning?**

Hard gate prevents accidental SQL-on-hot-path regressions but slows iteration. Warning is easier to ship but easier to ignore. Recommendation: hard gate, since spec-135 was born of a kernel panic and these regressions matter.

## 10. Migration

Per CONSTITUTION.md §13 / CLAUDE.md "Hard Rules" §3, every removal is hard. No shims, no fallbacks, no `# noqa`.

**Hard deletions (M1–M5):**

- `_insert_events_row` function (M1).
- `audit-index.sqlite` legacy file + `_LEGACY_INDEX_REL` constant (M1).
- `repository.save_decisions` legacy JSON write (M3, after caller migration).
- `hooks_integrity` table via migration 0008 (M5, Option A) OR the dead schema comment in 0002 (M5, Option B).

**Hard renames:** none currently anticipated. The table names (`events`, `decisions`, etc.) survive; their semantics tighten.

**CHANGELOG entries (per CONSTITUTION.md §13):**

```
### Removed
- `state.db.events` is no longer written by hot-path code paths. The
  `_insert_events_row` dual-write was never functional (schema
  mismatch silently swallowed). Use `ai-eng audit index --rebuild` to
  populate `state.db.events` from `framework-events.ndjson` for
  ad-hoc SQL queries.
- `decision-store.json` legacy mirror is no longer written. Decisions
  live in `state.db.decisions` (canonical) and `.ai-engineering/specs/*.md`
  (authoring).
- `audit-index.sqlite` legacy 0-byte file removed. Audit queries hit
  `state.db` directly.
- `state.db.hooks_integrity` table dropped (if M5 Option A). Hook
  integrity checks emit policy_decision events to
  `framework-events.ndjson` only.
```

**Breaking-banner thresholds:** removal of `_insert_events_row` is a private-API change (no external consumer); the JSON dual-write removal is also private. No breaking banner needed; the CHANGELOG entries suffice.

**Operator runbook:** documented in docs/persistence-doctrine.md under "Operator Surface — What Changes for You":
- `ai-eng decision list` works after `ai-eng decision backfill` (M3).
- `state.db.events` queries work after SessionEnd or manual `ai-eng audit index --rebuild` (M4).
- `ai-eng doctor --check state-db` reports populated / unpopulated table counts.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Caller migration for `decision-store.json` (12 callers per inline comment) is larger than estimated | Medium | Medium | M1 task 0: survey before scoping M3; if scope grows, split into M3a (decisions in state.db) + M3b (caller migration) |
| SessionEnd rebuild of state.db.events exceeds 5-second budget under heavy NDJSON growth | Medium | Low | Incremental indexing via `indexed_lines.last_offset` is already implemented; full rebuild only on schema change |
| Hot-path contract test produces false positives (legitimate read-only SQL access) | Low | Low | Test imports each registered hot-path hook script and statically scans for `import sqlite3` — read-only access on cold paths is allowed |
| Current Claude Code session hook gap (Bug 5) blocks M1 — cannot test runtime fixes if hooks do not emit | Medium | High | M1 task 4 isolates this as a diagnostic-first task. Worst case: it's a Claude Desktop CWD bug independent of this brief; report upstream and ship the rest |
| Operators with custom forks expect `_insert_events_row` for their own dual-write | Very Low | Low | Search GitHub for forks; none expected. CHANGELOG documents removal |
| `hooks_integrity` removal (M5 Option A) blocks a hypothetical future consumer | Low | Low | Reintroduce via migration 0009 if and when a real consumer is specified. YAGNI |
| Doctrine becomes outdated as new specs add new stores | Medium | Medium | M2 includes a check in `ai-eng doctor` that warns when a new `.json` or `.db` file appears under `.ai-engineering/state/` without a doctrine entry |
| `state.db PRAGMA incremental_vacuum` interference (per spec-135 R9) | Low | Low | Already mitigated: vacuum runs only at SessionEnd per [spec.md:153](.ai-engineering/specs/spec.md:153) |

## 12. References

External evidence supporting the architectural choices in §4:

**Polyglot persistence**
- [1] Martin Fowler, "Polyglot Persistence" (2011): https://martinfowler.com/bliki/PolyglotPersistence.html — coins the term; argues "any decent sized enterprise will have a variety of different data storage technologies for different kinds of data."
- [2] Fowler & Sadalage, *NoSQL Distilled* (2012): https://martinfowler.com/books/nosql.html — per-data-type optimization.
- [3] Fowler, "The future is: NoSQL Databases Polyglot Persistence" infodeck: https://martinfowler.com/articles/nosql-intro-original.pdf — explicit on the cost side (operational surface).

**Append-only logs + hash chains**
- [4] Hash-chain primitive walkthrough: https://dev.to/veritaschain/building-a-tamper-evident-audit-log-with-sha-256-hash-chains-zero-dependencies-h0b
- [5] Git's commit graph as the canonical example: https://graphite.com/guides/git-hashing — "Git's history is tamper-evident in a practical sense."
- [6] Sigstore Rekor (transparency log, Trillian-backed): https://docs.sigstore.dev/logging/overview/ — "every entry holds a cryptographic reference to all previous entries."
- [7] Hyperledger Fabric block headers: https://hyperledger-fabric.readthedocs.io/en/release-2.2/ledger.html
- [8] Linux auditd append-only stream: https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/html/security_guide/sec-understanding_audit_log_files
- [9] LSM-tree vs B-tree write amplification (foundational reason audit logs prefer NDJSON over RDBMS): https://tikv.org/deep-dive/key-value-engine/b-tree-vs-lsm/ — "tiered LSM-tree < leveled LSM-tree < B-tree."

**Event sourcing vs CQRS**
- [10] Fowler on Event Sourcing: https://martinfowler.com/eaaDev/EventSourcing.html — events are SoT; state is projection.
- [11] Fowler on CQRS: https://martinfowler.com/bliki/CQRS.html — "for most systems CQRS adds risky complexity."
- [12] Microsoft Learn Event Sourcing trade-offs: https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing — "complex pattern that introduces significant trade-offs."
- [13] Greg Young on validation under eventual consistency: https://codeopinion.com/greg-young-answers-your-event-sourcing-questions/

**SQLite operational characteristics**
- [14] SQLite WAL semantics: https://sqlite.org/wal.html — concurrent readers + serialized writer; same-host requirement.
- [15] SQLite "When To Use": https://sqlite.org/whentouse.html — "unsuitable for workloads with heavy concurrent writes."
- [16] SQLite STRICT tables (3.37+): https://www.sqlite.org/stricttables.html — per-column type enforcement (closes the historic type-affinity hole).

**Configuration as code**
- [17] Twelve-Factor App Factor III "Config": https://12factor.net/config — "config varies substantially across deploys, code does not."

**Markdown as Source of Truth**
- [18] Michael Nygard, "Documenting Architecture Decisions" (2011): https://github.com/joelparkerhenderson/architecture-decision-record/blob/main/locales/en/templates/decision-record-template-by-michael-nygard/index.md — ADR template.
- [19] Fowler on ADRs: https://martinfowler.com/bliki/ArchitectureDecisionRecord.html — "lightweight markup ... easily read and diffed just like any code."
- [20] Rust RFC process (markdown canonical): https://rust-lang.github.io/rfcs/0002-rfc-process.html
- [21] Write the Docs "Docs as Code" philosophy: https://www.writethedocs.org/guide/docs-as-code/

**Reference frameworks**
- [22] Terraform backends (state-as-artifact, swappable backend): https://developer.hashicorp.com/terraform/language/state/backends
- [23] dbt manifest.json same-file dual-write hazard: https://docs.getdbt.com/reference/node-selection/state-comparison-caveats — direct precedent for the silent-drift class of bug.
- [24] Ansible no-central-state philosophy: https://docs.ansible.com/ansible/latest/plugins/cache.html
- [25] Pulumi backend interface: https://www.pulumi.com/docs/iac/concepts/state-and-backends/
- [26] Kubernetes etcd as SoT (separation of intent and observed state): https://www.kubenatives.com/p/kubernetes-control-plane-architecture
- [27] Jenkins XML + JCasC parallel surfaces: https://www.jenkins.io/doc/book/managing/casc/

**Schema drift in dual-write systems**
- [28] Pydantic JSON Schema generation (Python contract toolchain): https://docs.pydantic.dev/latest/api/json_schema/

## 13. Glossary

- **Article-III** — CONSTITUTION.md §13.1 audit-chain immutability rule; `framework-events.ndjson` with `prev_event_hash` is the canonical, tamper-evident audit log.
- **Derived cache** — a store that is populated by an explicit, named, idempotent rebuild command from a canonical source. Drift between rebuilds is acceptable and bounded; the store is never written by production code paths.
- **Hot path** — code that executes on every operator action. Specifically: PreToolUse, PostToolUse, UserPromptSubmit hooks. Per-hook budget < 1 second.
- **Polyglot persistence** — Fowler's 2011 term for using different storage technologies for different kinds of data within one application.
- **SSOT-PD** (Single Source of Truth Per Datum) — the core doctrine: every piece of framework state has exactly one canonical store; all other copies are explicitly labelled derived caches or bugs.
- **Tier** — one of four storage primitives: Tier 1 (NDJSON audit), Tier 2 (SQLite lifecycle), Tier 3 (JSON config), Tier 4 (Markdown human-authored).
- **Derived projection** — synonym for derived cache, used specifically when the cache mirrors all rows of a canonical store (e.g. `state.db.events` projecting `framework-events.ndjson`).
- **Cold path** — code that runs on operator-explicit actions (spec approval, install, risk acceptance). Budget is operator patience (seconds to minutes), not hook timeouts.

## 14. Acceptance

Checklist version of §7. Spec phase confirms; implementation phase ticks off.

- [ ] `docs/persistence-doctrine.md` exists with the four tiers and SSOT-PD rule.
- [ ] CONSTITUTION.md has a hard rule referencing the doctrine.
- [ ] CLAUDE.md §0 points to the doctrine, not the empty `state.db.decisions` table.
- [ ] All five IDE mirrors regenerated (AGENTS.md, GEMINI.md, .github/copilot-instructions.md, .codex/, .cursor/ if any) byte-equivalent.
- [ ] `_insert_events_row` deleted from source tree.
- [ ] `decision-store.json` write removed from `repository.save_decisions`.
- [ ] `audit-index.sqlite` legacy file and `_LEGACY_INDEX_REL` constant removed.
- [ ] `runtime-stop.py:474` reads `state.db` not legacy index file.
- [ ] Current Claude Code session hook-emit gap (Bug 5) diagnosed and either fixed or upstream-reported.
- [ ] `state.db.decisions` populated after `/ai-brainstorm` approval (manual test).
- [ ] `state.db.install_steps` populated after `ai-eng install` (manual test).
- [ ] `state.db.ownership_map` populated after `ai-eng ownership import` (manual test).
- [ ] `state.db.events` populated by SessionEnd rebuild (instrumented test).
- [ ] `framework-events.ndjson` rotates at 100k lines or 50 MB.
- [ ] `hooks_integrity` decision resolved (table dropped OR runtime writer landed).
- [ ] Contract test `test_sql_writer_schemas.py` exists and passes.
- [ ] Contract test for "no SQL on hot path" exists and passes.
- [ ] `ai-eng doctor --check state-db` reports populated table counts and freshness.
- [ ] CHANGELOG.md documents all removals.
- [ ] `/ai-verify` returns GO on the resulting PR.
- [ ] Spec phase has resolved every Open Decision (OD-1 through OD-6).
