---
spec: "010"
total: 20
completed: 20
last_session: "2026-02-11"
next_session: "Done — PR pending"
---

# Tasks — Version Lifecycle

## Phase 0: Scaffold [S]

- [x] 0.1 Create branch `feat/010-version-lifecycle` from main
- [x] 0.2 Create spec 010 scaffold (spec.md, plan.md, tasks.md)
- [x] 0.3 Activate spec 010 in _active.md
- [x] 0.4 Update product-contract.md → 010

## Phase 1: Models & Registry [S]

- [x] 1.1 Create `src/ai_engineering/version/__init__.py` with public API exports
- [x] 1.2 Create `src/ai_engineering/version/models.py` — VersionStatus enum, VersionEntry model, VersionRegistry model
- [x] 1.3 Create `src/ai_engineering/version/registry.json` — initial registry with 0.1.0 as "current"

## Phase 2: Checker Service [S]

- [x] 2.1 Create `src/ai_engineering/version/checker.py` — VersionCheckResult dataclass
- [x] 2.2 Implement `load_registry()` — load bundled registry.json from package data
- [x] 2.3 Implement `check_version()` — pure function comparing installed vs registry
- [x] 2.4 Implement `find_latest_version()` and `find_version_entry()` helpers

## Phase 3: CLI Integration [M]

- [x] 3.1 Add `_version_lifecycle_callback()` to `cli_factory.py` — deprecation block + outdated warning
- [x] 3.2 Enhance `version_cmd()` in `cli_commands/core.py` — show lifecycle status from registry
- [x] 3.3 Update `pyproject.toml` — add `version/registry.json` to wheel includes

## Phase 4: Doctor & Gate Integration [M]

- [x] 4.1 Add `_check_version()` to `doctor/service.py` — diagnostic check (OK/WARN/FAIL)
- [x] 4.2 Add `_check_version_deprecation()` to `policy/gates.py` — gate check before branch protection
- [x] 4.3 Add `version_status` field to `MaintenanceReport` in `maintenance/report.py`

## Phase 5: Tests [M]

- [x] 5.1 Create `tests/unit/test_version_checker.py` — model parsing, check_version (current, outdated, deprecated, eol, unknown), find_latest, semver comparison, load_registry, graceful errors
- [x] 5.2 Create `tests/unit/test_version_lifecycle.py` — CLI callback tests: blocks deprecated (non-exempt), allows exempt commands, warns outdated, silent when current, graceful on registry error
- [x] 5.3 Extend `tests/unit/test_doctor.py` — version check appears in doctor report
- [x] 5.4 Extend `tests/unit/test_gates.py` — deprecation blocks gate, outdated doesn't block
- [x] 5.5 Verify >=90% coverage on `src/ai_engineering/version/` and no regressions
