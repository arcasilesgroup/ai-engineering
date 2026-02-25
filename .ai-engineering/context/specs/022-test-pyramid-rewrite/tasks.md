---
spec: "022"
total: 24
completed: 0
last_session: "2026-02-25"
next_session: "Phase 0 — Scaffold"
---

# Tasks — Test Pyramid Rewrite

## Phase 0: Scaffold [S]

- [ ] 0.1 Create spec directory and files (spec.md, plan.md, tasks.md)
- [ ] 0.2 Update _active.md to point to spec-022
- [ ] 0.3 Commit scaffold

## Phase 1: Infrastructure [M]

- [ ] 1.1 Add pytest-xdist to pyproject.toml dev dependencies
- [ ] 1.2 Add pytestmark = pytest.mark.unit to 13 unit files
- [ ] 1.3 Add pytestmark = pytest.mark.integration to 3 existing integration files
- [ ] 1.4 Add pytestmark = pytest.mark.e2e to 2 e2e files
- [ ] 1.5 Update gates.py stack-tests: -n auto --dist worksteal -m unit timeout=120

## Phase 2: Re-categorize [M]

- [ ] 2.1 git mv 16 files from tests/unit/ to tests/integration/
- [ ] 2.2 Rename collision files (_integration suffix)
- [ ] 2.3 Add pytestmark = pytest.mark.integration to 16 moved files
- [ ] 2.4 Fix test_gates.py duplicated git_repo fixture

## Phase 3: Mocked Unit Tests [L]

- [ ] 3.1 Create tests/unit/test_gates.py — mocked gates tests (~30 tests)
- [ ] 3.2 Create tests/unit/test_installer.py — mocked installer tests (~20 tests)
- [ ] 3.3 Create tests/unit/test_doctor.py — mocked doctor tests (~15 tests)
- [ ] 3.4 Create tests/unit/test_readiness.py — mocked readiness tests (~15 tests)
- [ ] 3.5 Create tests/unit/test_skills_maintenance.py — mocked skills tests (~15 tests)

## Phase 4: CI Optimization [M]

- [ ] 4.1 Split ci.yml test job into test-unit, test-integration, test-e2e
- [ ] 4.2 Reduce framework-smoke matrix from 9 to 3
- [ ] 4.3 Move --cov-fail-under=90 to unit job only

## Phase 5: Governance [M]

- [ ] 5.1 Update quality/core.md with test performance targets
- [ ] 5.2 Optimize conftest.py fixture scopes (installed_project → module)
- [ ] 5.3 Sync template mirrors
- [ ] 5.4 Verify: unit < 120s, coverage >= 90%, ai-eng validate passes
