---
id: sub-003
parent: spec-088
title: "Test Strategy: Directory-Based Selection"
status: planning
files:
  - src/ai_engineering/policy/checks/stack_runner.py
  - tests/unit/*.py
  - tests/integration/*.py
  - tests/e2e/*.py
depends_on: []
---

# Sub-Spec 003: Test Strategy: Directory-Based Selection

## Scope

Change pre-push gate `stack-tests` command from `pytest -m unit` to `pytest tests/unit/ --tb=short -q -x --no-cov -n auto --dist worksteal`. Remove all `pytestmark = pytest.mark.unit/integration/e2e` module-level markers from all test files (~80 files). Keep marker definitions in pyproject.toml for optional manual use. Decision D-088-03.

## Exploration
[EMPTY -- populated by Phase 2]
