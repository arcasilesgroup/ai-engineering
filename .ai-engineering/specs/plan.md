# Plan: spec-072 Install UX: Recursive Detection, Popularity Ordering, Git Init

## Pipeline: standard
## Phases: 4
## Tasks: 18 (build: 14, verify: 4)
## Status: COMPLETE

---

### Phase 1: Core Infrastructure — Popularity Ordering + Recursive Walker

**Gate**: `_order_by_popularity()` works correctly, walker detects markers recursively with exclusions, all new unit tests pass.

- [ ] T-1.1: Write tests for `_order_by_popularity()` helper (agent: build)
  - File: `tests/unit/installer/test_autodetect.py`
  - Tests: ranked items come first in order, unknown items appended alphabetically, empty input, all-unknown input
  - RED phase — tests must fail initially

- [ ] T-1.2: Implement `_order_by_popularity()` + popularity tuples in `autodetect.py` (agent: build)
  - Add `_STACK_POPULARITY`, `_IDE_POPULARITY`, `_PROVIDER_POPULARITY`, `_VCS_POPULARITY` tuples
  - Add `_order_by_popularity(items: Iterable[str], ranking: tuple[str, ...]) -> list[str]`
  - GREEN phase — T-1.1 tests must pass
  - Constraint: do NOT modify test files from T-1.1

- [ ] T-1.3: Write tests for recursive walker `_walk_markers()` (agent: build)
  - File: `tests/unit/installer/test_autodetect.py`
  - Tests: monorepo with nested markers, exclusion dirs skipped, symlinks not followed, JS/TS per-directory in different subdirs, `.vscode`/`.idea` at any level, AI providers NOT detected by walker
  - RED phase

- [ ] T-1.4: Implement `_walk_markers()` and refactor `detect_stacks()`/`detect_ides()`/`detect_all()` (agent: build)
  - Add `_WALK_EXCLUDE` frozenset
  - Implement `_walk_markers(root)` as single-pass `os.walk` with pruning
  - `detect_stacks()` -> thin wrapper calling `_walk_markers()`, returning popularity-ordered results
  - `detect_ides()` -> thin wrapper calling `_walk_markers()`, returning popularity-ordered results
  - `detect_all()` -> calls `_walk_markers()` once, distributes. `detect_ai_providers()` remains root-only
  - GREEN phase — T-1.3 tests must pass
  - Constraint: do NOT modify test files from T-1.3

- [ ] T-1.5: Update existing `test_autodetect.py` tests for new behavior (agent: build)
  - Update ordering assertions (alphabetical -> popularity)
  - Update shallow detection tests to validate recursive behavior
  - `test_exception_falls_back_to_github` -> deferred to Phase 2 (VCS change)
  - Ensure all 41 existing tests pass or are correctly updated

---

### Phase 2: VCS Changes — No Default, Empty Detection, Wizard UX

**Gate**: VCS detection returns `""` on failure, wizard handles empty VCS with "Detected: none" note, Ctrl+C aborts install, all unit tests pass.

- [ ] T-2.1: Write tests for VCS empty detection + wizard changes (agent: build)
  - File: `tests/unit/installer/test_autodetect.py` — `detect_vcs()` returns `""` on failure
  - File: `tests/unit/installer/test_wizard.py` — empty VCS shows no default, Ctrl+C raises `SystemExit(1)`, "Detected: none" note, popularity ordering in all prompts
  - RED phase

- [ ] T-2.2: Update `detect_vcs()` in `autodetect.py` to return `""` on failure (agent: build)
  - Wrapper logic: catch exception from `detect_from_remote()`, return `""`
  - Also handle: `detect_from_remote()` returns `"github"` but subprocess failed -> return `""`
  - `detect_from_remote()` in `vcs/factory.py` NOT modified
  - GREEN phase for autodetect tests from T-2.1

- [ ] T-2.3: Update `wizard.py` — popularity ordering + VCS changes (agent: build)
  - Import popularity tuples from `autodetect.py`
  - Use `_order_by_popularity()` for all checkbox/select choice lists
  - Make `_ask_select()` `default` optional (`default: str | None = None`)
  - When `default=None`, call `questionary.select()` without `default` kwarg
  - Ctrl+C on VCS select -> `raise SystemExit(1)` instead of returning `_DEFAULT_VCS`
  - Remove `_DEFAULT_VCS` constant
  - Add "Detected: none" styled print before VCS prompt when `detected.vcs` is empty
  - GREEN phase for wizard tests from T-2.1

- [ ] T-2.4: Update `_detect_vcs()` in `phases/detect.py` + VCS overwrite guard (agent: build)
  - `_detect_vcs()` returns `""` on subprocess failure instead of `"github"`
  - `DetectPhase.execute()`: only overwrite `context.vcs_provider` when detected value is non-empty
  - Update existing `test_detect.py` tests accordingly

- [ ] T-2.5: Update `ui.py` `render_detection()` for empty VCS (agent: build)
  - When `vcs` is empty, display "none detected" instead of empty string
  - File: `installer/ui.py`

- [ ] T-2.6: Update existing `test_wizard.py` tests for new behavior (agent: build)
  - Update ordering assertions (alphabetical -> popularity)
  - Update `test_select_returns_none_defaults_to_github` -> expect `SystemExit(1)`
  - Update `test_vcs_default_from_detection` -> handle empty VCS
  - Ensure all 22 existing tests pass or are correctly updated

---

### Phase 3: Git Init + Hooks Strictness

**Gate**: `git init` runs automatically on non-git directories, hooks never silently fail, `verify()` returns `passed=False` on missing hooks, all tests pass.

- [ ] T-3.1: Write tests for git init in detect phase + strict hooks (agent: build)
  - File: `tests/unit/installer/test_detect.py` — `.git/` absent -> plan includes `git init` action, execute runs `git init`, git-not-installed -> `InstallerError`
  - File: `tests/unit/installer/test_phases.py` — `HooksPhase.verify()` returns `passed=False` when hooks missing, `execute()` propagates `FileNotFoundError` (no suppress)
  - RED phase

- [ ] T-3.2: Implement git init in `DetectPhase` (agent: build)
  - `plan()`: check `context.target / ".git"`, add create action if missing
  - `execute()`: run `subprocess.run(["git", "init"], cwd=..., check=True)`, catch `FileNotFoundError` -> raise `InstallerError("git is required but not installed")`
  - File: `installer/phases/detect.py`
  - GREEN phase for detect tests from T-3.1

- [ ] T-3.3: Remove `contextlib.suppress` from hooks + strict verify (agent: build)
  - `HooksPhase.execute()`: remove `contextlib.suppress(FileNotFoundError)` wrapper
  - `HooksPhase.verify()`: return `passed=False` when pre-commit hook missing
  - Legacy `install()` at `service.py:164`: remove `contextlib.suppress`, add git init before `install_hooks()`
  - Files: `installer/phases/hooks.py`, `installer/service.py`
  - GREEN phase for hooks tests from T-3.1

- [ ] T-3.4: Update existing `test_phases.py` and `test_installer.py` tests (agent: build)
  - Update any test expecting silent hook failure -> expect propagation
  - Update any test expecting `verify() -> passed=True` with missing hooks -> `passed=False`
  - Ensure all existing tests pass or are correctly updated

---

### Phase 4: Integration Verification

**Gate**: All unit tests pass, integration test passes, linter clean, zero regressions.

- [ ] T-4.1: Write integration test for empty directory install (agent: build)
  - File: `tests/integration/test_cli_install_doctor.py`
  - Test: create empty `tmp_path`, run install pipeline, assert `.git/` exists, `.git/hooks/pre-commit` exists and executable, stacks/IDEs properly detected if markers exist in subdirs

- [ ] T-4.2: Run full test suite + linter (agent: verify)
  - `pytest tests/ -x --tb=short`
  - `ruff check src/ tests/`
  - `ty check src/`
  - All must pass with zero failures

- [ ] T-4.3: Verify all 18 ACs from spec (agent: verify)
  - Walk through each AC and confirm it is covered by a passing test
  - Flag any AC without test coverage

- [ ] T-4.4: Run gitleaks on staged changes (agent: verify)
  - `gitleaks protect --staged --no-banner`
  - Must pass with zero findings

## Task Dependency Graph

```
T-1.1 -> T-1.2 -> T-1.3 -> T-1.4 -> T-1.5
                                        |
T-2.1 -> T-2.2 -> T-2.3 -> T-2.4 -> T-2.5 -> T-2.6
                                                 |
T-3.1 -> T-3.2 -> T-3.3 -> T-3.4
                               |
T-4.1 -> T-4.2 -> T-4.3 -> T-4.4
```

Phase 1 completes before Phase 2 starts (wizard depends on popularity tuples).
Phase 2 completes before Phase 3 starts (detect phase VCS changes needed before git init).
Phase 3 completes before Phase 4 starts (all code changes done before integration verification).

## Files Modified Summary

| File | Tasks | Change Type |
|------|-------|-------------|
| `installer/autodetect.py` | T-1.2, T-1.4, T-2.2 | Walker, popularity, VCS empty |
| `installer/wizard.py` | T-2.3 | Popularity ordering, VCS UX |
| `installer/ui.py` | T-2.5 | Empty VCS display |
| `installer/phases/detect.py` | T-2.4, T-3.2 | VCS empty, git init |
| `installer/phases/hooks.py` | T-3.3 | Remove suppress, strict verify |
| `installer/service.py` | T-3.3 | Legacy path fix |
| `tests/unit/installer/test_autodetect.py` | T-1.1, T-1.3, T-1.5, T-2.1 | New + updated tests |
| `tests/unit/installer/test_wizard.py` | T-2.1, T-2.6 | New + updated tests |
| `tests/unit/installer/test_detect.py` | T-2.4, T-3.1 | New + updated tests |
| `tests/unit/installer/test_phases.py` | T-3.1, T-3.4 | New + updated tests |
| `tests/unit/test_installer.py` | T-3.4 | Updated tests |
| `tests/integration/test_cli_install_doctor.py` | T-4.1 | New integration test |
