# Test Generation Instructions

## Canonical Source

Use `.ai-engineering/` as the single source of truth for project governance and context.

## References

- `.ai-engineering/standards/framework/quality/core.md`
- `.ai-engineering/standards/framework/quality/python.md`
- `.ai-engineering/standards/framework/stacks/python.md`

## Conventions

- Use `pytest` as the test framework.
- Place unit tests under `tests/unit/` and integration tests under `tests/integration/`.
- Name test files `test_<module>.py` and test functions `test_<behavior>`.
- Use fixtures from `conftest.py`; prefer `tmp_path` or project-specific fixtures over manual setup.

## Coverage

- Every public function and class must have at least one test.
- Cover both happy-path and error/edge-case scenarios.
- Assert specific values rather than truthiness when possible.

## Quality Checks

- Generated tests must pass `ruff check` and `ty check`.
- Tests must be runnable with `uv run pytest`.
- Do not import or use internal/private APIs from third-party libraries.
