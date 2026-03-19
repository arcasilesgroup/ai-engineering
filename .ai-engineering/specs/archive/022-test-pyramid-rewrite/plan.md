---
spec: "022"
approach: "serial-phases"
---

# Plan — Test Pyramid Rewrite

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `tests/unit/test_gates.py` | Mocked unit tests for policy/gates.py |
| `tests/unit/test_installer.py` | Mocked unit tests for installer/service.py |
| `tests/unit/test_doctor.py` | Mocked unit tests for doctor/service.py |
| `tests/unit/test_readiness.py` | Mocked unit tests for detector/readiness.py |
| `tests/unit/test_skills_maintenance.py` | Mocked unit tests for skills/service.py |

### Modified Files

| File | Change |
|------|--------|
| `pyproject.toml` | Add pytest-xdist dependency |
| `src/ai_engineering/policy/gates.py` | Update stack-tests cmd (parallel, unit-only, timeout=120) |
| `.github/workflows/ci.yml` | Split into 3 test stages, reduce smoke matrix |
| `tests/conftest.py` | Optimize fixture scopes |
| `standards/framework/quality/core.md` | Add test performance targets |
| 34 test files | Add pytestmark decorators |

### Mirror Copies

- Template mirrors for pyproject.toml, ci.yml, quality/core.md if applicable.

## File Structure

```
tests/
├── conftest.py               (optimized fixture scopes)
├── unit/                      (13 existing + 5 new mocked = 18 files)
│   ├── test_cli_entrypoint.py      @pytest.mark.unit
│   ├── test_cli_errors.py          @pytest.mark.unit
│   ├── test_doctor.py              NEW — mocked
│   ├── test_duplication_main.py    @pytest.mark.unit
│   ├── test_duplication.py         @pytest.mark.unit
│   ├── test_gates.py               NEW — mocked
│   ├── test_hooks.py               @pytest.mark.unit
│   ├── test_installer.py           NEW — mocked
│   ├── test_pipeline_compliance.py @pytest.mark.unit
│   ├── test_pr_description.py      @pytest.mark.unit
│   ├── test_readiness.py           NEW — mocked
│   ├── test_risk_lifecycle.py      @pytest.mark.unit
│   ├── test_skills_maintenance.py  NEW — mocked
│   ├── test_skills_status.py       @pytest.mark.unit
│   ├── test_state.py               @pytest.mark.unit
│   ├── test_validator_extra.py     @pytest.mark.unit
│   ├── test_validator.py           @pytest.mark.unit
│   └── test_version_lifecycle.py   @pytest.mark.unit
├── integration/               (3 existing + 16 moved = 19 files)
│   ├── test_branch_cleanup.py      MOVED from unit/
│   ├── test_cli_command_modules.py MOVED from unit/
│   ├── test_cli_install_doctor.py  existing
│   ├── test_command_workflows.py   MOVED from unit/
│   ├── test_coverage_closure.py    MOVED from unit/
│   ├── test_doctor.py              MOVED from unit/ (renamed: test_doctor_integration.py)
│   ├── test_gap_fillers4.py        MOVED from unit/
│   ├── test_gates.py               MOVED from unit/ (renamed: test_gates_integration.py)
│   ├── test_git_operations.py      MOVED from unit/
│   ├── test_hooks_git.py           existing
│   ├── test_install_operational_flows.py existing
│   ├── test_installer.py           MOVED from unit/ (renamed: test_installer_integration.py)
│   ├── test_readiness.py           MOVED from unit/ (renamed: test_readiness_integration.py)
│   ├── test_skills_maintenance.py  MOVED from unit/ (renamed: test_skills_integration.py)
│   ├── test_updater.py             MOVED from unit/
│   ├── test_vcs_azure_devops.py    MOVED from unit/
│   ├── test_vcs_factory.py         MOVED from unit/
│   ├── test_vcs_github.py          MOVED from unit/
│   └── test_version_checker.py     MOVED from unit/
└── e2e/                       (2 files, unchanged)
    ├── test_install_clean.py       @pytest.mark.e2e
    └── test_install_existing.py    @pytest.mark.e2e
```

## Session Map

| Phase | Description | Size | Files |
|-------|-------------|------|-------|
| 0 | Scaffold spec | S | 4 spec files |
| 1 | Infrastructure: xdist + markers + gates | M | pyproject.toml, gates.py, 34 test files |
| 2 | Move 16 misplaced tests | M | 16 git mv + rename collisions |
| 3 | Create 5 mocked unit test files | L | 5 new test files |
| 4 | CI optimization | M | ci.yml |
| 5 | Governance + verification | M | quality/core.md, conftest.py, templates |

## Patterns

- Mocked unit tests use `unittest.mock.patch` and `MagicMock`.
- Files moved to integration/ get `pytestmark = pytest.mark.integration`.
- Files that collide on name (e.g., test_gates.py exists in both unit/ and integration/) get `_integration` suffix.
- Commits follow: `spec-022: Phase N — description`.
