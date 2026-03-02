---
spec: "029"
approach: "serial-phases"
---

# Plan — Selective Test Execution v1

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `src/ai_engineering/policy/test_scope.py` | Test scope engine + CLI |
| `scripts/check_test_mapping.py` | Rule/source/test bidirectional integrity checker |
| `tests/unit/test_test_scope.py` | Unit tests for scope algorithm and CLI contract |
| `.ai-engineering/context/specs/029-selective-test-execution-v1/spec.md` | WHAT document |
| `.ai-engineering/context/specs/029-selective-test-execution-v1/plan.md` | HOW document |
| `.ai-engineering/context/specs/029-selective-test-execution-v1/tasks.md` | DO document |

### Modified Files

| File | Change |
|------|--------|
| `src/ai_engineering/git/operations.py` | Add merge-base and changed-file helpers |
| `src/ai_engineering/policy/gates.py` | Integrate test scope modes and selective execution |
| `src/ai_engineering/cli_commands/gate.py` | Print scope diagnostics in passed state |
| `.github/workflows/ci.yml` | Scoped tier execution + scope artifacts + mapping check |
| `tests/integration/test_git_operations.py` | Coverage for new git helper functions |
| `tests/unit/test_gates.py` | Scope mode tests and fallback tests |
| `tests/integration/test_gates_integration.py` | Scoped gate integration tests |
| `tests/integration/test_platform_onboarding.py` | Add missing pytestmark |
| `tests/unit/test_credentials.py` | Add missing pytestmark |
| `tests/unit/test_platforms.py` | Add missing pytestmark |
| `tests/unit/test_setup_cli.py` | Add missing pytestmark |
| `tests/unit/test_sonar_gate.py` | Add missing pytestmark |
| `tests/unit/test_sonarlint.py` | Add missing pytestmark |
| `.ai-engineering/standards/framework/quality/core.md` | Gate structure update for scoped tests |
| `.ai-engineering/state/decision-store.json` | Record selective test execution decision |
| `.ai-engineering/state/audit-log.ndjson` | Append governance event |
| `.ai-engineering/context/specs/_active.md` | Activate spec-029 |
| `.ai-engineering/context/product/product-contract.md` | Update Active Spec pointer |

## Session Map

| Phase | Description | Size |
|------|-------------|------|
| 0 | Scaffold and activate spec files | S |
| 1 | Implement test scope engine + git helpers | L |
| 2 | Integrate pre-push and CLI diagnostics | M |
| 3 | Integrate CI scoped execution + mapping gate | L |
| 4 | Add mapping checker + tests + marker fixes | L |
| 5 | Governance updates + final verification | M |

## Patterns

- Fail-closed behavior on ambiguity, errors, unknown source coverage, and high-risk paths.
- Deterministic path normalization and stable sorted outputs.
- Non-mutating registry clone for selective gate overrides.
- Same scope engine used by local hooks and CI jobs.
