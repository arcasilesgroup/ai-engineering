---
spec: "018"
total: 29
completed: 0
last_session: "2026-02-23"
next_session: "Phase 0 — Scaffold"
---

# Tasks — Environment Stability & Governance Enforcement Hardening

## Phase 0: Scaffold & Activate [S]

- [x] 0.1 Create branch `feat/env-stability-governance-hardening` from main
- [x] 0.2 Create spec.md
- [x] 0.3 Create plan.md
- [x] 0.4 Create tasks.md
- [ ] 0.5 Update `_active.md` → spec-018
- [ ] 0.6 Update `product-contract.md` Active Spec → spec-018

## Phase 1: Python Environment Stability [M]

- [ ] 1.1 Create `.python-version` with content `3.12`
- [ ] 1.2 Add `_check_venv_health` to `doctor/service.py` (parse pyvenv.cfg, verify home path)
- [ ] 1.3 Add venv recreation via `uv venv --python 3.12` in fix path
- [ ] 1.4 Add 4 venv health tests to `tests/unit/test_doctor.py`
- [ ] 1.5 Update `standards/framework/stacks/python.md` with version pinning + venv stability sections

## Phase 2: Governance Code Hardening [M]

- [ ] 2.1 Fix `hooks/manager.py:295` — `True` → `False` (fail-closed when hash missing)
- [ ] 2.2 Fix `gates.py:436` — `required=False` → `required=True` (fail-closed default)
- [ ] 2.3 Add hash-missing test to `tests/unit/test_hooks.py`
- [ ] 2.4 Add required-default test to `tests/unit/test_gates.py`
- [ ] 2.5 Verify full test suite passes (no regressions)

## Phase 3: Agent Configuration Hardening [M]

- [ ] 3.1 Sync `.claude/settings.json` deny rules from template + add `--no-verify` patterns
- [ ] 3.2 Update `templates/project/.claude/settings.json` with `--no-verify` deny patterns
- [ ] 3.3 Add "Absolute Prohibitions for AI Agents" section to `CLAUDE.md`
- [ ] 3.4 Mirror prohibitions section to `templates/project/CLAUDE.md`

## Phase 4: Verification & Close [S]

- [ ] 4.1 Run pytest with 100% coverage
- [ ] 4.2 Run ruff lint/format checks
- [ ] 4.3 Run ty type check
- [ ] 4.4 Run gitleaks + pip-audit security checks
- [ ] 4.5 Verify `uv python find` resolves 3.12
- [ ] 4.6 Verify `ai-eng doctor` shows venv health check
- [ ] 4.7 Verify `ai-eng gate pre-commit` works with fail-closed hooks
- [ ] 4.8 Create done.md, update tasks.md frontmatter
- [ ] 4.9 Run integrity-check
