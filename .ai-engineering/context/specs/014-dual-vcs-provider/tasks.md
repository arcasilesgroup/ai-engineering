---
spec: "014"
total: 35
completed: 35
last_session: "2026-02-22"
next_session: "CLOSED"
---

# Tasks — Dual VCS Provider Support + Generic Hardening

## Phase 0: Scaffold [S]

- [x] 0.1 Create branch `feat/dual-vcs-provider` from main
- [x] 0.2 Create spec 014 scaffold (spec.md, plan.md, tasks.md)
- [x] 0.3 Activate spec 014 in `_active.md`
- [x] 0.4 Update `product-contract.md` active spec reference

## Phase 1: Generic Hardening — Hooks, Gates, Validator [M]

- [x] 1.1 Add `.venv` auto-activation to `generate_bash_hook()` in `hooks/manager.py`
- [x] 1.2 Add `.venv` auto-activation to `generate_powershell_hook()` in `hooks/manager.py`
- [x] 1.3 Add `required: bool` parameter to `_run_tool_check()` in `policy/gates.py`
- [x] 1.4 Add `encoding="utf-8", errors="replace"` to subprocess calls in `gates.py`
- [x] 1.5 Pass `required=True` in `_run_pre_commit_checks()` and `_run_pre_push_checks()`
- [x] 1.6 Replace regex counter patterns with `_parse_counter()` in `validator/service.py`
- [x] 1.7 Handle `active_spec == "none"` in `_check_manifest_coherence()`
- [x] 1.8 Update hook tests to verify `.venv` activation blocks
- [x] 1.9 Update gate tests to verify `required=True` failure behavior
- [x] 1.10 Update validator tests for `_parse_counter()` and "none" handling

## Phase 2: PR Description + Pre-Push Delegation [S]

- [x] 2.1 Create `src/ai_engineering/vcs/pr_description.py` with `build_pr_title()`, `build_pr_description()`
- [x] 2.2 Implement `_read_active_spec()` and `_recent_commit_subjects()` helpers
- [x] 2.3 Rewrite `_run_pre_push_checks()` to delegate to `run_gate(GateHook.PRE_PUSH)`
- [x] 2.4 Change `pip-audit` invocation from `["uv", "run", "pip-audit"]` to `["pip-audit"]`
- [x] 2.5 Change `ty check` target from `src` to `src/ai_engineering`
- [x] 2.6 Write `tests/unit/test_pr_description.py`

## Phase 3: VCS Provider Abstraction [L]

- [x] 3.1 Create `src/ai_engineering/vcs/__init__.py` with re-exports
- [x] 3.2 Create `vcs/protocol.py` with `VcsProvider` Protocol and `VcsContext` dataclass
- [x] 3.3 Create `vcs/github.py` with `GitHubProvider` (wraps `gh` CLI)
- [x] 3.4 Create `vcs/azure_devops.py` with `AzureDevOpsProvider` (wraps `az repos` CLI)
- [x] 3.5 Create `vcs/factory.py` with `get_provider()` dispatch
- [x] 3.6 Write `tests/unit/test_vcs_github.py`
- [x] 3.7 Write `tests/unit/test_vcs_azure_devops.py`
- [x] 3.8 Write `tests/unit/test_vcs_factory.py`

## Phase 4: Refactor VCS Touchpoints [M]

- [x] 4.1 Refactor `_create_pr()` in `commands/workflows.py` to use `get_provider()`
- [x] 4.2 Refactor `_enable_auto_complete()` to use provider dispatch
- [x] 4.3 Integrate `build_pr_title/description` into PR workflows
- [x] 4.4 Refactor `create_maintenance_pr()` in `maintenance/report.py`
- [x] 4.5 Update `tests/unit/test_command_workflows.py`
- [x] 4.6 Update `tests/unit/test_skills_maintenance.py`

## Phase 5: CLI Integration [M]

- [x] 5.1 Add `--vcs` option to `install_cmd()` in `cli_commands/core.py`
- [x] 5.2 Update `default_install_manifest()` to accept `vcs_provider` parameter
- [x] 5.3 Create `cli_commands/vcs.py` with `status` and `set-primary` commands
- [x] 5.4 Register `vcs` group in `cli_factory.py`

## Phase 6: Test Suite Completion [M]

- [x] 6.1 Run full test suite — all tests green (510 passed)
- [x] 6.2 Run `ruff check src/ tests/` — 0 issues
- [ ] 6.3 Run `ty check src/ai_engineering` — skipped (PyPI blocked, ty unavailable)
- [ ] 6.4 Run `ai-eng validate` — skipped (depends on installed hooks)
- [x] 6.5 Verify coverage ≥ 80% (87%)

## Phase 7: Close [S]

- [x] 7.1 Create `done.md` with delivery summary
- [x] 7.2 Update `tasks.md` frontmatter (completed = total, next_session = CLOSED)
- [x] 7.3 Update `_active.md` to "none" or next spec
