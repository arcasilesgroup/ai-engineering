---
spec: "014"
status: "completed"
started: "2026-02-22"
completed: "2026-02-22"
branch: "feat/dual-vcs-provider"
commits: 7
tests_added: 85
coverage: "87%"
---

# Done — Dual VCS Provider Support + Generic Hardening

## Delivery Summary

Spec 014 delivers dual VCS provider support (GitHub + Azure DevOps) and six
generic hardening improvements migrated from the work project.

## Phases Completed

| Phase | Description | Commit |
|-------|------------|--------|
| 0 | Scaffold spec files and activate | `87c8003` |
| 1 | Hook venv activation, required gate checks, ReDoS-safe validator | `1335c90` |
| 2 | PR description builder, pre-push delegation to `run_gate()` | `8acbe84` |
| 3 | VCS provider abstraction (protocol, github, azure_devops, factory) | `7dbf281` |
| 4 | Refactor PR creation and maintenance to use VCS provider dispatch | `9932174` |
| 5 | CLI integration (`--vcs` option, `vcs status`/`set-primary` commands) | `11af9fc` |
| 6 | Ruff lint/format fixes | `0092d73` |

## What Was Built

### Generic Hardening (G1-G6)

- **G1**: `.venv` auto-activation in generated bash and PowerShell git hooks.
- **G2**: `required` parameter on `_run_tool_check()` with UTF-8 encoding and
  fallback error messages.
- **G3**: ReDoS-safe `_parse_counter()` replacing regex-based objective/KPI
  counter parsing.
- **G4/G5**: `pip-audit` direct invocation (not via `uv run`) and `ty check`
  scoped to `src/ai_engineering`.
- **G6**: Pre-push checks delegated to `run_gate(GateHook.PRE_PUSH)`.

### Dual VCS Provider

- **Protocol**: `VcsProvider` structural interface with `create_pr`,
  `enable_auto_complete`, `is_available`, `provider_name`.
- **GitHub provider**: Wraps `gh` CLI (`gh pr create`, `gh pr merge --auto`).
- **Azure DevOps provider**: Wraps `az repos` CLI (`az repos pr create`,
  `az repos pr update` for auto-complete).
- **Factory**: `get_provider()` reads `providers.primary` from manifest,
  falls back to remote URL detection, defaults to GitHub.
- **PR description builder**: `build_pr_title()` and `build_pr_description()`
  generate structured PR titles/bodies from branch name and commit history.
- **CLI commands**: `ai-eng vcs status` and `ai-eng vcs set-primary`.
- **Install option**: `ai-eng install --vcs azure_devops`.

## New Files

| File | Purpose |
|------|---------|
| `src/ai_engineering/vcs/__init__.py` | Package re-exports |
| `src/ai_engineering/vcs/protocol.py` | `VcsProvider` Protocol, `VcsContext`, `VcsResult` |
| `src/ai_engineering/vcs/github.py` | `GitHubProvider` |
| `src/ai_engineering/vcs/azure_devops.py` | `AzureDevOpsProvider` |
| `src/ai_engineering/vcs/factory.py` | Provider dispatch factory |
| `src/ai_engineering/vcs/pr_description.py` | PR title/body builder |
| `src/ai_engineering/cli_commands/vcs.py` | VCS CLI commands |
| `tests/unit/test_pr_description.py` | 15 tests |
| `tests/unit/test_vcs_github.py` | 10 tests |
| `tests/unit/test_vcs_azure_devops.py` | 8 tests |
| `tests/unit/test_vcs_factory.py` | 10 tests |

## Modified Files

| File | Changes |
|------|---------|
| `hooks/manager.py` | `.venv` activation in hook generation |
| `policy/gates.py` | `required` param, UTF-8, fallback messages |
| `validator/service.py` | `_parse_counter()` replaces regex |
| `commands/workflows.py` | VCS provider dispatch for PR creation |
| `maintenance/report.py` | VCS provider dispatch for maintenance PRs |
| `state/defaults.py` | `vcs_provider` in manifest defaults |
| `installer/service.py` | `vcs_provider` through install chain |
| `cli_commands/core.py` | `--vcs` option on install |
| `cli_factory.py` | VCS command group registration |

## Quality Results

- **Tests**: 510 passed (0 failed)
- **Coverage**: 87% (threshold: 80%)
- **Ruff**: 0 lint issues, 0 format issues
- **ty**: Not available (PyPI blocked) — accepted risk
