---
spec: spec-099
title: First-run experience - wizard validation, warnings, and gate generalization
status: done
effort: medium
---

## Summary

The first-run experience after `ai-eng install` has multiple UX and correctness issues that compound into a frustrating onboarding. The most critical: `questionary.checkbox` prompts accept empty selections silently when the user presses Enter without spacebar, resulting in empty stacks/providers/IDEs in the manifest. This cascades into: persistent VCS warnings (state never written), irrecoverable stack-drift (doctor cannot fix), duplicate/confusing post-install warnings, and pre-push gates hardcoded to a specific project layout that fail on any user project. Additionally, the installer runs without validating that the target directory is a software project, and post-install step display order is desynchronized from actual execution.

## Goals

- [ ] Wizard checkbox prompts validate non-empty selection with re-prompt option and display spacebar usage hint
- [ ] `state.vcs_provider` is persisted during install, eliminating the persistent VCS mismatch warning in doctor
- [ ] Post-install warnings are deduplicated (VCS tool warning appears once, not twice)
- [ ] `install_cmd()` validates the target directory looks like a project before proceeding
- [ ] Python pre-push gate checks use dynamic paths (source root, test directory) instead of hardcoded `src/ai_engineering` and `tests/unit/`
- [ ] Pre-push gate checks gracefully skip when the target path does not exist (e.g., no tests yet) instead of failing
- [ ] `_render_pipeline_steps` imports `PHASE_ORDER` instead of hardcoding phase sequence
- [ ] CONTRIBUTING.md documents the contributor install flow (`git clone` + source install)
- [ ] Branch policy help text is expanded with actionable steps

## Non-Goals

- Redesigning the wizard flow or adding a post-wizard confirmation screen (validation + hints are sufficient)
- Making stack-drift auto-fixable in `doctor --fix` (fixing the wizard prevents new cases; existing cases use `ai-eng stack add`)
- Fixing the `pip` version upgrade suggestion (pip's own behavior, outside our control)
- Adding Windows-specific UI or installer
- Modifying the spec-098 changes already in the current branch (tools-before-hooks, pip fallback, README venv step)
- Grace period or advisory mode for hooks
- Automatic initial commit of scaffolding files

## Decisions

D-099-01: Add `validate` parameter to `questionary.checkbox` calls in wizard to reject empty selections, plus a hint string explaining spacebar usage.
**Rationale**: `questionary.checkbox` supports a `validate` callback and an `instruction` parameter natively. Using the library's built-in validation is the simplest fix — no custom wrapper needed. The instruction text "(spacebar to select, Enter to confirm)" addresses the root cause: users expect Enter to select, not confirm.

D-099-02: Write `state.vcs_provider = vcs_provider` in `_run_operational_phases()` before `save_install_state()`.
**Rationale**: The field exists in the `InstallState` model and doctor already reads it. The parameter is already available in scope. This is a one-line fix to a data flow gap, not a design change.

D-099-03: Remove ToolsPhase warning promotion from `_summary_to_install_result()` to eliminate duplicate VCS tool warnings.
**Rationale**: `_run_operational_phases()` already checks the same tools with more detail (auth, install attempt). ToolsPhase warnings are redundant in `manual_steps` since operational phases provide the authoritative result. The pipeline step status icon still shows tool results — only the duplicate manual_step text is removed.

D-099-04: Add project validation in `install_cmd()` before calling install functions, not in `resolve_project_root()`.
**Rationale**: Other commands (doctor, gate) also use `resolve_project_root()` and are expected to run in any directory. The validation guard belongs only in the install entry point. Check for at least one project signal (`.git`, `pyproject.toml`, `package.json`, `*.sln`, `go.mod`, `Cargo.toml`, `tsconfig.json`). In interactive mode: warn and confirm. In `--non-interactive` mode: abort.

D-099-05: Replace hardcoded `src/ai_engineering` and `tests/unit/` in `stack_runner.py` Python checks with dynamic path detection.
**Rationale**: dotnet and nextjs checks already use generic commands (`dotnet build`, `tsc --noEmit`, `vitest run`). Python checks must follow the same pattern. Source root is detectable from `pyproject.toml` `[tool.hatch.build]` or `[tool.setuptools]` packages field, with fallback to `src/` or `.`. Test directory is detectable from `[tool.pytest.ini_options] testpaths` or by probing `tests/`, `test/`. If the path doesn't exist, the check passes with a skip message.

D-099-06: Remove `ai_engineering.policy.duplication` from user-facing gate checks.
**Rationale**: The duplication checker is invoked via `python -m ai_engineering.policy.duplication --path src/ai_engineering` — the `--path` is hardcoded to ai-engineering's own source tree, not the user's project. The module itself is stdlib-only, but its invocation in `PRE_PUSH_CHECKS` targets a path that does not exist in user projects. Remove it from the default gate and keep it only for ai-engineering's own CI.

D-099-07: Remove `pip-audit --ignore-vuln CVE-2026-4539` from user-facing gate checks.
**Rationale**: This CVE exemption is specific to ai-engineering's own dependency tree. User projects have different dependencies and different vulnerability profiles. The `pip-audit` check should run without project-specific ignores. The exemption belongs in ai-engineering's own `pyproject.toml` or CI config.

D-099-08: Import `PHASE_ORDER` from `phases/__init__.py` in `_render_pipeline_steps` instead of maintaining a separate hardcoded list.
**Rationale**: Two lists that must stay in sync will drift. Single source of truth eliminates the class of bug entirely.

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Wizard validation annoys users who intentionally want zero stacks | Low — edge case | Validation message offers explicit "continue with none" option |
| Dynamic source root detection misidentifies project layout | Gate checks wrong directory | Fallback chain: pyproject.toml config → `src/` probe → `.` (current dir). Same behavior as ruff/ty defaults |
| Removing duplication check weakens quality gate | Reduced gate coverage for users | The check was never running correctly on user projects anyway (wrong path). Net quality impact is zero |
| Project validation blocks legitimate use on truly empty new projects | User cannot install | The check warns and asks confirmation, never hard-blocks in interactive mode. `--non-interactive` requires `--target` flag to proceed |
| Removing pip-audit CVE ignore causes false positives on ai-engineering's own CI | CI breaks | Move the `--ignore-vuln` to ai-engineering's own `pyproject.toml` `[tool.pip-audit]` config, not in the shared gate |

## References

- Anonymous community feedback: first-run experience on Windows (2026-04)
- spec-098: tools-before-hooks fix (current branch, predecessor to this spec)
- Wizard implementation: `src/ai_engineering/installer/wizard.py`
- Gate checks: `src/ai_engineering/policy/checks/stack_runner.py`
- VCS state gap: `src/ai_engineering/installer/service.py:_run_operational_phases()`
- Display order: `src/ai_engineering/cli_commands/core.py:_render_pipeline_steps()`
