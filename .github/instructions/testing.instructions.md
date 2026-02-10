---
applyTo: "**/tests/**"
---

# Testing Instructions

## Governance References

- `.ai-engineering/standards/framework/quality/core.md` — coverage targets, quality gates.
- `.ai-engineering/standards/framework/quality/python.md` — Python-specific test requirements.
- `.ai-engineering/standards/framework/stacks/python.md` — testing patterns section.

## Framework

- **Runner**: `pytest` via `uv run pytest`
- **Coverage**: `pytest-cov` — target ≥ 80% (≥ 90% governance-critical modules)
- **Assertions**: use `pytest` native assertions, not `unittest.TestCase`

## Directory Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures
├── unit/                # Fast, isolated, no I/O
│   ├── __init__.py
│   └── test_<module>.py
├── integration/         # Real git, real filesystem
│   ├── __init__.py
│   └── test_<scenario>.py
└── e2e/                 # Full install, CLI, workflows
    ├── __init__.py
    └── test_<flow>.py
```

## Naming Conventions

- Test files: `test_<module>.py`
- Test functions: `test_<behavior_under_test>` — describe what is being tested, not the method name.
- Fixtures: descriptive nouns (`tmp_project`, `git_repo`, `installed_framework`).

## Test Patterns

### Arrange-Act-Assert (AAA)

```python
def test_install_creates_manifest(tmp_path: Path) -> None:
    # Arrange
    project = tmp_path / "my-project"
    project.mkdir()

    # Act
    result = install(project)

    # Assert
    assert (project / ".ai-engineering" / "manifest.yml").exists()
    assert result.success is True
```

### Fixtures over Setup

- Use `tmp_path` for filesystem tests — never hardcode paths.
- Use `conftest.py` fixtures for shared setup.
- Prefer factory fixtures for configurable test data.

### What to Test

- **Happy path**: normal expected behavior.
- **Edge cases**: empty input, boundary values, missing files.
- **Error paths**: invalid input, permission errors, missing tools.
- **Regression**: every bug fix gets a test that fails without the fix.

### What NOT to Test

- Third-party library internals.
- Private functions directly (test through public interfaces).
- Implementation details that may change.

## Quality Checks on Tests

- Tests must pass `ruff check` and `ruff format --check`.
- Tests must not import private APIs from third-party libraries.
- Tests must be deterministic — no random, no time-dependent assertions.
- Tests must be independent — no test depends on another test's side effects.

## Running

```bash
uv run pytest                          # All tests
uv run pytest tests/unit/              # Unit only
uv run pytest tests/integration/       # Integration only
uv run pytest --cov --cov-report=term  # With coverage
uv run pytest -x                       # Stop on first failure
uv run pytest -k "test_install"        # Filter by name
```

## Skills Reference

- `.ai-engineering/skills/swe/test-strategy.md` — test design procedure.
- `.ai-engineering/skills/swe/debug.md` — diagnosing test failures.
