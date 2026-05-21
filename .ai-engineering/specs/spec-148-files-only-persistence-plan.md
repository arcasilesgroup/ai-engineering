---
execution_route:
  version: 1
  spec: spec-148
  executor: autopilot
  automation: autopilot
  concern_count: 6
  estimated_files: 105
  reason: "Retiring state.db touches ~100-110 files across installer/update/migrations, ~15 src readers/writers, 3 hooks (+templates), the audit CLI, the persistence doctrine, ~26 skills + ~6 agents (+mirrors), and ~80 test files. Six independent per-datum concerns. Multi-concern + large → autopilot. (Operator may run directly per the rogue-agent incident in spec-147.)"
  safe_next_command: "/ai-autopilot"
status: draft
pipeline: full
spec: spec-148
title: Plan — Files-only persistence (retire state.db)
---

# Plan — spec-148 Files-only persistence

## Summary

Retire SQLite `state.db` by migrating each datum to its file SoT FIRST (reversible — `state.db` still present, dual-write intact), then deleting the SQLite layer + the DB file LAST behind a one-shot export migration. Sequenced by datum, each wave green before the next. The hot-path/cross-OS SQLite reads (hooks + audit) go first to retire the Windows-WAL liability early; the installer/install-state reversal (hardest) is its own wave; deletion is the gated penultimate wave; docs/skills/tests cleanup closes it out.

## Pipeline classification

`full` — cross-cutting reversal, ~105 files, 6 concerns. Executor route: `autopilot` (frontmatter). Operator may execute directly (no autonomous agents) per the spec-147 rogue-agent incident — the wave structure holds either way.

## Architecture

Pattern: **per-datum strangler migration** — move each datum's read/write to its file SoT while the DB still exists (reversible), then delete the now-unused SQLite layer. Files-first persistence (research [1][2]); NDJSON + SHA-256 hash chain for the audit/event log (research [5][6]). Module boundaries: `state/` (delete SQLite, keep file IO `io.py`/`locking.py`/NDJSON), `cli_commands/audit_cmd.py` (NDJSON-backed), `installer/`+`updater/` (files, export migration), `.ai-engineering/scripts/hooks/**` (drop sqlite), `docs/persistence-doctrine.md` + canonical/skills/agents (rewrite), `tests/**` (rewrite SQLite-seeding to files).

## Wave DAG

```
Wave 1 events/audit ──► Wave 2 decisions/risk ──► Wave 3 ownership ──► Wave 4 install-state+capabilities ──► Wave 5 DELETE layer (gated) ──► Wave 6 docs/skills/tests
```
Each wave migrates one datum to files (reversible, DB still present). Wave 5 deletes `state_db.py`/migrations/`state.db` behind the one-shot export — PAUSE for operator approval (irreversible). Wave 6 rewrites doctrine/skills/agents/mirrors + cleans tests.

## Phase 1 — Wave 1: Events/audit off SQLite (D-148-04, D-148-06)

Retire the hot-path + cross-OS SQLite reads first. Agent: build.

- [ ] T-1.1 RED: `audit tokens` by skill/agent/session computes correct rollups from `framework-events.ndjson` (no SQLite). Files: `tests/unit/cli/test_audit_tokens_cli.py`. §10.5 TDD.
- [ ] T-1.2 GREEN: reimplement `audit tokens` + `audit replay` as NDJSON scans; remove `audit query` + `audit index` (fail-loud "removed — use `audit tokens`" stub for `query`). Files: `cli_commands/audit_cmd.py`, `state/audit_index.py` (delete), `state/audit_replay.py` (NDJSON), `state/audit_otel_export.py`. §10.1 KISS.
- [ ] T-1.3 RED: stop-hook session token rollup + session-end (no vacuum) computed from NDJSON; no `sqlite3` import in hooks. Files: `tests/unit/hooks/test_runtime_stop_session_rollup.py`, `tests/unit/hooks/test_state_db_incremental_vacuum.py` (delete/rewrite). §10.5 TDD.
- [ ] T-1.4 GREEN: `runtime-stop.py`, `runtime-session-end.py`, `session_bootstrap.py` (+ `templates/` copies) drop `state.db`/sqlite reads → NDJSON/file scans (mtime-cached, tail-N bounded for hot-path budget); regenerate hooks-manifest. §10.8 Hexagonal.
- [ ] T-1.5 Gate: `audit verify` (NDJSON + decision-store chains) still green; hot-path budgets (<1s/<5s) preserved. **Wave-1 acceptance**: G4 + G5; zero sqlite reads in hooks/audit-query path.

## Phase 2 — Wave 2: Decisions + risk off SQLite (D-148-02, D-148-03)

`decision-store.json` becomes sole SoT (it already carries the hash chain). Agent: build.

- [ ] T-2.1 RED: decision read/write round-trips through `decision-store.json` only; risk acceptance = decision record; `audit verify --decisions` verifies the file chain. Files: `tests/unit/test_decision_store.py`, `tests/unit/test_cli_decisions.py`, `tests/unit/cli/test_decision_backfill.py`. §10.5 TDD.
- [ ] T-2.2 GREEN: repoint decision readers/writers to file IO; remove the state.db dual-write in `save_decisions`; remove `decision-store.json` from any control-plane staleness path. Files: `state/repository.py`, `state/service.py`, `cli_commands/decisions_cmd.py`, `cli_commands/risk_cmd.py`, `brainstorm/spec_approval.py`, `policy/checks/risk.py`, `commands/workflows.py`, `maintenance/report.py`, `policy/orchestrator.py`. §10.4 DRY.
- [ ] T-2.3 GREEN: rewrite the ~6 decision/risk SQLite-seeding tests to seed `decision-store.json`. Files: `tests/integration/test_gate_skip_accepted.py`, `tests/unit/state/test_decision_writer_integration.py`, gates/coverage/gap-fillers risk tests. §10.5 TDD.
- [ ] T-2.4 Gate: `ai-eng decision list/record/backfill`, `ai-eng risk *` all green against the file. **Wave-2 acceptance**: decisions/risk have one file SoT; no dual-write.

## Phase 3 — Wave 3: Ownership off SQLite (D-148-02)

`ownership-map.json` becomes sole SoT (repo already reads it first — collapse the split-brain). Agent: build.

- [ ] T-3.1 RED: ownership read/write + `ai-eng ownership import` + `ai-eng update` round-trip through `ownership-map.json`. Files: `tests/unit/cli/test_ownership_import.py`, `tests/unit/state/test_ownership_state_db_read.py` (rewrite), `tests/unit/installer/test_phases_state_upserts.py`. §10.5 TDD.
- [ ] T-3.2 GREEN: repoint ownership readers/writers to the JSON; installer writes `ownership-map.json` (stop deleting it post-upsert); `updater/service.py` reads it. Files: `state/repository.py` (load_ownership already JSON), `state_db.py` ownership fns (delete), `installer/phases/state.py`, `updater/service.py`, `cli_commands/ownership_cmd.py`. §10.4 DRY.
- [ ] T-3.3 Gate: `ai-eng update` ownership flow green against the file. **Wave-3 acceptance**: ownership one file SoT.

## Phase 4 — Wave 4: Install-state + capabilities off SQLite (D-148-02, D-148-08) — HARDEST

Reinstate writable `install-state.json`; `framework-capabilities.json` rebuilt on demand. Reverses spec-125. Agent: build.

- [ ] T-4.1 RED: install pipeline writes `install-state.json` (singleton + per-step) and reads it back; doctor + readiness read the file. Files: `tests/unit/state/test_install_state_table.py` (rewrite → file), `tests/unit/installer/test_install_steps_writer.py`, `tests/unit/cli/test_doctor_state_db.py` (rewrite). §10.5 TDD.
- [ ] T-4.2 GREEN: reinstate `install-state.json` as the writable SoT (resolve shape in OQ); installer pipeline + `service.py` + `doctor/service.py` + `detector/readiness.py` + `cli_commands/core.py` read/write the file. Files: those + `installer/phases/state.py`, `installer/phases/pipeline.py`. §10.8 Hexagonal.
- [ ] T-4.3 GREEN: `tool_capabilities` → `framework-capabilities.json` rebuilt from manifest + disk on demand; readers (`validator/categories/manifest_coherence.py`, `state/context_packs.py`) read the file. §10.2 YAGNI.
- [ ] T-4.4 Gate: installer e2e (`tests/e2e/test_install_pipeline.py`) green WITHOUT `state.db` present. **Wave-4 acceptance**: install/capabilities one file SoT; install creates no `state.db`.

## Phase 5 — Wave 5: Delete the SQLite layer + one-shot export migration (D-148-01, D-148-05, D-148-09) — GATED/IRREVERSIBLE

After Waves 1-4, no datum reads SQLite. Delete the layer behind a safe export. **PAUSE for operator approval before deletion.** Agent: build.

- [ ] T-5.1 RED: `ai-eng update` exports any `state.db`-only data (install_state/steps, unmirrored decisions) to files then deletes `state.db`(+wal/shm); idempotent; no-op when absent; backs up to `state.db.bak` first; fails loud (no delete) on export error. Files: `tests/unit/updater/test_state_db_export_migration.py` (new). §10.5 TDD.
- [ ] T-5.2 GREEN: implement the export-then-delete step in `updater/service.py`. §10.6 SDD.
- [ ] T-5.3 GREEN: delete `state/state_db.py`, `state/migrations/**`, `state/migrations/_runner.py`; collapse/delete `DurableStateRepository`/`StateService` SQLite paths (per OQ); remove every `sqlite3` import for framework state. CHANGELOG hard-delete entries. §10.2 YAGNI.
- [ ] T-5.4 RED+GREEN: CI guard `tests/architecture/test_no_sqlite.py` asserts no `import sqlite3` / `state.db` in `src/` + hooks (replaces `test_no_sql_on_hot_path.py`). §10.5 TDD.
- [ ] T-5.5 Gate: full suite green; fresh `ai-eng install` + `ai-eng update` on a pre-existing `state.db` fixture both green. **Wave-5 acceptance**: G1 — no SQLite anywhere.

## Phase 6 — Wave 6: Doctrine + skills/agents + mirrors + test cleanup (D-148-07)

Reconcile every doc/skill/agent claim. Agent: build.

- [ ] T-6.1 GREEN: rewrite `docs/persistence-doctrine.md` to the files-only model (NDJSON audit / JSON-YAML records+config / Markdown); update `tests/unit/specs/test_persistence_doctrine_contract.py`. §10.7 Clean Code.
- [ ] T-6.2 GREEN: update `state.db` references in `CANONICAL.md` (lines 15/21/97/265) → files; regenerate root + template mirrors via `scripts/sync_command_mirrors.py`. §10.4 DRY.
- [ ] T-6.3 GREEN: update the ~26 skills + ~6 agents citing `state.db.decisions` → `decision-store.json`; regenerate `.codex/`/`.gemini/` skill/agent mirrors. §10.7 Clean Code.
- [ ] T-6.4 GREEN: delete/rewrite remaining SQLite tests (migration, lazy-bootstrap, connection-pragma, db-migration integration); update the ~57 string-ref tests. §10.5 TDD.
- [ ] T-6.5 Gate: `sync_command_mirrors --check` clean; full suite green; grep shows zero stale `state.db` doc claims. **Wave-6 acceptance**: G6 — every doc claim resolves to a file fact.

## Cross-cutting gates (every wave)

- CHANGELOG documents each hard-delete + behavior change; zero shims (G8). Record the reversal of spec-123/125/132.
- Canonical-payload / SKILL.md edits → `scripts/sync_command_mirrors.py`; `--check` clean before PR.
- Hot-path budgets preserved (pre-commit <1s, pre-push <5s); hooks-manifest regenerated after hook edits.
- One file SoT per datum; no dual-write reintroduced.

## Self-review (§10.7) — 2 iterations

- **Iter 1** — Sequenced hot-path/cross-OS SQLite reads (hooks/audit) into Wave 1 so the Windows-WAL liability retires before the bulk migration. Resolved.
- **Iter 1** — Isolated install-state (the spec-125 reversal, hardest) into its own wave (4) with an e2e gate before deletion. Resolved.
- **Iter 2** — Deletion (Wave 5) is gated/PAUSED + behind a fail-loud export-then-delete with `.bak`; verified each prior wave leaves `state.db` present + reversible. TDD pairs present. No remaining concerns.

## Next

Operator approves, then `/ai-autopilot` (or executes directly per the spec-147 incident). PAUSE before Wave 5 deletion. Resolve the 4 spec Open Questions (install-state shape, audit-query scope, export retention, repository fate) during planning/Wave 4-5.
