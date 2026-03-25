# Plan: spec-070 Update Command Parity with Install

## Pipeline: standard
## Phases: 5
## Tasks: 13 (build: 10, verify: 3)
## Status: COMPLETE

### Phase 1: Expand ownership rules
**Gate**: PASSED

- [x] T-1.1: Add 15 missing ownership rules to `_DEFAULT_OWNERSHIP_PATHS` in `state/defaults.py` (agent: build) -- DONE
- [x] T-1.2: Add tests for new ownership patterns in `tests/unit/test_state.py` (agent: build) -- DONE (27 tests pass)

### Phase 2: Preserve VCS provider in state migration
**Gate**: PASSED

- [x] T-2.1: Add `vcs_provider` and `ai_providers` fields to `InstallState` model in `state/models.py` (agent: build) -- DONE
- [x] T-2.2: Add tests for `from_legacy_dict()` VCS extraction in `tests/unit/state/test_install_state.py` (agent: build) -- DONE (8 tests pass)

### Phase 3: Wire VCS provider and ownership auto-merge into updater
**Gate**: PASSED

- [x] T-3.1: Read VCS provider from install state in `update()` and pass to `_evaluate_project_files()` (agent: build) -- DONE
- [x] T-3.2: Implement ownership auto-merge in `update()` before evaluation (agent: build) -- DONE
- [x] T-3.3: Update integration test for settings.json deny behavior (agent: build) -- DONE (22 updater tests pass)

### Phase 4: Fix CLI status reporting
**Gate**: PASSED

- [x] T-4.1: Add `"info"` status to `status_line()` in `cli_ui.py` (agent: build) -- DONE
- [x] T-4.2: Update `update_cmd()` status logic in `core.py` (agent: build) -- DONE

### Phase 5: Verify all acceptance criteria
**Gate**: PASSED (1925 unit tests, 0 failures)

- [x] T-5.1: Run full test suite — zero regressions (agent: verify) -- DONE (1925 passed)
- [x] T-5.2: All ACs verified via tests
- [x] T-5.3: Ownership rule ordering verified — `.claude/settings.json` deny matches before `.claude/**` allow

### Files Changed
- `src/ai_engineering/state/defaults.py` — 15 new ownership rules
- `src/ai_engineering/state/models.py` — `vcs_provider` + `ai_providers` fields, `from_legacy_dict()` extraction
- `src/ai_engineering/updater/service.py` — VCS wiring, ownership auto-merge, ownership persistence
- `src/ai_engineering/cli_ui.py` — `info` status icon
- `src/ai_engineering/cli_commands/core.py` — 3-way status mapping
- `tests/unit/test_state.py` — 16 new ownership tests, 1 updated test
- `tests/unit/state/test_install_state.py` — 3 new VCS extraction tests
- `tests/integration/test_updater.py` — `test_claude_settings_denied` (replaces `test_claude_settings_updated`)
