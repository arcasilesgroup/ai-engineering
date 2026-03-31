---
total: 12
completed: 0
confidence: high
---

# Plan: sub-003 Version & Commit Modernization

```
exports: [pyproject.toml [tool.semantic_release] config, conventional commit format in ai-commit/SKILL.md]
imports: [ci-build.yml from sub-002]
```

## Plan

### T-3.1: Configure python-semantic-release in pyproject.toml

Add `[tool.semantic_release]` and `[tool.semantic_release.commit_parser_options]` sections. Configure `version_toml` to point at `pyproject.toml:project.version` (single source). Set `commit_parser = "angular"`, `tag_format = "v{version}"`, `major_on_zero = false`. Disable automatic changelog generation (CHANGELOG is manual per existing convention). Configure branch to `main`. Add `python-semantic-release` to dev dependency group.

**Files**: `pyproject.toml`
**Done**: `[tool.semantic_release]` section present with correct `version_toml`, `commit_parser`, `tag_format`, `major_on_zero`, `branch` values. `python-semantic-release` in dev deps. `ruff check` clean.

### T-3.2: Eliminate __version__.py, update __init__.py with importlib.metadata

Delete `src/ai_engineering/__version__.py`. Update `src/ai_engineering/__init__.py` to use `importlib.metadata.version("ai-engineering")` with `except Exception` fallback to `"0.0.0"` for editable installs. Keep `__all__ = ["__version__"]` export.

**Files**: `src/ai_engineering/__version__.py` (delete), `src/ai_engineering/__init__.py`
**Done**: `__version__.py` does not exist. `__init__.py` uses `importlib.metadata`. `from ai_engineering import __version__` returns a version string. `python -c "from ai_engineering import __version__; print(__version__)"` works.

### T-3.3: Update all __version__ imports across codebase (5 files)

Change 4 files from `from ai_engineering.__version__ import __version__` to `from ai_engineering import __version__`. The 5th file (`doctor/runtime/version.py`) already uses the correct form and needs no change.

Files to update:
1. `src/ai_engineering/cli_ui.py` -- line 22
2. `src/ai_engineering/cli_commands/core.py` -- line 19
3. `src/ai_engineering/cli_factory.py` -- line 143 (lazy import inside `_app_callback`)
4. `src/ai_engineering/policy/checks/branch_protection.py` -- line 35 (lazy import inside `check_version_deprecation`)

**Files**: `src/ai_engineering/cli_ui.py`, `src/ai_engineering/cli_commands/core.py`, `src/ai_engineering/cli_factory.py`, `src/ai_engineering/policy/checks/branch_protection.py`
**Done**: Zero occurrences of `from ai_engineering.__version__` in codebase. All 4 files import `from ai_engineering import __version__`. `ruff check` clean. No import errors.

### T-3.4: Update version_bump.py for single-file management

Remove `_find_version_file()` function entirely. Simplify `bump_python_version()` to only update `pyproject.toml` -- remove all `__version__.py` read/write/regex logic (lines 148-161). `BumpResult.files_modified` returns `[pyproject]` only (single element list). `detect_current_version()` stays unchanged (already reads from pyproject.toml).

**Files**: `src/ai_engineering/release/version_bump.py`
**Done**: No `_find_version_file` function. `bump_python_version()` modifies only `pyproject.toml`. `BumpResult.files_modified` is a single-element list. No references to `__version__.py` in the file. `ruff check` clean.

### T-3.5: Update orchestrator.py to remove __version__.py references

Update `_prepare_branch()` to handle simplified `bump_python_version()` return. Replace the hardcoded `str(bump.files_modified[1])` at line 375 with a dynamic approach using all items from `bump.files_modified`. Update `git add` command to use `[str(p.relative_to(config.project_root)) for p in bump.files_modified]` unpacked into the args list.

**Files**: `src/ai_engineering/release/orchestrator.py`
**Done**: No `__version__.py` string literal in the file. `git add` command uses `*[str(f) for f in bump.files_modified]`. No `IndexError` when `files_modified` has 1 element. `ruff check` clean.

### T-3.6: Update commit_msg.py for dual-format acceptance

Add conventional commit format validation to `validate_commit_message()`. Define `_CONVENTIONAL_RE` regex matching `type(optional-scope): description` and `type: description`. Define `_LEGACY_SPEC_RE` matching `spec-NNN: description`. Add a validation check: if the first line matches either pattern, it passes. If it matches neither, add a warning (not error) suggesting conventional format. Keep existing empty/length checks unchanged. This is a transitional state -- Phase 6 (sub-006) removes legacy acceptance.

**Files**: `src/ai_engineering/policy/checks/commit_msg.py`
**Done**: `validate_commit_message("feat(spec-097): add feature")` returns `[]`. `validate_commit_message("spec-097: add feature")` returns `[]`. `validate_commit_message("fix: resolve bug")` returns `[]`. `validate_commit_message("")` returns errors. `validate_commit_message("a" * 73)` returns errors. `ruff check` clean.

### T-3.7: Update ai-commit SKILL.md with conventional commit format

Change step 7 commit format from `spec-NNN: Task X.Y -- <description>` to conventional commit format:
- **With active spec**: `feat(spec-NNN): Task X.Y -- <description>` (features), `fix(spec-NNN): <description>` (fixes), `chore(spec-NNN): <description>` (internal)
- **Without spec**: `type(scope): description` (conventional commits, imperative mood)

Update the "Common Mistakes" section to reference conventional commit format.

**Files**: `.claude/skills/ai-commit/SKILL.md`
**Done**: No `spec-NNN: Task` pattern in the file. Conventional commit format documented in step 7. Both spec and non-spec examples shown.

### T-3.8: Update ai-pr SKILL.md and pr_description.py

Update `.claude/skills/ai-pr/SKILL.md` PR title format section (line 184) to use `feat(spec-NNN): title` as primary format. Remove `spec-NNN: Task X.Y -- description` as an option.

Update `src/ai_engineering/vcs/pr_description.py` `build_pr_title()` to generate conventional format: change `f"spec-{spec}: {slug}"` to `f"feat(spec-{spec}): {slug}"`.

**Files**: `.claude/skills/ai-pr/SKILL.md`, `src/ai_engineering/vcs/pr_description.py`
**Done**: `build_pr_title()` returns `feat(spec-NNN): slug` when spec is active. SKILL.md shows conventional format as primary. `ruff check` clean.

### T-3.9: Sync skill mirrors via sync_command_mirrors.py

Run `python scripts/sync_command_mirrors.py` to propagate ai-commit and ai-pr SKILL.md changes to all 8 mirror surfaces: `.codex/skills/`, `.github/skills/`, `.gemini/skills/`, and all `templates/project/` variants for each IDE.

Then run `python scripts/sync_command_mirrors.py --check` to verify zero drift.

**Files**: `scripts/sync_command_mirrors.py` (executor, not modified), plus all mirror targets (16 files: 2 skills x 8 surfaces)
**Done**: `python scripts/sync_command_mirrors.py --check` exits with code 0. All mirrors match canonical `.claude/` sources.

### T-3.10: Integrate semantic-release into ci-build.yml

Add semantic-release step to `ci-build.yml` (created by sub-002) after the `uv build` step. The step runs `semantic-release version --no-push --no-commit` to determine the next version. If a bump is needed: create git tag, create draft GitHub Release with dist artifacts attached. If no bump: skip tag/release/artifact-upload (silent no-op per D-097-06).

Requires `contents: write` permission for tag creation and `id-token: write` for GitHub Release. Install `python-semantic-release` in the workflow before running.

**Files**: `.github/workflows/ci-build.yml`
**Done**: ci-build.yml contains semantic-release step. Step is conditional on bump detection. Tag and draft release created only when bump occurs. `python scripts/check_workflow_policy.py` passes for ci-build.yml.

### T-3.11: Write/update tests for commit_msg and version_bump

**commit_msg tests** (both `tests/unit/test_gates.py` and `tests/integration/test_gates_integration.py`):
- Add test for conventional commit: `feat(scope): description` passes
- Add test for conventional commit without scope: `fix: description` passes
- Add test for legacy spec format: `spec-097: description` passes (transition)
- Add test for breaking change footer acceptance
- Add test for invalid format still caught (empty, too long)

**version_bump tests** (`tests/unit/test_version_bump.py`):
- Update `_write_project()` helper to NOT create `__version__.py`
- Update `test_bump_python_version_updates_pyproject_and_version_file` to only assert pyproject.toml
- Remove `test_bump_python_version_raises_when_version_file_missing`
- Remove `test_bump_python_version_raises_when_version_assignment_missing`
- Add test: `bump_python_version` returns single-element `files_modified`

**orchestrator tests** (`tests/unit/test_release_orchestrator.py`):
- Update `bump.files_modified` in `test_prepare_branch_success_path` to `[tmp_path / "pyproject.toml"]` (single element)
- Update `_prepare_branch` mock output in `test_execute_release_wait_path_success` to `"pyproject.toml"` only
- Update `test_prepare_branch_promote_add_commit_error_paths` mock data

**Files**: `tests/unit/test_gates.py`, `tests/integration/test_gates_integration.py`, `tests/unit/test_version_bump.py`, `tests/unit/test_release_orchestrator.py`
**Done**: `pytest tests/unit/test_gates.py tests/unit/test_version_bump.py tests/unit/test_release_orchestrator.py tests/integration/test_gates_integration.py -v` all pass. No `__version__.py` references in test files. New conventional commit tests present.

### T-3.12: Verify semantic-release dry-run

Run `semantic-release --dry-run version` to confirm:
1. Commit parser recognizes existing conventional commits in history
2. Version detection reads from `pyproject.toml` correctly
3. No errors from the configuration
4. `ruff check` and `ty check src/` clean
5. Full `pytest` suite passes

**Files**: None (verification only)
**Done**: `semantic-release version --dry-run` exits 0. No config errors. Full test suite passes. Lint clean.

## Confidence

**High**. The changes are well-scoped and follow established Python packaging patterns. Key risk factors are mitigated:

1. **importlib.metadata** is the standard approach since Python 3.8+ and works with hatchling out of the box.
2. **Dual-format commit validation** is additive -- no existing behavior is broken, only new format is accepted alongside legacy.
3. **python-semantic-release v9** has stable configuration format and good documentation for `version_toml` single-source pattern.
4. **Mirror sync** is fully automated via existing `sync_command_mirrors.py` -- no manual copying needed.
5. **Test updates** are mechanical -- removing `__version__.py` references and adding conventional commit assertions.
6. **ci-build.yml dependency** on sub-002 is explicit in the manifest and the plan accounts for sequencing.

The only medium-risk item is editable install fallback testing -- this requires verifying the `except Exception` branch in a real editable install scenario, which may need manual verification beyond unit tests.

## Self-Report
[EMPTY -- populated by Phase 4]
