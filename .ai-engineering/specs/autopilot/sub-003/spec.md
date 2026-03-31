---
id: sub-003
parent: spec-097
title: "Version & Commit Modernization"
status: planning
files:
  # Python source (version imports)
  - pyproject.toml
  - src/ai_engineering/__version__.py
  - src/ai_engineering/__init__.py
  - src/ai_engineering/cli_ui.py
  - src/ai_engineering/cli_commands/core.py
  - src/ai_engineering/cli_factory.py
  - src/ai_engineering/doctor/runtime/version.py
  - src/ai_engineering/policy/checks/branch_protection.py
  # Commit validation + version management
  - src/ai_engineering/policy/checks/commit_msg.py
  - src/ai_engineering/release/version_bump.py
  - src/ai_engineering/release/orchestrator.py
  # PR description
  - src/ai_engineering/vcs/pr_description.py
  # Skills (canonical .claude source)
  - .claude/skills/ai-commit/SKILL.md
  - .claude/skills/ai-pr/SKILL.md
  # Tests
  - tests/unit/test_version_bump.py
  - tests/unit/test_release_orchestrator.py
  - tests/unit/test_gates.py
  - tests/integration/test_gates_integration.py
  # Mirror sync
  - scripts/sync_command_mirrors.py
  # CI (dependency from sub-002)
  - .github/workflows/ci-build.yml
depends_on: ["sub-002"]
---

# Sub-Spec 003: Version & Commit Modernization

## Scope

Adopt python-semantic-release with conventional commits. Eliminate `__version__.py` (single version source in `pyproject.toml` via `importlib.metadata`). Configure `[tool.semantic_release]` in pyproject.toml. Update `commit_msg.py` to accept both legacy and conventional formats. Update `/ai-commit` and `/ai-pr` skills. Update `version_bump.py` and `orchestrator.py`. Sync mirrors. Integrate semantic-release into ci-build.yml. Covers spec-097 Phase 3 and decisions D-097-03, D-097-06, D-097-12.

## Exploration

### Existing Files

#### `pyproject.toml`
- **Current state**: `version = "0.1.0"` under `[project]` (line 3). Build system is hatchling (`[build-system] requires = ["hatchling>=1.25.0"]`). No `[tool.semantic_release]` section exists. Existing tool sections: `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.lint.isort]`, `[tool.pytest.ini_options]`, `[tool.hatch.build.targets.wheel]`.
- **Imports**: None (this is the version source of truth after migration).
- **Exports**: Version string consumed by all `__version__` importers.
- **Action**: Add `[tool.semantic_release]` section. Keep `version = "0.1.0"` as the single source. No hatchling dynamic versioning needed -- `importlib.metadata` reads from installed package metadata which hatchling populates from this field.

#### `src/ai_engineering/__version__.py`
- **Current state**: Single line: `__version__ = "0.1.0"`. This is the file to be **deleted**.
- **Exports**: `__version__` string imported by 5 modules.
- **Action**: Delete this file entirely.

#### `src/ai_engineering/__init__.py`
- **Current state**: Line 8: `from ai_engineering.__version__ import __version__`. Re-exports `__version__` in `__all__`.
- **Exports**: `__version__` re-exported for `from ai_engineering import __version__` pattern.
- **Action**: Replace import with `importlib.metadata.version("ai-engineering")` with fallback for editable installs.

#### `src/ai_engineering/cli_ui.py`
- **Current state**: Line 22: `from ai_engineering.__version__ import __version__`. Uses `__version__` in `show_logo()` (line 112) to display version in the CLI banner.
- **Action**: Change import to `from ai_engineering import __version__` (use the __init__.py re-export).

#### `src/ai_engineering/cli_commands/core.py`
- **Current state**: Line 19: `from ai_engineering.__version__ import __version__`. Uses `__version__` in `version_cmd()` (lines 815, 818, 823) for version display and lifecycle check.
- **Action**: Change import to `from ai_engineering import __version__`.

#### `src/ai_engineering/cli_factory.py`
- **Current state**: Line 143 (inside `_app_callback`): `from ai_engineering.__version__ import __version__`. Lazy import used for version lifecycle blocking.
- **Action**: Change import to `from ai_engineering import __version__`.

#### `src/ai_engineering/doctor/runtime/version.py`
- **Current state**: Line 14: `from ai_engineering import __version__`. Already uses the __init__.py re-export pattern -- this import is correct after migration and needs **no change**.
- **Action**: None. Already correct.

#### `src/ai_engineering/policy/checks/branch_protection.py`
- **Current state**: Line 35 (inside `check_version_deprecation`): `from ai_engineering.__version__ import __version__`. Lazy import.
- **Action**: Change import to `from ai_engineering import __version__`.

#### `src/ai_engineering/policy/checks/commit_msg.py`
- **Current state**: Two functions: `validate_commit_message(msg)` and `inject_gate_trailer(commit_msg_file)`. Validation checks: non-empty, first line non-empty, first line <= 72 chars. No format-specific validation (no conventional commit check, no spec-NNN check). Very permissive -- anything with a non-empty first line under 72 chars passes.
- **Action**: Add conventional commit format recognition. Accept both `type(scope): description` and legacy `spec-NNN: description` during transition period. The current validator is format-agnostic, so we add format awareness without breaking existing behavior.

#### `src/ai_engineering/release/version_bump.py`
- **Current state**: `_find_version_file()` (line 114) locates `__version__.py` under `src/`. `bump_python_version()` (line 126) updates both `pyproject.toml` and `__version__.py`. `detect_current_version()` (line 103) reads from `pyproject.toml` only.
- **Exports**: `BumpResult`, `validate_semver`, `compare_versions`, `detect_current_version`, `bump_python_version`.
- **Action**: Remove `_find_version_file()`. Simplify `bump_python_version()` to update only `pyproject.toml`. Remove all `__version__.py` update logic. `detect_current_version()` stays as-is (already reads from pyproject.toml).

#### `src/ai_engineering/release/orchestrator.py`
- **Current state**: `_prepare_branch()` (line 344) calls `bump_python_version()` and references `bump.files_modified[1]` (the __version__.py path) in the `git add` command. Commit message uses `chore(release): v{version}` (already conventional format). The `git add` at line 374 explicitly names `str(bump.files_modified[1])`.
- **Action**: Update `_prepare_branch()` to handle the simplified `bump_python_version()` return value (only pyproject.toml modified). Remove hardcoded `bump.files_modified[1]` index. Use the full `files_modified` list for `git add`.

#### `src/ai_engineering/vcs/pr_description.py`
- **Current state**: `build_pr_title()` (line 22) generates format `spec-{spec}: {slug}` when a spec is active. `_humanize_branch()` strips `feat/`, `fix/`, `chore/` prefixes.
- **Action**: Change PR title format to conventional: `feat(spec-{spec}): {slug}`. Keep the `_humanize_branch()` stripping logic.

#### `.claude/skills/ai-commit/SKILL.md`
- **Current state**: Step 7 (line 89): `spec-NNN: Task X.Y -- <description>` for spec commits, `type(scope): description` for non-spec commits. Already mentions conventional commits as an alternative.
- **Action**: Change spec format to `feat(spec-NNN): Task X.Y -- description`. Keep `type(scope): description` for non-spec. Make conventional commits the primary format.

#### `.claude/skills/ai-pr/SKILL.md`
- **Current state**: Line 184: Title format `type(scope): description` or `spec-NNN: Task X.Y -- description`. Already lists both.
- **Action**: Change to `type(scope-NNN): description` as the primary format. Remove `spec-NNN:` legacy.

#### `tests/unit/test_version_bump.py`
- **Current state**: `_write_project()` helper creates both `pyproject.toml` and `__version__.py`. Tests assert both files are updated by `bump_python_version()`. Test `test_bump_python_version_raises_when_version_file_missing` expects `FileNotFoundError`.
- **Action**: Update `_write_project()` to not create `__version__.py`. Update `test_bump_python_version_updates_pyproject_and_version_file` to only assert pyproject.toml change. Remove `test_bump_python_version_raises_when_version_file_missing` and `test_bump_python_version_raises_when_version_assignment_missing`. Add new tests for single-file bump.

#### `tests/unit/test_release_orchestrator.py`
- **Current state**: Multiple references to `__version__.py` in mock data: `_prepare_branch` mocks return `"pyproject.toml\nsrc/ai_engineering/__version__.py"` as output (line 464). `bump.files_modified` lists include `__version__.py` (lines 258, 532).
- **Action**: Update mock data to remove `__version__.py` references. Update `bump.files_modified` to only contain `pyproject.toml`.

#### `tests/unit/test_gates.py`
- **Current state**: `TestValidateCommitMessage` class (line 133) tests: valid message, empty, whitespace-only, long first line, exactly 72 chars, multiline. All use basic messages ("feat: add new feature", "a" * 73, etc.). No conventional commit format tests.
- **Action**: Add tests for conventional commit acceptance and legacy spec-NNN acceptance during transition.

#### `tests/integration/test_gates_integration.py`
- **Current state**: `TestCommitMsgValidation` class (line 100) tests: valid, empty, long, exactly 72, multiline. `TestCommitMsgGate` tests the gate hook with valid/invalid msg files.
- **Action**: Add integration tests for conventional commit format in gate context.

### Patterns to Follow

#### `importlib.metadata.version()` pattern
```python
# In __init__.py
try:
    from importlib.metadata import version
    __version__ = version("ai-engineering")
except Exception:
    __version__ = "0.0.0"  # fallback for editable/dev installs
```
This is the standard Python packaging pattern for single-source versioning. The version is defined in `pyproject.toml` and read at runtime via `importlib.metadata`. The fallback handles editable installs (`pip install -e .` / `uv pip install -e .`) where metadata may not be available until the package is built.

#### python-semantic-release config in pyproject.toml
```toml
[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
commit_parser = "angular"
tag_format = "v{version}"
major_on_zero = false
changelog_file = false  # manual CHANGELOG
branch = "main"

[tool.semantic_release.commit_parser_options]
allowed_tags = ["feat", "fix", "perf", "refactor", "chore", "docs", "ci", "test", "style", "build"]
```

#### Conventional commit format
```
type(scope): description

[optional body]

[optional footer(s)]
```
Types: `feat` (minor bump), `fix` (patch bump), `perf`, `refactor`, `chore`, `docs`, `ci`, `test`, `style`, `build` (no bump unless BREAKING CHANGE).
Scope is optional. `BREAKING CHANGE:` footer or `!` after type triggers major bump.
Spec integration: `feat(spec-097): description` preserves spec traceability.

### Dependencies Map

#### Files importing `__version__` (6 direct + 1 re-export)
| File | Import form | Lazy? |
|------|------------|-------|
| `__init__.py` | `from ai_engineering.__version__ import __version__` | No |
| `cli_ui.py` | `from ai_engineering.__version__ import __version__` | No |
| `cli_commands/core.py` | `from ai_engineering.__version__ import __version__` | No |
| `cli_factory.py` | `from ai_engineering.__version__ import __version__` | Yes (inside function) |
| `branch_protection.py` | `from ai_engineering.__version__ import __version__` | Yes (inside function) |
| `doctor/runtime/version.py` | `from ai_engineering import __version__` | No (already correct) |

#### Files referencing commit format (`spec-NNN:` pattern)
- **Canonical skills**: `.claude/skills/ai-commit/SKILL.md`, `.claude/skills/ai-pr/SKILL.md`
- **Canonical agents**: `.claude/agents/ai-plan.md`, `.claude/agents/review-context-explorer.md`
- **Autopilot handlers**: `.claude/skills/ai-autopilot/handlers/phase-implement.md`, `.claude/skills/ai-autopilot/handlers/phase-quality.md`
- **All IDE mirrors** (`.github/`, `.codex/`, `.gemini/`, and `templates/project/` variants) -- handled by `sync_command_mirrors.py`
- **Code**: `src/ai_engineering/vcs/pr_description.py` (`build_pr_title()`)

#### Files referencing `__version__.py` in tests
- `tests/unit/test_version_bump.py` (lines 30-31, 69-71, 101-102, 130)
- `tests/unit/test_release_orchestrator.py` (lines 258, 464, 532)

### Risks

1. **Import breakage at runtime**: If `importlib.metadata.version()` fails for editable installs, the fallback must be robust. Risk: CI runs in editable mode (`uv pip install -e .`) -- if metadata is not available, version checks fail. Mitigation: Use broad `except Exception` fallback to `"0.0.0"`, verify in editable install test.

2. **Commit format transition**: Existing branches with `spec-NNN:` commits are in-flight. During transition, `commit_msg.py` must accept both formats. Risk: if we only accept conventional commits, existing branches cannot commit. Mitigation: dual-format acceptance in Phase 3, legacy removal deferred to Phase 6 (sub-006).

3. **Mirror sync completeness**: Changing `.claude/skills/ai-commit/SKILL.md` requires propagation to 4 IDE surfaces + 4 template surfaces (8 mirrors per skill, 2 skills = 16 mirror operations). Risk: missed mirrors cause inconsistent commit format instructions across IDEs. Mitigation: run `sync_command_mirrors.py --check` after sync.

4. **Test failures from `__version__.py` removal**: 7+ test assertions reference `__version__.py` paths. Risk: tests fail on import or assertion if not all references are updated. Mitigation: systematic search-and-update of all test files.

5. **Orchestrator `git add` breakage**: `orchestrator.py` line 374 uses `bump.files_modified[1]` (index-based access to `__version__.py` path). After migration, `files_modified` has only 1 element. Index `[1]` will raise `IndexError`. Mitigation: change to iterate over all `files_modified` items.

6. **python-semantic-release version**: Must pin to a stable version. The library has had breaking changes between major versions (v7 vs v8 vs v9). Mitigation: pin to `>=9.0,<10` and verify config format matches.

7. **ci-build.yml dependency**: Sub-003 adds semantic-release integration to `ci-build.yml` which is created by sub-002. If sub-002 is not complete, sub-003 cannot write to that file. Mitigation: sub-003 depends_on sub-002 in the manifest. The plan accounts for this sequencing.
