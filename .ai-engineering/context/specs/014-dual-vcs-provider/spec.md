---
id: "014"
slug: "dual-vcs-provider"
status: "in-progress"
created: "2026-02-22"
---

# Spec 014 — Dual VCS Provider Support + Generic Hardening

## Problem

The codebase has six proven improvements in a work fork that need migrating, plus the PR workflows are hardcoded to a single VCS provider (`gh` CLI for GitHub). The `InstallManifest` already models `VcsProviders` with `primary`/`enabled` fields and an `AzureDevOpsExtension`, but no runtime dispatch exists — `_create_pr()`, `_enable_auto_complete()`, and `create_maintenance_pr()` all call `gh` directly. This prevents Azure DevOps users from using governed PR workflows. Additionally, the work fork contains battle-tested improvements to hooks, gates, validator, and workflow orchestration that should be upstreamed.

### Generic improvements pending migration

- **G1**: Git hooks generated without `.venv` auto-activation — GUI git clients (VS Code, JetBrains) can't find `ai-eng` on PATH.
- **G2**: `_run_tool_check()` silently skips missing required tools instead of failing.
- **G3**: Validator uses regex patterns for counter parsing — vulnerable to ReDoS (S5852). Active spec `"none"` not handled.
- **G4**: PR descriptions are minimal (`gh pr create --fill`) — no structured What/Why/How/Checklist, no spec context.
- **G5**: `_run_pre_push_checks()` in workflows duplicates logic already in `policy/gates.py`.
- **G6**: `pip-audit` invoked via `uv run` wrapper; `ty check` targets broad `src` instead of `src/ai_engineering`.

## Solution

1. **Migrate G1–G6** as independent, incremental changes.
2. **Create `src/ai_engineering/vcs/` package** — a VCS provider abstraction layer using Python's Protocol pattern.
3. **Implement `GitHubProvider`** — wraps `gh` CLI commands.
4. **Implement `AzureDevOpsProvider`** — wraps `az repos` CLI commands (ported from work fork).
5. **Factory-based dispatch** — `get_provider(project_root)` reads `InstallManifest.providers.primary` and returns the correct provider. Fallback: detect provider from git remote URL.
6. **Provider-agnostic PR description** — `build_pr_title()` and `build_pr_description()` generate structured content consumed by both providers.
7. **Refactor all VCS touchpoints** — `commands/workflows.py` and `maintenance/report.py` use the provider abstraction instead of hardcoded CLI calls.
8. **CLI integration** — `--vcs` option on `install` command, new `ai-eng vcs` command group.

## Scope

### In Scope

- G1–G6 generic improvements migration.
- New `vcs/` package: `protocol.py`, `github.py`, `azure_devops.py`, `factory.py`, `pr_description.py`.
- Refactor `commands/workflows.py` to use VCS provider abstraction.
- Refactor `maintenance/report.py` to use VCS provider abstraction.
- `--vcs` option on `ai-eng install`.
- `ai-eng vcs status` and `ai-eng vcs set-primary` commands.
- Full test coverage for new and modified modules.

### Out of Scope

- `config.py` with `ARTIFACT_INDEX_URL` (corporate-specific, not applicable).
- `ado/main.yml` pipeline (corporate CI/CD, not applicable).
- `--index-url` injection in tool install, pipeline snippets (corporate feed).
- Removal of `gh` from optional tools (both providers remain optional).
- GitLab or Bitbucket providers (future extension point only).

## Acceptance Criteria

1. `ai-eng install --vcs github` sets `providers.primary = "github"` in manifest.
2. `ai-eng install --vcs azure-devops` sets `providers.primary = "azure-devops"` in manifest.
3. `ai-eng vcs status` displays current provider, enabled providers, and tool readiness.
4. `ai-eng vcs set-primary azure-devops` switches the active provider.
5. PR workflow dispatches to `gh` or `az` based on manifest `providers.primary`.
6. Maintenance PR dispatches to correct VCS provider.
7. Generated git hooks contain `.venv` auto-activation for both Bash and PowerShell.
8. `_run_tool_check()` with `required=True` fails when tool is missing.
9. Validator uses plain-string counter parsing (no regex). `active_spec == "none"` handled.
10. PR descriptions include structured What/Why/How/Checklist with active spec context.
11. `_run_pre_push_checks()` delegates to `run_gate(GateHook.PRE_PUSH)`.
12. All existing tests pass. New tests for `vcs/` achieve ≥80% coverage.
13. Content integrity 6/6 passes (`ai-eng validate`).

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D014-001 | Protocol pattern over ABC for VcsProvider | Structural subtyping — no forced inheritance. Providers can be tested independently. Aligns with Python patterns contract. |
| D014-002 | Factory reads manifest then falls back to remote URL detection | Supports pre-install usage (no manifest yet) and explicit configuration (post-install). |
| D014-003 | `gh pr create --title --body` replaces `--fill` | Enables structured PR description injection. `--fill` ignores custom body. |
| D014-004 | `create_pr()` returns `tuple[StepResult, str \| None]` | ADO needs PR ID for auto-complete. GitHub can return None (auto-targets current branch). Unified interface. |
| D014-005 | PR description generation is provider-agnostic | `build_pr_title/description` produce plain text consumed by both `gh` and `az`. No provider coupling. |
| D014-006 | G1–G6 in Phase 1–2 before VCS refactor | Independent improvements land first — smaller diffs, easier review, no VCS coupling. |
