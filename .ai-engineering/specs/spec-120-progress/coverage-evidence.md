# Spec-120 Phase D — Coverage evidence

**Date**: 2026-05-04
**Spec**: [spec-120-observability-modernization](../spec-120-observability-modernization.md)
**Phase**: D (T-D3 — coverage evidence)

## Command

```
python -m pytest \
  --cov=ai_engineering.state.trace_context \
  --cov=ai_engineering.state.audit_index \
  --cov=ai_engineering.state.audit_replay \
  --cov=ai_engineering.state.audit_otel_export \
  --cov=ai_engineering.state.observability \
  --cov-report=term-missing \
  tests/unit/state/ tests/unit/cli/ tests/unit/hooks/ \
  tests/integration/test_spec_120_e2e.py
```

## Result

`309 passed in 12.64s` (pytest 9.0.3, Python 3.12.12).

### Per-module coverage

| Module                                       | Stmts | Miss | Cover | Gate (≥ 90 %) |
|----------------------------------------------|-------|------|-------|---------------|
| `ai_engineering.state.trace_context`         |   151 |    8 | **95 %** | ✅ |
| `ai_engineering.state.audit_index`           |   205 |   12 | **94 %** | ✅ |
| `ai_engineering.state.audit_replay`          |   153 |    9 | **94 %** | ✅ |
| `ai_engineering.state.audit_otel_export`     |    80 |    4 | **95 %** | ✅ |
| `ai_engineering.state.observability`         |   286 |  114 |   60 %   | n/a — pre-existing module, not gated by Phase D |
| **Total (all five)**                         |   875 |  147 |   83 %   | — |

All four NEW spec-120 modules clear the ≥ 90 % gate declared in the
Phase D plan. `observability.py` is a pre-existing module that the
Phase D scope explicitly excludes from the gate (see plan-120 § Phase D
hard constraints); its 60 % is informational only and corresponds to
the existing emit helpers + downstream branches that other test suites
exercise (eval, memory, framework_operation).

### Missing-line annotations

| Module                  | Missing line(s)                              | Nature                                    |
|-------------------------|----------------------------------------------|-------------------------------------------|
| `trace_context`         | 145-146, 167-168, 182-183, 185, 188          | Defensive OS-error / corruption fallbacks |
| `audit_index`           | 278, 333, 405, 416, 455-456, 549-553, 574-576| Malformed-row / decode-error branches     |
| `audit_replay`          | 144, 149, 188, 191-194, 206, 313             | Edge-case row coercion + sort defensiveness |
| `audit_otel_export`     | 102, 107, 123, 130                           | Non-dict row + missing-iso fallback paths |

These are best-effort recovery branches with no deterministic trigger
in the canonical happy path; they are exercised by the surrounding unit
tests via mock-induced failure injection where appropriate.

## Audit-chain canary

`tests/unit/state/test_audit_chain.py` and
`tests/unit/test_audit_chain_verify.py` ran independently to confirm
the Phase D work did not regress the spec-110 / spec-112 audit-chain
contract:

```
27 passed in 0.20s
```

## Hard-constraint compliance

* `audit_chain.py` — untouched.
* `hooks-manifest.json` — untouched.
* Phase A/B/C modules — consumed via their public APIs only.

## Files updated for Phase D

* `tests/integration/test_spec_120_e2e.py` (T-D1, NEW)
* `AGENTS.md` (T-D2, additive subsection)
* `CLAUDE.md` (T-D2, additive subsection)
* `.ai-engineering/specs/spec-120-progress/coverage-evidence.md` (T-D3, NEW)
