---
spec: "014"
approach: "serial-phases"
---

# Plan — Dual VCS Provider Support + Generic Hardening

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `src/ai_engineering/vcs/__init__.py` | Package init, re-exports `get_provider`, `VcsProvider` |
| `src/ai_engineering/vcs/protocol.py` | `VcsProvider` Protocol, `VcsContext` dataclass, `StepResult` re-export |
| `src/ai_engineering/vcs/github.py` | `GitHubProvider` — `gh` CLI wrapper implementing `VcsProvider` |
| `src/ai_engineering/vcs/azure_devops.py` | `AzureDevOpsProvider` — `az repos` CLI wrapper implementing `VcsProvider` |
| `src/ai_engineering/vcs/factory.py` | `get_provider()` — manifest-based dispatch with remote URL fallback |
| `src/ai_engineering/vcs/pr_description.py` | `build_pr_title()`, `build_pr_description()` — structured PR content |
| `src/ai_engineering/cli_commands/vcs.py` | CLI commands: `vcs status`, `vcs set-primary` |
| `tests/unit/test_vcs_github.py` | Unit tests for `GitHubProvider` |
| `tests/unit/test_vcs_azure_devops.py` | Unit tests for `AzureDevOpsProvider` |
| `tests/unit/test_vcs_factory.py` | Unit tests for `get_provider()` factory |
| `tests/unit/test_pr_description.py` | Unit tests for PR description generation |

### Modified Files

| File | Change |
|------|--------|
| `src/ai_engineering/hooks/manager.py` | G1: Add `.venv` auto-activation to generated Bash and PowerShell hooks |
| `src/ai_engineering/policy/gates.py` | G2: Add `required` param to `_run_tool_check()`, UTF-8 encoding, fallback message. G6: `pip-audit` direct, `ty check src/ai_engineering` |
| `src/ai_engineering/validator/service.py` | G3: Replace regex with `_parse_counter()`, handle `active_spec == "none"` |
| `src/ai_engineering/commands/workflows.py` | G4: Structured PR via `vcs/pr_description.py`. G5: Delegate pre-push to `run_gate()`. VCS: Replace `_create_pr()`/`_enable_auto_complete()` with provider dispatch |
| `src/ai_engineering/maintenance/report.py` | VCS: Replace `gh pr create` with provider dispatch |
| `src/ai_engineering/cli_factory.py` | Register `vcs` command group |
| `src/ai_engineering/cli_commands/core.py` | Add `--vcs` option to `install_cmd()` |
| `src/ai_engineering/state/defaults.py` | Accept `vcs_provider` param in `default_install_manifest()` |
| `tests/unit/test_hooks.py` | Verify `.venv` activation in generated scripts |
| `tests/unit/test_gates.py` | Verify `required=True` behavior |
| `tests/unit/test_validator.py` | Verify `_parse_counter()` and "none" handling |
| `tests/unit/test_command_workflows.py` | Adapt to provider-based PR creation |
| `tests/unit/test_skills_maintenance.py` | Adapt `create_maintenance_pr()` tests |

### Mirror Copies

None — changes are source code and tests only.

## Session Map

| Phase | Size | Description |
|-------|------|-------------|
| 0 | S | Scaffold spec files, activate, create branch |
| 1 | M | G1–G3: Hook venv activation, required gate checks, ReDoS-safe validator |
| 2 | S | G4–G6: PR description helpers (provider-agnostic), pre-push delegation, pip-audit/ty fixes |
| 3 | L | VCS abstraction: `vcs/` package (protocol, github, azure_devops, factory) |
| 4 | M | Refactor workflows and maintenance to use VCS provider |
| 5 | M | CLI integration: `--vcs` on install, `ai-eng vcs` command group |
| 6 | M | Tests: unit tests for all new/modified modules |
| 7 | S | Close: full test suite, integrity check, done.md |

## Patterns

- **Protocol pattern**: `VcsProvider` as `typing.Protocol` — structural subtyping, no inheritance required. Each provider is a standalone class with `create_pr()`, `enable_auto_complete()`, `resolve_context()`.
- **Factory dispatch**: `get_provider()` reads `install-manifest.json` → `providers.primary`. Falls back to remote URL regex detection. Default: `GitHubProvider`.
- **Subprocess safety**: All subprocess calls use `encoding="utf-8", errors="replace"`, explicit `timeout`, `capture_output=True`.
- **Testing**: Mock `subprocess.run` for provider tests. Mock `get_provider` for workflow tests. Use existing `installed_project` fixture for integration.
- **Commit pattern**: One atomic commit per phase: `spec-014: Phase N — description`.
