---
spec: "014"
total: 35
completed: 0
last_session: "2026-02-22"
next_session: "Phase 0 — Scaffold"
---

# Tasks — Dual VCS Provider Support + Generic Hardening

## Phase 0: Scaffold [S]

- [ ] 0.1 Create branch `feat/dual-vcs-provider` from main
- [ ] 0.2 Create spec 014 scaffold (spec.md, plan.md, tasks.md)
- [ ] 0.3 Activate spec 014 in `_active.md`
- [ ] 0.4 Update `product-contract.md` active spec reference

## Phase 1: Generic Hardening — Hooks, Gates, Validator [M]

- [ ] 1.1 Add `.venv` auto-activation to `generate_bash_hook()` in `hooks/manager.py`
- [ ] 1.2 Add `.venv` auto-activation to `generate_powershell_hook()` in `hooks/manager.py`
- [ ] 1.3 Add `required: bool` parameter to `_run_tool_check()` in `policy/gates.py`
- [ ] 1.4 Add `encoding="utf-8", errors="replace"` to subprocess calls in `gates.py`
- [ ] 1.5 Pass `required=True` in `_run_pre_commit_checks()` and `_run_pre_push_checks()`
- [ ] 1.6 Replace regex counter patterns with `_parse_counter()` in `validator/service.py`
- [ ] 1.7 Handle `active_spec == "none"` in `_check_manifest_coherence()`
- [ ] 1.8 Update hook tests to verify `.venv` activation blocks
- [ ] 1.9 Update gate tests to verify `required=True` failure behavior
- [ ] 1.10 Update validator tests for `_parse_counter()` and "none" handling

## Phase 2: PR Description + Pre-Push Delegation [S]

- [ ] 2.1 Create `src/ai_engineering/vcs/pr_description.py` with `build_pr_title()`, `build_pr_description()`
- [ ] 2.2 Implement `_read_active_spec()` and `_recent_commit_subjects()` helpers
- [ ] 2.3 Rewrite `_run_pre_push_checks()` to delegate to `run_gate(GateHook.PRE_PUSH)`
- [ ] 2.4 Change `pip-audit` invocation from `["uv", "run", "pip-audit"]` to `["pip-audit"]`
- [ ] 2.5 Change `ty check` target from `src` to `src/ai_engineering`
- [ ] 2.6 Write `tests/unit/test_pr_description.py`

## Phase 3: VCS Provider Abstraction [L]

- [ ] 3.1 Create `src/ai_engineering/vcs/__init__.py` with re-exports
- [ ] 3.2 Create `vcs/protocol.py` with `VcsProvider` Protocol and `VcsContext` dataclass
- [ ] 3.3 Create `vcs/github.py` with `GitHubProvider` (wraps `gh` CLI)
- [ ] 3.4 Create `vcs/azure_devops.py` with `AzureDevOpsProvider` (wraps `az repos` CLI)
- [ ] 3.5 Create `vcs/factory.py` with `get_provider()` dispatch
- [ ] 3.6 Write `tests/unit/test_vcs_github.py`
- [ ] 3.7 Write `tests/unit/test_vcs_azure_devops.py`
- [ ] 3.8 Write `tests/unit/test_vcs_factory.py`

## Phase 4: Refactor VCS Touchpoints [M]

- [ ] 4.1 Refactor `_create_pr()` in `commands/workflows.py` to use `get_provider()`
- [ ] 4.2 Refactor `_enable_auto_complete()` to use provider dispatch
- [ ] 4.3 Integrate `build_pr_title/description` into PR workflows
- [ ] 4.4 Refactor `create_maintenance_pr()` in `maintenance/report.py`
- [ ] 4.5 Update `tests/unit/test_command_workflows.py`
- [ ] 4.6 Update `tests/unit/test_skills_maintenance.py`

## Phase 5: CLI Integration [M]

- [ ] 5.1 Add `--vcs` option to `install_cmd()` in `cli_commands/core.py`
- [ ] 5.2 Update `default_install_manifest()` to accept `vcs_provider` parameter
- [ ] 5.3 Create `cli_commands/vcs.py` with `status` and `set-primary` commands
- [ ] 5.4 Register `vcs` group in `cli_factory.py`

## Phase 6: Test Suite Completion [M]

- [ ] 6.1 Run full test suite — all tests green
- [ ] 6.2 Run `ruff check src/ tests/` — 0 issues
- [ ] 6.3 Run `ty check src/ai_engineering` — 0 errors
- [ ] 6.4 Run `ai-eng validate` — 6/6 integrity
- [ ] 6.5 Verify coverage ≥ 80%

## Phase 7: Close [S]

- [ ] 7.1 Create `done.md` with delivery summary
- [ ] 7.2 Update `tasks.md` frontmatter (completed = total, next_session = CLOSED)
- [ ] 7.3 Update `_active.md` to "none" or next spec
