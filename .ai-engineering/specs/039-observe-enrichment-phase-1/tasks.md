---
spec: "039"
total: 46
completed: 46
last_session: "2026-03-09"
next_session: "CLOSED"
---

# Tasks — Observe Enrichment Phase 1

### Phase 0: LLM-Driven Spec Creation [M] ✅
- [x] 0.1 Move `_next_spec_number()` and `_slugify()` from `spec_save.py` to `src/ai_engineering/lib/parsing.py`
- [x] 0.2 Delete `src/ai_engineering/cli_commands/spec_save.py`
- [x] 0.3 Delete `tests/unit/test_spec_save.py`
- [x] 0.4 Remove `spec save` registration from `src/ai_engineering/cli_factory.py`
- [x] 0.5 Create `tests/unit/test_spec_helpers.py` — tests for `next_spec_number()` and `slugify()` in lib/parsing.py
- [x] 0.6 Update `.ai-engineering/agents/plan.md` — new Spec-as-Gate Pattern (LLM writes via Write tool, not CLI)
- [x] 0.7 Update `.ai-engineering/skills/spec/SKILL.md` — remove CLI-Driven Path section, make manual procedure primary
- [x] 0.8 Update `.ai-engineering/skills/plan/SKILL.md` — remove reference to `ai-eng spec save`

### Phase 1: VCS Context [S] ✅
- [x] 1.1 Create `src/ai_engineering/vcs/repo_context.py` — RepoContext dataclass, URL parsing (GitHub SSH/HTTPS, ADO modern/user-prefix/legacy/SSH), module-level cache, fail-open, uses run_git
- [x] 1.2 Create `src/ai_engineering/git/context.py` — GitContext dataclass (branch, commit_sha short 8), module-level cache, uses run_git
- [x] 1.3 Create `tests/unit/test_repo_context.py`
- [x] 1.4 Create `tests/unit/test_git_context.py`

### Phase 2: AuditEntry Extension [S] ✅
- [x] 2.1 Add 7 optional fields to AuditEntry in `src/ai_engineering/state/models.py`: vcs_provider, vcs_organization, vcs_project, vcs_repository, branch, commit_sha, session_id
- [x] 2.2 Inject get_repo_context + get_git_context in `_emit()` in `src/ai_engineering/state/audit.py`

### Phase 3: Update Write Sites [M] ✅
- [x] 3.1 Update `src/ai_engineering/installer/service.py` — `_log_install_event()` add VCS context
- [x] 3.2 Update `src/ai_engineering/installer/operations.py` — `_save_manifest_and_log()` add VCS context
- [x] 3.3 Update `src/ai_engineering/commands/workflows.py` — `_log_audit()` add VCS context
- [x] 3.4 Update `src/ai_engineering/release/orchestrator.py` — replace `_log_audit_event()` with `emit_deploy_event()` calls
- [x] 3.5 Update `src/ai_engineering/updater/service.py` — `_log_update_event()` add VCS context
- [x] 3.6 Update `src/ai_engineering/cli_commands/signals_cmd.py` — `signals_emit()` add VCS context
- [x] 3.7 Create `tests/unit/test_deploy_event_wiring.py`

### Phase 4: Workflow CLI Wiring [S] ✅
- [x] 4.1 Create `src/ai_engineering/cli_commands/workflow.py` — 3 commands: `workflow commit "msg" [--only]`, `workflow pr "msg"`, `workflow pr-only`
- [x] 4.2 Register `workflow_app` in `src/ai_engineering/cli_factory.py`
- [x] 4.3 Create `tests/unit/test_workflow_cmd.py`

### Phase 5: Signal Aggregators [M] ✅
- [x] 5.1 Add `scan_metrics_from(events, *, days=30)` to `signals.py` — scan_complete events -> avg score by mode, finding counts
- [x] 5.2 Add `build_metrics_from(events, *, days=30)` to `signals.py` — build_complete events -> files changed, lines, tests added
- [x] 5.3 Add `deploy_metrics_from(events, *, days=30)` to `signals.py` — deploy_complete events -> count, rollbacks, failure rate
- [x] 5.4 Add `session_metrics_from(events, *, limit=10)` to `signals.py` — session_metric events -> tokens, utilization, skills
- [x] 5.5 Add `decision_store_health(project_root)` to `signals.py` — read decision-store.json -> active, expired, resolved, avg age
- [x] 5.6 Add `adoption_metrics(project_root)` to `signals.py` — read install-manifest.json -> stacks, providers, hooks, IDEs
- [x] 5.7 Add `checkpoint_status(project_root)` to `signals.py` — read session-checkpoint.json -> last checkpoint, progress, blocked_on
- [x] 5.8 Add `lead_time_metrics(project_root, *, days=30)` to `signals.py` — git merge history -> median lead time (first commit -> merge)
- [x] 5.9 Create `tests/unit/test_signal_aggregators.py`

### Phase 6: Dashboard Expansion [L] ✅
- [x] 6.1 Expand `observe_engineer()` — add Code Quality (from scan events), Build Activity (from build events), Lead Time (from git)
- [x] 6.2 Expand `observe_team()` — add Decision Store Health (from decision-store.json), Adoption (from install-manifest.json), Scan Health (from scan events)
- [x] 6.3 Expand `observe_ai()` — add Token Utilization (used/available), Session Recovery (from checkpoint), Skills loaded
- [x] 6.4 Expand `observe_dora()` — add Lead Time for Changes (median days, rating), Change Failure Rate (deployments, rollbacks, rate, rating)
- [x] 6.5 Expand `observe_health()` — multi-variable score: gate + velocity + scan + decision + DORA, weighted by data availability
- [x] 6.6 Create `tests/unit/test_observe_dashboards.py`

### Phase 7: Git Tracking [S] ✅
- [x] 7.1 Simplify `.gitignore` — remove `state/*` + exceptions, track all `state/`
- [x] 7.2 Reset `audit-log.ndjson` — empty for fresh start with enriched format

### Phase 8: Verification [S] ✅
- [x] 8.1 `ruff check` + `ruff format` — zero errors
- [x] 8.2 `ty` — no new errors
- [x] 8.3 `pytest` — all tests pass (1253/1253)
- [x] 8.4 `ai-eng observe engineer/team/ai/dora/health` — verify expanded output
- [x] 8.5 `ai-eng workflow commit --help` — verify CLI wiring
