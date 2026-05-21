---
execution_route:
  version: 1
  spec: spec-148
  executor: autopilot
  automation: autopilot
  concern_count: 9
  estimated_files: 115
  reason: "Unified spec-148: retire state.db (per-datum strangler across installer/update/migrations/~15 readers/3 hooks/audit CLI) + obvious-by-default conventions (triggers, branch-cleanup, deterministic STOP, §10.x/naming/suppression CI). ~115 files, 9 waves. Multi-concern + large → autopilot. Operator launches; may pause before the gated SQLite deletion (Wave P5)."
  safe_next_command: "/ai-autopilot"
status: approved
pipeline: full
spec: spec-148
title: Plan — Files-only persistence + obvious-by-default conventions
---

# Plan — spec-148 (unified)

## Summary

Nine waves on branch `spec-147-wave-1` / PR #532. **Part A (P1-P6): files-only persistence** via per-datum strangler — migrate each datum's read/write to its file SoT FIRST (reversible, `state.db` still present), retire the cross-OS SQLite hot-path reads early, do the hard install-state reversal as its own wave, then DELETE the SQLite layer LAST behind a fail-loud export→verify→delete migration (PAUSE for operator approval). **Part B (W7-W9): obvious-by-default conventions** carried from spec-147 Waves 3-5 (triggers, branch-cleanup, deterministic STOP, poka-yoke CI). Each wave green before the next; the SKILL.md-touching waves (P6, W7, W9) are serialized so mirror regen never collides.

## Pipeline classification

`full` — ~115 files, 9 concerns. Executor route: `autopilot` (frontmatter). PAUSE before Wave P5 (irreversible SQLite deletion). Operator may run directly per the spec-147 rogue-agent incident.

## Architecture

Pattern: **per-datum strangler** (Part A) + **convention poka-yoke** (Part B). Files-first persistence (research [1][2]); NDJSON + SHA-256 hash chain for audit (research [5][6]). Boundaries: `state/` (delete SQLite, keep file IO + NDJSON; collapse Repository/Service to file-backed wrappers), `cli_commands/audit_cmd.py` (NDJSON), `installer/`+`updater/` (files + export migration), hooks (drop sqlite), `.claude/skills`+`agents`+`CLAUDE.md`/`CANONICAL.md`+`docs/persistence-doctrine.md` (rewrite + mirror regen), `tests/**`.

## Wave DAG

```
P1 events/audit ─► P2 decisions/risk ─► P3 ownership ─► P4 install+capabilities ─► P5 DELETE layer (GATED) ─► P6 persistence docs/tests
                                                                                                                   │
                                                                          W7 one-obvious-way ─► W8 deterministic-done ─► W9 poka-yoke
```
Part A is strictly sequential (each leaves `state.db` present + reversible until P5). Part B (W7-W9) runs after P6 so all SKILL.md/mirror edits serialize (P6 persistence-ref edits → W7 trigger edits → W9 §10.x edits). W8 (verify/quality code) is mirror-light and may overlap W7.

## PART A — Files-only persistence

### Phase P1 — Events/audit off SQLite (D-148-05, D-148-06)
Retire hot-path + cross-OS SQLite reads first.
- [ ] T-P1.1 RED: `audit tokens`/`replay`/`otel-export` produce correct output from `framework-events.ndjson` (no SQLite). Files: `tests/unit/cli/test_audit_*.py`. §10.5
- [ ] T-P1.2 GREEN: reimplement those as NDJSON scans; remove `audit query`+`audit index` (fail-loud "removed — use `audit tokens`" stub for `query`). Files: `cli_commands/audit_cmd.py`, `state/audit_index.py` (del), `state/audit_replay.py`, `state/audit_otel_export.py`. §10.1
- [ ] T-P1.3 RED+GREEN: hooks (`runtime-stop.py`, `runtime-session-end.py`, `session_bootstrap.py` + templates) drop `sqlite3`/`state.db` → NDJSON/JSON scans (mtime-cached, tail-N bounded for hot-path budget); regenerate hooks-manifest. Files: those + `tests/unit/hooks/test_runtime_stop_session_rollup.py`, `test_state_db_incremental_vacuum.py` (del/rewrite). §10.8 §10.5
- [ ] Gate: `audit verify` green; hot-path <1s/<5s preserved. **P1 acceptance**: zero sqlite reads in hooks + audit-query path.

### Phase P2 — Decisions + risk off SQLite (D-148-02, D-148-03)
`decision-store.json` sole SoT (already carries the hash chain).
- [ ] T-P2.1 RED: decision read/write round-trips through `decision-store.json`; risk = decision record; `audit verify --decisions` verifies the file chain. Files: `tests/unit/test_decision_store.py`, `test_cli_decisions.py`, `cli/test_decision_backfill.py`. §10.5
- [ ] T-P2.2 GREEN: collapse `DurableStateRepository`/`StateService` to file-backed (D-148-07); repoint decision readers/writers; remove the state.db dual-write. Files: `state/repository.py`, `state/service.py`, `cli_commands/decisions_cmd.py`, `risk_cmd.py`, `brainstorm/spec_approval.py`, `policy/checks/risk.py`, `commands/workflows.py`, `maintenance/report.py`, `policy/orchestrator.py`. §10.4 §10.8
- [ ] T-P2.3 GREEN: rewrite the ~6 decision/risk SQLite-seeding tests to seed `decision-store.json` (test_gate_skip_accepted, decision_writer_integration, gates/coverage/gap-fillers risk tests). §10.5
- [ ] Gate: `ai-eng decision *`, `ai-eng risk *` green against the file. **P2 acceptance**: decisions/risk one file SoT, no dual-write.

### Phase P3 — Ownership off SQLite (D-148-02)
`ownership-map.json` sole SoT (repo already reads it first — collapse split-brain).
- [ ] T-P3.1 RED: ownership read/write + `ownership import` + `ai-eng update` round-trip through `ownership-map.json`. Files: `tests/unit/cli/test_ownership_import.py`, `state/test_ownership_state_db_read.py` (rewrite), `installer/test_phases_state_upserts.py`. §10.5
- [ ] T-P3.2 GREEN: repoint ownership readers/writers to JSON; installer writes (stop deleting) `ownership-map.json`; `updater/service.py` reads it; drop state_db ownership fns. §10.4
- [ ] Gate: `ai-eng update` ownership flow green. **P3 acceptance**: ownership one file SoT.

### Phase P4 — Install-state + capabilities off SQLite (D-148-04, D-148-08) — HARDEST
Reinstate writable `install-state.json` (= `InstallState` Pydantic dump); `framework-capabilities.json` rebuilt on demand. Reverses spec-125.
- [ ] T-P4.1 RED: install pipeline writes+reads `install-state.json` (singleton + steps); doctor + readiness read the file. Files: `tests/unit/state/test_install_state_table.py` (→file), `installer/test_install_steps_writer.py`, `cli/test_doctor_state_db.py` (rewrite). §10.5
- [ ] T-P4.2 GREEN: `install-state.json` writable SoT = `InstallState` model dump; installer pipeline + `service.py` + `doctor/service.py` + `detector/readiness.py` + `cli_commands/core.py` read/write the file. §10.8
- [ ] T-P4.3 GREEN: `framework-capabilities.json` rebuilt from manifest+disk on demand; readers (`manifest_coherence.py`, `context_packs.py`) read the file. §10.2
- [ ] Gate: installer e2e (`tests/e2e/test_install_pipeline.py`) green WITHOUT `state.db`. **P4 acceptance**: install/capabilities one file SoT; install creates no state.db.

### Phase P5 — DELETE the SQLite layer + export migration (D-148-01, D-148-09) — GATED/IRREVERSIBLE
After P1-P4 no datum reads SQLite. **PAUSE for operator approval before deletion.**
- [ ] T-P5.1 RED: `ai-eng update` exports state.db-only data (install_state/steps, unmirrored decisions) to files, VERIFIES, then deletes `state.db`(+wal/shm) directly (no `.bak`); idempotent; no-op when absent; fail-loud (no delete) on export/verify failure. Files: `tests/unit/updater/test_state_db_export_migration.py` (new). §10.5
- [ ] T-P5.2 GREEN: implement export→verify→delete in `updater/service.py`. §10.6
- [ ] T-P5.3 GREEN: delete `state/state_db.py`, `state/migrations/**`, `_runner.py`; finish collapsing Repository/Service file-backed; remove every framework `sqlite3` import. CHANGELOG hard-delete + spec-123/125/132 reversal note. §10.2
- [ ] T-P5.4 RED+GREEN: `tests/architecture/test_no_sqlite.py` asserts no `import sqlite3` / `state.db` in src+hooks (replaces `test_no_sql_on_hot_path.py`). §10.5
- [ ] Gate: full suite green; fresh `install` + `update` over a pre-existing state.db fixture both green. **P5 acceptance**: G1 — no SQLite anywhere.

### Phase P6 — Persistence doctrine + docs/skills/tests (D-148-09/G9)
- [ ] T-P6.1 GREEN: rewrite `docs/persistence-doctrine.md` to files-only (NDJSON audit / JSON-YAML records+config / Markdown); update `tests/unit/specs/test_persistence_doctrine_contract.py`. §10.7
- [ ] T-P6.2 GREEN: update `state.db` refs in `CANONICAL.md` (15/21/97/265) + the ~26 skills + ~6 agents citing `state.db.decisions` → `decision-store.json`; `python scripts/sync_command_mirrors.py`. §10.4 §10.7
- [ ] T-P6.3 GREEN: delete/rewrite remaining SQLite tests (migration, lazy-bootstrap, connection-pragma, db-migration integration); update ~57 string-ref tests. §10.5
- [ ] Gate: `sync_command_mirrors --check` clean; grep shows zero stale `state.db` doc claims. **P6 acceptance**: G9.

## PART B — Obvious-by-default conventions (from spec-147 W3-5, adapted)

### Phase W7 — One obvious way (D-148-11, D-148-12)
- [ ] T-W7.1 GREEN: de-collide contested trigger phrases across `.claude/skills/{ai-prose,ai-marketing,ai-verify,ai-governance,ai-security,ai-explore,ai-explain,ai-onboard,ai-code,ai-build}/SKILL.md`; assign each phrase to one skill, others cross-reference; no merges; `sync_command_mirrors.py`. Gate: no listed phrase in >1 description. §10.3 §10.7
- [ ] T-W7.2 GREEN: surface `ai-spec-draft` in CLAUDE.md §11 chain; state ai-code(subcomponent) vs ai-build(gateway) boundary; regen mirrors. §10.7
- [ ] T-W7.3 RED: `tests/architecture/test_branch_cleanup_single_impl.py` asserts one branch-cleanup import path. §10.5
- [ ] T-W7.4 GREEN: delegate `maintenance branch-cleanup` → `cleanup branches` (`maintenance.py:123-149`, `cli_factory.py:414`); CHANGELOG; no shim. Gate: T-W7.3 passes. §10.4 §10.1
- [ ] **W7 acceptance**: G6 (one obvious surface; surface count unchanged).

### Phase W8 — Deterministic done (D-148-13)
- [ ] T-W8.1 RED: every verify Finding carries `method: deterministic|llm`. Files: `tests/unit/test_verify_service.py`. §10.5
- [ ] T-W8.2 GREEN: add `method` to the Finding model + assembly (tool runners=deterministic, verifier-acceptance=llm); document in `.claude/skills/ai-verify/SKILL.md` contract; regen mirrors. §10.3 §10.7
- [ ] T-W8.3 RED+GREEN: make quality.md Step 2d condition 4 deterministic-or-advisory; replay test: same diff → same STOP verdict. Files: `.claude/skills/ai-build/handlers/quality.md` + replay test. §10.6 §10.5
- [ ] **W8 acceptance**: G7 (reproducible STOP; method-tagged findings).

### Phase W9 — Poka-yoke conventions (D-148-14..17)
- [ ] T-W9.1 GREEN: backfill §10.x into the ~22 Workflow-without-citation skills; regen mirrors. §10.7
- [ ] T-W9.2 RED+GREEN: `tests/architecture/test_workflow_principle_citation.py` — Workflow ⇒ `§10.\d` (after T-W9.1). §10.5
- [ ] T-W9.3 GREEN: codify naming grammar (`ai-` + lowercase-kebab + verb|noun) in `ai-scaffold` + CONSTITUTION.md; `tests/architecture/test_skill_naming_grammar.py`; confirm zero renames; regen mirrors. §10.7
- [ ] T-W9.4 RED+GREEN: `cleanup branches` no-flag deletes nothing (plan + confirm). Files: `tests/unit/test_cleanup.py`, `cli_commands/cleanup.py:257-260,297-300`. §10.7 §10.5
- [ ] T-W9.5 RED+GREEN: nosemgrep suppression without dec_id fails allowlist load; non-security empty dec_id warns until 2026-07-10; author DECs for current nosemgrep entries. Files: `.ai-engineering/suppression-allowlist.yml`, `no_suppression/` loader, `tests/unit/test_suppression_allowlist.py`. §10.8 §10.6
- [ ] **W9 acceptance**: G8 (conventions CI-enforced; destructive verbs dry-run-by-default).

## Cross-cutting gates (every wave)
- CHANGELOG documents each hard-delete + behavior change; zero shims (G9); record the spec-123/125/132 reversal.
- Canonical-payload / SKILL.md edits → `scripts/sync_command_mirrors.py`; `--check` clean before PR.
- Hot-path budgets preserved (<1s/<5s); hooks-manifest regenerated after hook edits.
- One file SoT per datum; no dual-write reintroduced. SKILL.md-touching waves (P6→W7→W9) serialized for mirror regen.

## Self-review (§10.7) — 2 iterations
- **Iter 1** — Sequenced hot-path/cross-OS SQLite reads into P1 (retire Windows-WAL liability before the bulk migration); install-state reversal isolated in P4 with an e2e gate before deletion (P5). Resolved.
- **Iter 1** — Serialized the three SKILL.md-touching waves (P6 persistence refs → W7 triggers → W9 §10.x) to avoid mirror-regen collisions. Resolved.
- **Iter 2** — P5 deletion gated/PAUSED behind fail-loud export→verify→delete; each P1-P4 wave leaves state.db present + reversible. TDD pairs present; Part B carries spec-147's approved decisions. No remaining concerns.

## Next
Operator runs **`/ai-autopilot`** (executor: autopilot — 9 concerns, ~115 files, all on PR #532). PAUSE before Wave P5 (SQLite deletion). Resolve the 2 spec Open Questions (exact phrase→skill assignments; `otel-export` reimplement-vs-drop) during planning of W7 / P1.
