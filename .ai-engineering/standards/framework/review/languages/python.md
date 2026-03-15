# Python Review Guidelines

## Update Metadata
- Rationale: Python-specific patterns, anti-patterns, and idioms for code review.

## Idiomatic Patterns
- Use `pathlib.Path` over `os.path` for path manipulation.
- Prefer `dict.get()` for optional keys, direct access `dict["key"]` for required keys (fail-fast).
- Use dataclasses or Pydantic models over raw dicts for structured data.
- Type hints on all public APIs (functions, methods, class attributes).
- Context managers (`with`) for all resource management.

## Performance Anti-Patterns
- **N+1 queries**: Watch for database calls inside loops. Use `select_related()`, `prefetch_related()`, or batch queries.
- **Fallback N+1**: Cache miss in a loop that triggers individual fetches — batch the cache lookup.
- **String concatenation in loops**: Use `"".join(parts)` or f-strings.
- **Unbounded list growth**: Check for `.append()` in loops without size limits.

## Security Patterns
- Never use `eval()`, `exec()`, or `pickle.loads()` on untrusted input.
- Parameterized queries for all database access — no string formatting.
- Validate all external input at system boundaries.
- Use `secrets` module for tokens, not `random`.

## Testing Patterns
- AAA pattern: Arrange, Act, Assert.
- Use `pytest.fixture` for shared setup, not class inheritance.
- `@pytest.mark.parametrize` for data-driven tests.
- Mock external services, not internal functions.

## Self-Challenge Questions
- Is this truly a Python-specific issue, or a general code quality issue?
- Does the standard library already provide what this code reimplements?
- Is the type hint suggestion actually improving safety or just adding noise?

## References
- Enforcement: `standards/framework/stacks/python.md`
