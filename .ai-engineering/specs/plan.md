# Plan: spec-099 First-run experience - wizard validation, warnings, and gate generalization

## Pipeline: standard
## Phases: 3
## Tasks: 16 (build: 13, verify: 3)

### Phase 1: Tests + surgical one-liner fixes
**Gate**: New tests exist (RED for wizard/gates/validation). One-liner state/dedup/display fixes applied. Existing tests pass.

- [x] T-1.1: Write failing tests for wizard checkbox validation — `validate` rejects empty list, `instruction` parameter is passed to `questionary.checkbox` (file: `tests/unit/installer/test_wizard.py`) (agent: build) -- DONE
- [x] T-1.2: Write failing tests for dynamic Python path detection — source root from `pyproject.toml` `[tool.hatch.build]`/`[tool.setuptools]`, test dir from `[tool.pytest.ini_options] testpaths` or probe `tests/`/`test/`, graceful skip when path missing (file: `tests/unit/test_stack_runner.py`) (agent: build) -- DONE
- [x] T-1.3: Write failing test for project validation in `install_cmd` — warns on non-project directory, aborts in `--non-interactive` mode (file: `tests/unit/test_install_validation.py`) (agent: build) -- DONE
- [x] T-1.4: Add `state.vcs_provider = vcs_provider` in `_run_operational_phases()` at `service.py:509` before `save_install_state()` call at line 510 (D-099-02) (agent: build) -- DONE
- [x] T-1.5: Remove ToolsPhase warning promotion — delete `elif phase_result.phase_name == PHASE_TOOLS` block at `service.py:296-297` in `_summary_to_install_result()` (D-099-03) (agent: build) -- DONE
- [x] T-1.6: Replace hardcoded `phase_names` list at `core.py:383-390` with `PHASE_ORDER` import from `installer/phases/__init__.py` (D-099-08) (agent: build) -- DONE

### Phase 2: Wizard validation + gate generalization
**Gate**: Wizard validates empty selections with re-prompt + spacebar hint. Python gates use dynamic paths. Duplication/CVE cleaned. All tests GREEN.

- [x] T-2.1: Add `validate` callback (reject empty) and `instruction` string to `_ask_checkbox` in `wizard.py:60-65`, pass through at call sites lines 107, 114, 122 (D-099-01) (agent: build) -- DONE
- [x] T-2.2: Add `detect_python_source_root(project_root)` and `detect_python_test_dir(project_root)` helpers to `stack_runner.py` — parse `pyproject.toml` with `tomllib`, fallback chain: config → `src/` probe → `.` for source, `testpaths` → `tests/` → `test/` for tests (D-099-05) (agent: build) -- DONE
- [x] T-2.3: Update Python `PRE_PUSH_CHECKS` entries (`stack-tests`, `ty-check`) to call helpers from T-2.2. If path does not exist, check passes with skip message instead of failing (D-099-05) (agent: build) -- DONE
- [x] T-2.4: Remove `duplication-check` entry from `PRE_PUSH_CHECKS["python"]` in `stack_runner.py:77-88` (D-099-06) (agent: build) -- DONE
- [x] T-2.5: Remove `--ignore-vuln CVE-2026-4539` from `pip-audit` check at `stack_runner.py:54-57`. Add `[tool.pip-audit]` section to `pyproject.toml` with the exemption for ai-engineering's own CI (D-099-07) (agent: build) -- DONE
- [x] T-2.6: Verify phase 2 — all tests pass, lint clean, format clean (agent: verify) -- DONE

### Phase 3: Install safety + documentation
**Gate**: Project validation works in interactive and non-interactive modes. Docs updated. All 9 spec-099 goals verified.

- [x] T-3.1: Add project validation guard in `install_cmd()` at `core.py:~123` after `resolve_project_root()` — check for project signals (`.git`, `pyproject.toml`, `package.json`, `*.sln`, `go.mod`, `Cargo.toml`, `tsconfig.json`), warn+confirm in interactive, abort in `--non-interactive` (D-099-04) (agent: build) -- DONE
- [x] T-3.2: Add contributor install flow section to `CONTRIBUTING.md` — `git clone`, venv setup, `pip install -e ".[dev]"`, run tests (agent: build) -- DONE
- [x] T-3.3: Expand branch policy help text with actionable setup steps — what to enable in GitHub/Azure DevOps settings, required status checks, reviewer requirements (agent: build) -- DONE
- [x] T-3.4: Final verification — all 9 spec-099 goals checkable, no regressions, full test suite passes (agent: verify) -- DONE (2464 passed, 2 pre-existing failures in test_update_provider_filtering.py unrelated to spec-099)
