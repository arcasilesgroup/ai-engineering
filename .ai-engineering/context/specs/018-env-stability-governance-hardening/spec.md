---
id: "018"
slug: "env-stability-governance-hardening"
status: "done"
created: "2026-02-23"
---

# Spec 018 — Environment Stability & Governance Enforcement Hardening

## Problem

Three recurring operational failures undermine framework reliability and governance integrity:

1. **Python tooling resolution fragility**: No `.python-version` file pins the Python version for `uv`. PATH resolution differs across terminal, git hooks, and Claude Code subprocess contexts, causing intermittent "not installed" errors for `uv`, `ruff`, and venv-dependent tools.

2. **Venv invalidation on Python upgrades**: `.venv/pyvenv.cfg` contains absolute homebrew paths (e.g., `/opt/homebrew/Cellar/python@3.12/3.12.12/...`). When `brew upgrade` changes the Python path, the venv becomes invalid with no automated detection or recovery.

3. **AI agent governance bypass vectors**: Five distinct paths exist where agents can circumvent security/quality/governance gates:
   - `.claude/settings.json` has `"deny": []` — no deny rules blocking `--no-verify`.
   - No `--no-verify` detection exists in hook or gate code.
   - `CLAUDE.md` lacks explicit AI agent prohibitions.
   - Hook integrity verification silently passes when install-manifest hash is missing (`hooks/manager.py:295`).
   - `_run_tool_check` defaults to `required=False` (`gates.py:436`), fail-open behavior.

## Solution

Deliver a consolidated hardening spec with three tracks:

1. **Python version pinning**: Create `.python-version` at repo root, add venv health detection in `ai-eng doctor`, document in stack standards.
2. **Governance code hardening**: Fix fail-open behavior in `verify_hooks` (fail-closed when hash missing) and `_run_tool_check` (default `required=True`).
3. **Agent configuration hardening**: Sync deny rules in `.claude/settings.json`, add `--no-verify` blocking, add explicit agent prohibitions in `CLAUDE.md`.

## Scope

### In Scope

- `.python-version` creation and documentation.
- `doctor/service.py` venv health check with fix-tools recreation path.
- `hooks/manager.py` line 295 fix (True → False).
- `gates.py` line 436 fix (False → True).
- `.claude/settings.json` deny rules sync + `--no-verify` patterns.
- `CLAUDE.md` "Absolute Prohibitions for AI Agents" section.
- Template mirrors for CLAUDE.md and settings.json.
- Tests for all code changes.
- Stack standards documentation update.

### Out of Scope

- CI/CD pipeline changes.
- New CLI commands or subcommands.
- Python version upgrade (stays 3.12).
- `--no-verify` runtime detection in hooks (git does not pass this info to hooks).

## Acceptance Criteria

1. `.python-version` exists at repo root with content `3.12`.
2. `ai-eng doctor` includes a venv health check that detects stale `pyvenv.cfg` paths.
3. `ai-eng doctor --fix-tools` can recreate a stale venv via `uv venv --python 3.12`.
4. `verify_hooks` returns False when expected hash is missing (fail-closed).
5. `_run_tool_check` defaults to `required=True` (fail-closed).
6. `.claude/settings.json` deny list includes `--no-verify` patterns and matches template.
7. `CLAUDE.md` contains "Absolute Prohibitions for AI Agents" section.
8. Template mirrors are consistent with canonical files.
9. All tests pass at 100% coverage.
10. All quality gates pass (ruff, ty, gitleaks, pip-audit).

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D018-001 | Pin `.python-version` at major.minor `3.12` only | Allows patch upgrades without manual file changes. Consistent with `pyproject.toml requires-python >=3.11`. |
| D018-002 | Fail-closed for hook verification without hash | A managed hook without a recorded hash is an integrity gap. `doctor --fix-hooks` provides recovery. |
| D018-003 | Default `required=True` for `_run_tool_check` | All existing callers pass `check.required` explicitly. Default change is defense-in-depth against future direct callers. |
