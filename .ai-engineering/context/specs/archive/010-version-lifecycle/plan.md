---
spec: "010"
approach: "serial-phases"
---

# Plan — Version Lifecycle

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `src/ai_engineering/version/__init__.py` | Package init, re-export public API |
| `src/ai_engineering/version/models.py` | VersionStatus, VersionEntry, VersionRegistry Pydantic models |
| `src/ai_engineering/version/checker.py` | Pure check logic: load_registry, check_version, find_latest |
| `src/ai_engineering/version/registry.json` | Embedded version registry data |
| `tests/unit/test_version_checker.py` | Unit tests for models + checker |
| `tests/unit/test_version_lifecycle.py` | CLI callback + integration tests |

### Modified Files

| File | Change |
|------|--------|
| `src/ai_engineering/cli_factory.py` | Add app-level callback `_version_lifecycle_callback` |
| `src/ai_engineering/cli_commands/core.py` | Enhance `version_cmd` with registry status |
| `src/ai_engineering/doctor/service.py` | Add `_check_version()` diagnostic |
| `src/ai_engineering/policy/gates.py` | Add `_check_version_deprecation()` gate check |
| `src/ai_engineering/maintenance/report.py` | Add `version_status` field to MaintenanceReport |
| `pyproject.toml` | Add registry.json to wheel includes |

### Reusable Existing Patterns

- `state/models.py` — StrEnum, BaseModel, Field(alias=...), model_config pattern
- `state/io.py::read_json_model()` — JSON to Pydantic model loading
- `doctor/service.py::CheckResult` — diagnostic check pattern (name, status, message)
- `policy/gates.py::GateCheckResult` — gate check pattern (name, passed, output)
- `policy/gates.py::_load_decision_store()` — risk acceptance lookup pattern
- `state/models.py::AuditEntry` — audit event logging

## Session Map

| Phase | Name | Size | Description |
|-------|------|------|-------------|
| 0 | Scaffold | S | Spec files, branch, activate |
| 1 | Models & Registry | S | VersionStatus, VersionEntry, VersionRegistry, registry.json |
| 2 | Checker Service | S | Pure check functions, load_registry |
| 3 | CLI Integration | M | App callback, version_cmd enhancement, pyproject.toml |
| 4 | Doctor & Gate Integration | M | Doctor check, gate check, maintenance report |
| 5 | Tests | M | Unit tests, integration tests, coverage verification |

## Patterns

- All new code in `version/` subpackage — self-contained
- Pure functions in checker.py — no side effects, easy to test
- Pydantic models follow state/models.py conventions exactly
- Tests follow existing patterns: `tmp_path`, `unittest.mock.patch`, class-based `Test*`
