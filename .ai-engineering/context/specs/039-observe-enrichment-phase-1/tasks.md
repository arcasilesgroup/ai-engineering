---
spec: "039"
total: 38
completed: 0
last_session: "2026-03-09"
next_session: "Phase 1"
---

# Tasks — Observe Enrichment Phase 1

### Phase 1: VCS Context (no dependencies)
- [ ] 1.1 Create `src/ai_engineering/vcs/repo_context.py` — RepoContext dataclass, URL parsing (GitHub SSH/HTTPS, ADO), module-level cache, fail-open, uses run_git
- [ ] 1.2 Create `src/ai_engineering/git/context.py` — GitContext dataclass (branch, commit_sha short 8), module-level cache, uses run_git
- [ ] 1.3 Create `tests/unit/test_repo_context.py`
- [ ] 1.4 Create `tests/unit/test_git_context.py`

### Phase 2: AuditEntry Extension
- [ ] 2.1 Add 7 optional fields to AuditEntry in `src/ai_engineering/state/models.py`: vcs_provider, vcs_organization, vcs_project, vcs_repository, branch, commit_sha, session_id
- [ ] 2.2 Inject get_repo_context + get_git_context in `_emit()` in `src/ai_engineering/state/audit.py`

### Phase 3: Update Write Sites
- [ ] 3.1 Update `src/ai_engineering/installer/service.py` — _log_install_event()
- [ ] 3.2 Update `src/ai_engineering/installer/operations.py` — _save_manifest_and_log()
- [ ] 3.3 Update `src/ai_engineering/commands/workflows.py` — _log_audit()
- [ ] 3.4 Update `src/ai_engineering/release/orchestrator.py` — replace _log_audit_event() with emit_deploy_event()
- [ ] 3.5 Update `src/ai_engineering/updater/service.py` — _log_update_event()
- [ ] 3.6 Update `src/ai_engineering/cli_commands/signals_cmd.py` — signals_emit()
- [ ] 3.7 Create `tests/unit/test_deploy_event_wiring.py`

### Phase 4: Workflow CLI Wiring
- [ ] 4.1 Create `src/ai_engineering/cli_commands/workflow.py` — 3 commands: workflow commit, workflow pr, workflow pr-only
- [ ] 4.2 Register workflow_app in `src/ai_engineering/cli_factory.py`
- [ ] 4.3 Create `tests/unit/test_workflow_cmd.py`

### Phase 5: Signal Aggregators
- [ ] 5.1 Add scan_metrics_from() to signals.py
- [ ] 5.2 Add build_metrics_from() to signals.py
- [ ] 5.3 Add deploy_metrics_from() to signals.py
- [ ] 5.4 Add session_metrics_from() to signals.py
- [ ] 5.5 Add decision_store_health() to signals.py
- [ ] 5.6 Add adoption_metrics() to signals.py
- [ ] 5.7 Add checkpoint_status() to signals.py
- [ ] 5.8 Add lead_time_metrics() to signals.py
- [ ] 5.9 Create `tests/unit/test_signal_aggregators.py`

### Phase 6: Dashboard Expansion
- [ ] 6.1 Expand observe_engineer() — add Code Quality, Build Activity, Lead Time sections
- [ ] 6.2 Expand observe_team() — add Decision Store Health, Adoption, Scan Health sections
- [ ] 6.3 Expand observe_ai() — add Session Recovery (from checkpoint), Token Utilization sections
- [ ] 6.4 Expand observe_dora() — add Lead Time, Change Failure Rate sections
- [ ] 6.5 Expand observe_health() — multi-variable score (gate, velocity, scan, decision, DORA)
- [ ] 6.6 Create `tests/unit/test_observe_dashboards.py`

### Phase 7: Git Tracking
- [ ] 7.1 Simplify .gitignore — remove state/* + exceptions, track all state/
- [ ] 7.2 Reset audit-log.ndjson (empty for fresh start with new format)

### Phase 8: Verification
- [ ] 8.1 ruff check + ruff format — zero errors
- [ ] 8.2 ty — no new errors
- [ ] 8.3 pytest — all tests pass
- [ ] 8.4 ai-eng observe engineer/team/ai/dora/health — verify output
- [ ] 8.5 ai-eng workflow commit --help — verify CLI wiring
