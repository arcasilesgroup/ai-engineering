---
spec: "018"
approach: "serial-phases"
---

# Plan — Environment Stability & Governance Enforcement Hardening

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `.python-version` | Pin Python 3.12 for uv and toolchain resolution |

### Modified Files

| File | Change |
|------|--------|
| `src/ai_engineering/doctor/service.py` | Add `_check_venv_health` function + wire into `diagnose()` |
| `src/ai_engineering/hooks/manager.py` | L295: `True` → `False` (fail-closed) |
| `src/ai_engineering/policy/gates.py` | L436: `required=False` → `required=True` |
| `.claude/settings.json` | Sync deny rules from template + add `--no-verify` patterns |
| `src/ai_engineering/templates/project/.claude/settings.json` | Add `--no-verify` deny patterns |
| `CLAUDE.md` | Add "Absolute Prohibitions for AI Agents" section |
| `src/ai_engineering/templates/project/CLAUDE.md` | Mirror prohibitions section |
| `.ai-engineering/standards/framework/stacks/python.md` | Add version pinning + venv stability sections |
| `tests/unit/test_doctor.py` | Add venv health tests |
| `tests/unit/test_hooks.py` | Add hash-missing test |
| `tests/unit/test_gates.py` | Add required-default test |

### Mirror Copies

- `CLAUDE.md` ↔ `src/ai_engineering/templates/project/CLAUDE.md`
- `.claude/settings.json` ↔ `src/ai_engineering/templates/project/.claude/settings.json`

## Session Map

| Phase | Name | Size | Tasks |
|-------|------|------|-------|
| 0 | Scaffold & Activate | S | 0.1–0.6 |
| 1 | Python Environment Stability | M | 1.1–1.5 |
| 2 | Governance Code Hardening | M | 2.1–2.5 |
| 3 | Agent Configuration Hardening | M | 3.1–3.4 |
| 4 | Verification & Close | S | 4.1–4.9 |

## Patterns

- **Fail-closed by default**: All changes move from fail-open to fail-closed behavior.
- **Atomic phase commits**: `spec-018: Phase N — <description>`.
- **Mirror discipline**: Canonical files and template mirrors stay byte-identical.
- **Security-first ordering**: Code hardening (Phase 2) before config hardening (Phase 3).
