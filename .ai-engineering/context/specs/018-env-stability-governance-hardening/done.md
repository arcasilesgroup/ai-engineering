---
spec: "018"
status: "done"
completed: "2026-02-23"
---

# Done — Environment Stability & Governance Enforcement Hardening

## Summary

Delivered a consolidated hardening spec addressing three recurring operational failures:

1. **Python version pinning** — Created `.python-version` (3.12) at repo root for deterministic `uv` resolution across all contexts (terminal, git hooks, subprocesses).

2. **Venv health detection** — Added `_check_venv_health`, `_parse_pyvenv_home`, and `_recreate_venv` to `doctor/service.py`. The doctor now detects stale venvs (broken `pyvenv.cfg` paths) and `--fix-tools` can recreate them automatically.

3. **Governance enforcement hardening** — Closed 5 bypass vectors:
   - `hooks/manager.py:295`: Fail-closed when hash missing (was silently passing).
   - `gates.py:436`: Default `required=True` for `_run_tool_check` (was fail-open).
   - `.claude/settings.json`: Synced 13 deny rules including `--no-verify` patterns.
   - `CLAUDE.md`: Added "Absolute Prohibitions for AI Agents" (8 rules).
   - Template mirrors updated for consistency.

## Verification Evidence

| Check | Result |
|-------|--------|
| Tests | 629 passed, 100% coverage |
| Ruff lint | 0 issues |
| Ruff format | 0 issues |
| ty type check | 0 errors |
| gitleaks | 0 leaks |
| pip-audit | 0 vulnerabilities |
| `uv python find` | Resolves to `.venv/bin/python3` via `.python-version` |
| `ai-eng doctor` venv-health | ok — Venv home valid |
| Fail-closed hooks | Verified — hooks without manifest hashes fail verification |

## Files Changed

| File | Action |
|------|--------|
| `.python-version` | Created |
| `.gitignore` | Modified (unignore `.python-version`) |
| `src/ai_engineering/doctor/service.py` | Modified (venv health check) |
| `src/ai_engineering/hooks/manager.py` | Modified (fail-closed L295) |
| `src/ai_engineering/policy/gates.py` | Modified (fail-closed L436) |
| `.claude/settings.json` | Modified (deny rules) |
| `src/ai_engineering/templates/project/.claude/settings.json` | Modified (deny rules) |
| `CLAUDE.md` | Modified (prohibitions section) |
| `src/ai_engineering/templates/project/CLAUDE.md` | Modified (prohibitions section) |
| `.ai-engineering/standards/framework/stacks/python.md` | Modified (version pinning + venv sections) |
| `tests/unit/test_doctor.py` | Modified (13 new tests) |
| `tests/unit/test_hooks.py` | Modified (1 new test + manifest setup) |
| `tests/unit/test_gates.py` | Modified (2 new tests) |
| `tests/integration/test_hooks_git.py` | Modified (manifest setup for fail-closed) |

## Decisions Made

| ID | Decision |
|----|----------|
| D018-001 | Pin `.python-version` at major.minor `3.12` only |
| D018-002 | Fail-closed for hook verification without hash |
| D018-003 | Default `required=True` for `_run_tool_check` |
