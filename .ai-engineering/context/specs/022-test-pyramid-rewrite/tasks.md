---
spec: "022"
total: 24
completed: 24
last_session: "2026-02-25"
next_session: "Done — verification + commit + PR"
---

# Tasks — Test Pyramid Rewrite

## Phase 0: Scaffold [S]

- [x] 0.1 Create spec directory and files (spec.md, plan.md, tasks.md)
- [x] 0.2 Update _active.md to point to spec-022
- [x] 0.3 Commit scaffold

## Phase 1: Infrastructure [M]

- [x] 1.1 Add pytest-xdist to pyproject.toml dev dependencies
- [x] 1.2 Add pytestmark = pytest.mark.unit to 13 unit files
- [x] 1.3 Add pytestmark = pytest.mark.integration to 3 existing integration files
- [x] 1.4 Add pytestmark = pytest.mark.e2e to 2 e2e files
- [x] 1.5 Update gates.py stack-tests: -n auto --dist worksteal -m unit timeout=120

## Phase 2: Re-categorize [M]

- [x] 2.1 git mv 16 files from tests/unit/ to tests/integration/
- [x] 2.2 Rename collision files (_integration suffix)
- [x] 2.3 Add pytestmark = pytest.mark.integration to 16 moved files
- [x] 2.4 Fix test_command_workflows.py git_project fixture (missing git init)

## Phase 3: Mocked Unit Tests [L]

- [x] 3.1 Create tests/unit/test_gates.py — 39 mocked gates tests
- [x] 3.2 Create tests/unit/test_installer.py — 43 mocked installer tests
- [x] 3.3 Create tests/unit/test_doctor.py — 19 mocked doctor tests
- [x] 3.4 Create tests/unit/test_readiness.py — 20 mocked readiness tests
- [x] 3.5 Create tests/unit/test_skills_maintenance.py — 17 mocked skills tests

## Phase 4: CI Optimization [M]

- [x] 4.1 Split ci.yml test job into test-unit, test-integration, test-e2e
- [x] 4.2 Reduce framework-smoke matrix from 9 to 3
- [x] 4.3 Move --cov-fail-under=90 to unit job only

## Phase 5: Governance [M]

- [x] 5.1 Update quality/core.md with test performance targets + gate structure
- [x] 5.2 Sync template mirrors (quality/core.md, test-runner SKILL.md)
- [x] 5.3 Update test-runner SKILL.md with pyramid enforcement + tiered commands
- [x] 5.4 Verify: unit < 120s, coverage >= 90%, ai-eng validate passes
