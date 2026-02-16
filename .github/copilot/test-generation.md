# Test Generation Instructions

## Canonical Source

Use `.ai-engineering/` as the single source of truth for project governance and context.

## References

- `.ai-engineering/standards/framework/quality/core.md` — coverage targets, quality gates.
- `.ai-engineering/standards/framework/quality/python.md` — Python-specific test requirements.
- `.ai-engineering/standards/framework/stacks/python.md` — testing patterns section.

## Skills

- Use `.ai-engineering/skills/dev/test-strategy.md` for test design procedure.
- Reference `.ai-engineering/skills/dev/debug.md` for diagnosing test failures.

## Conventions

- Use `pytest` as the test framework.
- Place unit tests under `tests/unit/` and integration tests under `tests/integration/`.
- Name test files `test_<module>.py` and test functions `test_<behavior>`.
- Use fixtures from `conftest.py`; prefer `tmp_path` or project-specific fixtures over manual setup.
- Follow Arrange-Act-Assert (AAA) pattern in every test.

## Coverage

- Every public function and class must have at least one test.
- Cover both happy-path and error/edge-case scenarios.
- Assert specific values rather than truthiness when possible.
- Target ≥ 80% coverage (≥ 90% for governance-critical modules).

## Test Types

- **Unit tests**: fast, isolated, no I/O, no network. Mock external dependencies.
- **Integration tests**: real filesystem, real git. Use `tmp_path` for isolation.
- **E2E tests**: full install, CLI commands, workflow execution.

## Quality Checks

- Generated tests must pass `ruff check` and `ty check`.
- Tests must be runnable with `uv run pytest`.
- Do not import or use internal/private APIs from third-party libraries.
- Tests must be deterministic — no random, no time-dependent assertions.
- Tests must be independent — no test depends on another test's side effects.
