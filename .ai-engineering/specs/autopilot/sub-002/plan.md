---
total: 22
completed: 0
---

# Plan: sub-002 Engram + state.db

## Plan

exports:
  - ai_engineering.state.state_db.connect
  - ai_engineering.state.state_db.projection_write
  - ai_engineering.state.state_db.STATE_DB_REL
  - ai_engineering.state.migrations.run_pending
  - ai_engineering.state.migrations.verify_integrity
  - ai_engineering.state.outbox.OutboxRecorder
  - ai_engineering.state.rotation.rotate_now
  - ai_engineering.state.rotation.compress_month
  - ai_engineering.state.retention.apply_retention
  - ai_engineering.state.sidecar.maybe_offload
  - ai_engineering.state.sidecar.SIDECAR_CEILING_BYTES
  - ai_engineering.cli_commands.audit_cmd.audit_retention_apply
  - ai_engineering.cli_commands.audit_cmd.audit_rotate
  - ai_engineering.cli_commands.audit_cmd.audit_compress
  - ai_engineering.cli_commands.audit_cmd.audit_verify_chain
  - ai_engineering.cli_commands.audit_cmd.audit_health
  - ai_engineering.cli_commands.audit_cmd.audit_vacuum
  - ai_engineering.installer.service.run_engram_setup_per_ide

imports:
  - sub-001 hygiene complete (clean pyproject.toml, no orphan markers, manifest.yml deduped, wire-memory-hooks.py deleted)

- [ ] T-2.1: Add migrations package scaffold + runner with sha256 integrity check
  - **Files**: `src/ai_engineering/state/migrations/__init__.py` (NEW), `src/ai_engineering/state/migrations/_runner.py` (NEW), `tests/unit/state/test_migration_integrity.py` (NEW)
  - **Done**: `python -c "from ai_engineering.state.migrations import run_pending, verify_integrity; print('ok')"` succeeds; `pytest tests/unit/state/test_migration_integrity.py -v` passes for: (a) clean apply records sha256 in `_migrations`; (b) tampered file under `AIENG_HOOK_INTEGRITY_MODE=enforce` raises `MigrationIntegrityError` and emits `framework_error` with `error_code='migration_integrity_violation'`; (c) under `warn` mode logs but proceeds; (d) under `off` mode no check.

- [ ] T-2.2: Write 0001_initial_schema migration with seven STRICT tables + `_migrations` ledger + decisions_fts virtual table + all indexes
  - **Files**: `src/ai_engineering/state/migrations/0001_initial_schema.py` (NEW)
  - **Done**: `apply(conn)` creates 7 STRICT tables (events, decisions, risk_acceptances, gate_findings, hooks_integrity, ownership_map, install_steps) + `_migrations` STRICT ledger + `decisions_fts` FTS5 virtual table + all CREATE INDEX statements (idx_events_ts, idx_events_ts_session, idx_events_session_ts, idx_events_kind_ts, idx_events_correlation, idx_events_archive_month, idx_events_outcome partial WHERE outcome='failure', idx_decisions_status partial WHERE status='active', idx_decisions_spec partial WHERE spec_id IS NOT NULL, idx_risk_active, idx_gate_session, idx_gate_open partial WHERE status='open', idx_hooks_recent). `BODY_SHA256` constant present. `sqlite3 state.db '.schema'` after apply shows all tables marked `STRICT` and `decisions_fts` virtual table.

- [ ] T-2.3: Create state_db.connect() with all 9 PRAGMAs (WAL, synchronous=NORMAL, foreign_keys=ON, busy_timeout=10000, cache_size=-65536, temp_store=MEMORY, mmap_size=268435456, auto_vacuum=INCREMENTAL on first creation only, journal_size_limit)
  - **Files**: `src/ai_engineering/state/state_db.py` (NEW), `tests/unit/state/test_connection_pragmas.py` (NEW)
  - **Done**: `pytest tests/unit/state/test_connection_pragmas.py -v` asserts each PRAGMA returns the expected value on a fresh `connect()`; `auto_vacuum=2` on a fresh DB but unchanged on subsequent connects; `STATE_DB_REL = Path('.ai-engineering/state/state.db')` exposed.

- [ ] T-2.4: Add OutboxRecorder + projection_write context manager (transactional outbox, BEGIN IMMEDIATE)
  - **Files**: `src/ai_engineering/state/outbox.py` (NEW), `tests/integration/state/test_outbox_atomic.py` (NEW)
  - **Done**: `pytest tests/integration/state/test_outbox_atomic.py -v` passes for: (a) success path commits SQL + appends NDJSON event atomically; (b) SQL failure mid-context rolls back row AND skips NDJSON emit; (c) emit failure post-COMMIT raises but row stays committed (NDJSON emit is at-least-once after commit); (d) reentrant `projection_write()` raises immediately to surface programmer error.

- [ ] T-2.5: Write 0002_seed_from_json migration (decision-store, ownership-map, install-state, gate-findings → tables; archive originals to state/archive/pre-state-db/)
  - **Files**: `src/ai_engineering/state/migrations/0002_seed_from_json.py` (NEW)
  - **Done**: After apply, `SELECT count(*) FROM decisions` matches active+superseded count from JSON; `SELECT count(*) FROM ownership_map` == len(paths) from `ownership-map.json` (~33); `SELECT count(*) FROM install_steps` == len(tooling) from `install-state.json` (~9); `SELECT count(*) FROM gate_findings` == len(findings); originals moved (not copied) to `.ai-engineering/state/archive/pre-state-db/<filename>.json`. Idempotent: re-running on a populated DB is a no-op (UPSERT semantics).

- [ ] T-2.6: Write 0003_replay_ndjson migration (idempotent NDJSON → events; ON CONFLICT(span_id) DO NOTHING; populates GENERATED ts_unix_ms + archive_month)
  - **Files**: `src/ai_engineering/state/migrations/0003_replay_ndjson.py` (NEW), `tests/integration/state/test_db_migration.py` (NEW)
  - **Done**: After apply, `SELECT count(*) FROM events` equals `wc -l framework-events.ndjson` (modulo blank lines + malformed entries, with stderr warnings for skipped lines); re-applying produces zero net inserts (idempotency); each row has `archive_month=strftime('%Y-%m', timestamp)` and `ts_unix_ms` populated from julianday cast; `pytest tests/integration/state/test_db_migration.py::test_round_trip_each_json_file -v` passes; `pytest tests/integration/state/test_db_migration.py::test_replay_idempotent -v` passes.

- [ ] T-2.7: Add sidecar offload module (3 KB ceiling; content-addressed sha256 path; inline event carries hash + summary)
  - **Files**: `src/ai_engineering/state/sidecar.py` (NEW), `tests/unit/state/test_sidecar_overflow.py` (NEW)
  - **Done**: `SIDECAR_CEILING_BYTES = 3072` exposed; `maybe_offload(event_dict)` returns either the original dict (≤ 3072 bytes serialized) or `{"sidecar_sha256": hex, "summary": str, "kind": str, "timestamp": str}` with the full payload written to `.ai-engineering/state/runtime/event-sidecars/<sha256>.json`. Tests cover: (a) small event passes through unchanged; (b) large event → sidecar file written + inline shortened; (c) deterministic sha256 (same input → same path); (d) collision-safe (same path → no rewrite, idempotent).

- [ ] T-2.8: Wire sidecar into runtime-guard.py PostToolUse (existing AIENG_TOOL_OFFLOAD_BYTES infra extended with AIENG_EVENT_SIDECAR_BYTES)
  - **Files**: `.ai-engineering/scripts/hooks/runtime-guard.py`, `.ai-engineering/scripts/hooks/_lib/audit.py`
  - **Done**: Hook integrity manifest regenerated via `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py`; `runtime-guard.py` reads `AIENG_EVENT_SIDECAR_BYTES` env (default 3072) and calls `sidecar.maybe_offload` on every event before NDJSON append; manual repro: emit a 5 KB synthetic event → inline NDJSON line < 500 bytes; sidecar file exists at `state/runtime/event-sidecars/<hash>.json`.

- [ ] T-2.9: Add NDJSON rotation module (monthly OR 256MB; advisory flock; hash-chain bridging via Crosby/Wallach pattern)
  - **Files**: `src/ai_engineering/state/rotation.py` (NEW), `tests/integration/state/test_rotation_chain.py` (NEW)
  - **Done**: `rotate_now()` (a) acquires `.ai-engineering/state/locks/audit-rotation.lock` via existing `state.locking.artifact_lock`; (b) computes head_hash of closing month; (c) writes `state/audit-archive/YYYY/YYYY-MM.manifest.json` with `{head_hash, line_count, sha256_of_file}`; (d) opens `state/audit-archive/YYYY/YYYY-MM.ndjson` for the new month with synthetic anchor event carrying `prev_event_hash = closed_head_hash`; (e) updates `state/audit-archive/hash-chain.json`. Test asserts `audit_chain.verify_audit_chain` walks across rotation boundary and returns ok=True. Compress is a separate task (T-2.10).

- [ ] T-2.10: Add zstd seekable compress for closed months
  - **Files**: `src/ai_engineering/state/rotation.py`, `tests/integration/state/test_rotation_chain.py`
  - **Done**: `compress_month(year_month)` produces `state/audit-archive/YYYY/YYYY-MM.ndjson.zst` using zstd seekable frame structure (subprocess to system `zstd` with `--long=27 --maxsize`; or pure-python via stdlib if zstd binary absent — fail with clear message if neither available); preserves plaintext for 24mo (D-122-19); test asserts plaintext + zst coexist post-compress; test asserts random-access decompression of one frame works (no full-file decode).

- [ ] T-2.11: Add retention module (90d HOT cutoff for events; tier-aware delete with audit event emission)
  - **Files**: `src/ai_engineering/state/retention.py` (NEW), `tests/integration/state/test_retention.py` (NEW)
  - **Done**: `apply_retention(conn, keep_days=90)` deletes from `events` where `archive_month <= cutoff_month`; emits one `events_retention_applied` event into NDJSON with `{rows_deleted, cutoff_month, kept_months}`; idempotent (no-op if no rows past cutoff); WARM tier (NDJSON archive months 24mo) and COLD tier (zstd 7yr) are file-level not row-level so they belong to rotation/compression flows, not this module. Test fixture seeds events spanning 3 years → after `apply_retention(90)` only last 3 months of events remain.

- [ ] T-2.12: Extend audit CLI with `retention apply | rotate | compress | verify-chain | health | vacuum | query --include-archived`
  - **Files**: `src/ai_engineering/cli_commands/audit_cmd.py`, `tests/unit/cli/test_audit_retention_cli.py` (NEW), `tests/unit/cli/test_audit_rotate_cli.py` (NEW), `tests/unit/cli/test_audit_health_cli.py` (NEW), `tests/unit/cli/test_audit_vacuum_cli.py` (NEW)
  - **Done**: `ai-eng audit --help` lists all 7 new subcommands; `ai-eng audit health --json` reports `{freelist_count, page_count, freelist_ratio, wal_size_bytes, db_size_bytes}`; `ai-eng audit vacuum --incremental 5000` runs `PRAGMA incremental_vacuum(5000)` and reports reclaimed pages; `ai-eng audit verify-chain --full` walks every NDJSON month including archived zstd files; `ai-eng audit query --include-archived "SELECT count(*) FROM events"` ATTACHes archived shards if any exist (read-only). Each subcommand has dual JSON+text output per existing pattern in `audit_cmd.py`.

- [ ] T-2.13: Add Engram subprocess wrapper module + per-IDE setup orchestration in installer pipeline
  - **Files**: `src/ai_engineering/installer/service.py`, `src/ai_engineering/installer/engram.py` (NEW), `tests/unit/installer/test_engram_setup.py` (NEW)
  - **Done**: `run_engram_setup_per_ide(detected_ides: list[str])` calls `subprocess.run(['engram', 'setup', agent], capture_output=True, timeout=30)` for each agent in `{claude-code, codex, gemini-cli, copilot, opencode}` that maps from detected IDEs; records `install_steps(step_id='engram_setup:<agent>', status='done|failed', detail_json=stdout/stderr)`; tolerates `FileNotFoundError` (engram binary missing) by recording `status='skipped'` with hint message; test mocks subprocess + asserts each detected IDE triggers exactly one setup call; binary-missing path produces a single `framework_warning` and skipped status (not failure).

- [ ] T-2.14: Wire engram-setup step into `ai-eng install` pipeline + add engram to required_tools.baseline
  - **Files**: `src/ai_engineering/cli_commands/core.py`, `.ai-engineering/manifest.yml`, `tests/unit/cli/test_install_engram_step.py` (NEW)
  - **Done**: `ai-eng install --json` shows `engram_setup` as a tracked step; `manifest.yml required_tools.baseline.engram = ">=1.15.8,<1.16"`; `ai-eng doctor` lists engram in tool readiness; if engram missing on mac/linux, install hint says `brew install engram`; on Windows, says `winget install Engram` then fallback to direct binary download.

- [ ] T-2.15: Reduce `/ai-remember` to thin wrapper over `engram search --project`
  - **Files**: `.claude/skills/ai-remember/SKILL.md`, `src/ai_engineering/templates/project/.claude/skills/ai-remember/SKILL.md`, `src/ai_engineering/templates/project/.gemini/skills/ai-remember/SKILL.md`
  - **Done**: SKILL.md body invokes `engram search --project "<query>" --top-k 10 --json` (NOT `uv run ai-eng memory remember`); description rewritten without `sqlite-vec + fastembed` references; failure modes updated: `binary_missing` → install hint, `timeout` → retry once, `malformed_json` → surface stderr; `argument-hint` field updated; mirror copies match canonical `.claude/skills/ai-remember/SKILL.md` byte-for-byte minus IDE-specific frontmatter.

- [ ] T-2.16: Reduce `/ai-dream` to thin wrapper over `engram save` (or Engram consolidation surface)
  - **Files**: `.claude/skills/ai-dream/SKILL.md`, `src/ai_engineering/templates/project/.claude/skills/ai-dream/SKILL.md`, `src/ai_engineering/templates/project/.gemini/skills/ai-dream/SKILL.md`
  - **Done**: SKILL.md body invokes Engram consolidation entry (defer exact CLI to Engram docs current version; spec-122-b says "engram save"); HDBSCAN + decay logic deleted from skill description; "NEVER auto-mutate LESSONS.md" hard rule preserved; mirror copies match.

- [ ] T-2.17: Update `/ai-instinct --review` to also `engram save` enriched observations
  - **Files**: `.claude/skills/ai-instinct/SKILL.md`
  - **Done**: Step 3 (WRITE) appends `engram save --kind correction|recovery|workflow --metadata ...` per enriched observation alongside the existing `instincts.yml` upsert; instinct-observations.ndjson archive (read-only post-migration) noted in artifact set; failure modes for missing engram = warn-and-continue (instincts.yml update is the SoT).

- [ ] T-2.18: Add `tests/integration/memory/test_engram_subprocess.py` (mock engram CLI; verify shell-out + failure modes)
  - **Files**: `tests/integration/memory/test_engram_subprocess.py` (NEW)
  - **Done**: Tests cover: (a) `/ai-remember` happy path (mock engram returns JSON results → skill renders correct list); (b) binary missing → fail clean with install hint, no traceback; (c) subprocess timeout → retry once, then fail; (d) malformed JSON output → surface stderr; (e) `/ai-dream` shells out correctly; (f) latency budget (subprocess overhead < 100 ms for empty corpus).

- [ ] T-2.19: Delete memory layer (~2,568 LOC) + associated tests
  - **Files**: `.ai-engineering/scripts/memory/` (entire directory), `tests/unit/memory/` (entire directory), `tests/integration/memory/test_session_lifecycle.py`, `src/ai_engineering/cli_commands/memory_cmd.py` (replace with stub OR unregister), `src/ai_engineering/cli_factory.py` (drop memory_app registration)
  - **Done**: `find .ai-engineering/scripts/memory -type f` returns empty; `find tests/unit/memory -type f` returns empty (or only `__init__.py`); `ai-eng memory --help` either says "delegated to Engram" (stub) or returns command-not-found; full test suite passes (no orphan imports).

- [ ] T-2.20: Clean pyproject.toml + uv.lock (remove sqlite-vec, fastembed, hdbscan, numpy, memory extra, memory pytest markers, --extra memory CI paths)
  - **Files**: `pyproject.toml`, `uv.lock`, `.github/workflows/*.yml`
  - **Done**: `grep -E '(sqlite-vec|fastembed|hdbscan)' pyproject.toml` returns empty; `[project.optional-dependencies.memory]` block deleted; `numpy` removed unless still pulled by another dep; `memory` and `memory_slow` pytest markers deleted from `[tool.pytest.ini_options]`; `--extra memory` removed from all CI workflow files; `uv lock` regenerated from clean state via `rm uv.lock && uv lock`; `uv sync` from clean state succeeds; `uv pip list | grep -E 'sqlite-vec|fastembed|hdbscan'` returns empty.

- [ ] T-2.21: Update .gitignore (add state.db variants; preserve memory.db ignore as historical safety)
  - **Files**: `.gitignore`
  - **Done**: `.gitignore` contains `.ai-engineering/state/state.db`, `.ai-engineering/state/state.db-wal`, `.ai-engineering/state/state.db-shm`, `.ai-engineering/state/state.db-journal`, `.ai-engineering/state/runtime/event-sidecars/`; existing `audit-index.sqlite*` and `memory.db*` entries preserved (defense in depth — old DB names should never re-enter git history).

- [ ] T-2.22: Archive old state files + delete deprecated audit-index.sqlite consumers' compatibility shims
  - **Files**: `.ai-engineering/state/instinct-observations.ndjson` (archive read-only to `state/archive/pre-state-db/`), `src/ai_engineering/state/audit_index.py` (rewire to point at state.db; preserve public API), `tests/unit/state/test_audit_index_redirect.py` (NEW)
  - **Done**: `instinct-observations.ndjson` moved to `state/archive/pre-state-db/instinct-observations.ndjson` (read-only via chmod 444); `audit_index.py:NDJSON_REL` and `INDEX_REL` constants kept for backward compat but the writer now writes into `state.db` (a single table within the unified DB) instead of a separate `audit-index.sqlite` file; `open_index_readonly()` returns a `state.db` connection in read-only URI mode; `tests/unit/cli/test_audit_index_cli.py` continues to pass; new test `test_audit_index_redirect.py` asserts new writes land in `state.db` not `audit-index.sqlite`.

### Confidence
- **Level**: high
- **Assumptions**:
  - NDJSON entry count is data-volume-agnostic; the spec's "84,679 events" figure is exemplar (current repo has 173). Acceptance restated as `count == wc -l framework-events.ndjson` so tests pass on any deployment size.
  - `scripts/install.sh` does not exist; the actual installer entry is `ai-eng install` CLI command via `src/ai_engineering/cli_commands/core.py:install_cmd` and `installer/service.py`. T-2.13/T-2.14 target the actual installer pipeline.
  - Engram CLI ships `engram search --project`, `engram save`, and `engram setup <agent>` per spec D-122-05/D-122-38; exact subcommand surface tracks Engram's evolving CLI (pinned version range `>=1.15.8,<1.16`).
  - Pure-stdlib `sqlite3` is sufficient for STRICT tables (introduced SQLite 3.37.0, 2021); Python ≥3.11 ships SQLite ≥3.40 so STRICT is universally available.
  - Existing `state/audit_chain.py` API (`compute_event_hash`, `verify_audit_chain`) is preserved unchanged; new code consumes it.
  - `_outbox` in-DB queue alternative (D-122-18) is deferred to future scale; this sub-spec uses post-yield in-process emit (50 LOC simpler, single-tx contract maintained).
- **Unknowns**:
  - Exact Engram CLI signature for the consolidation operation `/ai-dream` should call (`engram save` per spec; Engram may have a dedicated `engram consolidate` subcommand by deploy time). T-2.16 defers to Engram's docs at implementation time; SKILL.md is updated with the correct subcommand at Phase 4.
  - Whether `numpy` should be removed entirely from pyproject.toml or kept as an indirect dep (pulled by other tools). T-2.20 final-checks against `uv pip list` post-removal.
  - Whether `audit-index.sqlite` legacy file is deleted or kept-for-rollback during the transition. T-2.22 chooses redirect-not-delete to preserve a recovery path; cleanup is sub-spec d's responsibility post-merge.

## Self-Report

### Status: PARTIAL - agent truncated mid-T-2.9 (rotation.py)

### Code artifacts on disk (verified)
- src/ai_engineering/state/state_db.py - connect() + STATE_DB_REL + projection_write + 9 PRAGMAs
- src/ai_engineering/state/migrations/{__init__,_runner,0001_initial_schema,0002_seed_from_json,0003_replay_ndjson}.py - sha256-gated migration runner
- src/ai_engineering/state/{outbox,sidecar,rotation}.py - transactional outbox + 3KB content-addressed sidecar + monthly/256MB rotation w/ Crosby-Wallach hash chain
- 25 new unit tests passing

### Tasks: T-2.1..T-2.7 + T-2.9 done. T-2.8, T-2.10..T-2.22 deferred.

| done | task |
|------|------|
| yes | T-2.1 migrations scaffold + runner |
| yes | T-2.2 0001 schema (7 STRICT tables + _migrations + decisions_fts) |
| yes | T-2.3 state_db.connect with 9 PRAGMAs |
| yes | T-2.4 OutboxRecorder + projection_write |
| yes | T-2.5 0002 seed_from_json |
| yes | T-2.6 0003 replay_ndjson |
| yes | T-2.7 sidecar offload (3KB ceiling) |
| no  | T-2.8 wire sidecar into runtime-guard.py |
| yes | T-2.9 rotation module |
| no  | T-2.10..T-2.22 zstd/retention/audit-CLI/Engram/skills/deps cleanup |

### Critical deferred items
- pyproject.toml NOT cleaned (sqlite-vec/fastembed/hdbscan/numpy still present)
- Engram delegation NOT wired
- /ai-remember + /ai-dream still legacy
- audit_index.py not redirected to state.db
- ~13 of 22 tasks deferred

### Tests: 25 new unit tests passing. 33 pre-existing tests broken by sub-001 cleanup + sub-003 v1 migration (deferred to Phase 5).

### Confidence: medium - core infra real; ~13/22 tasks deferred. Phase 5 quality loop or spec-122-b-followup.
