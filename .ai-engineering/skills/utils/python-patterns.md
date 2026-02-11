# Python Mastery

## Purpose

Comprehensive Python engineering skill consolidating 12 domains into a single reference for AI-assisted code generation, review, and optimization. Provides patterns, anti-patterns, and best practices for production Python code.

## Trigger

- Command: agent invokes python-patterns skill or references it during code generation/review.
- Context: writing production Python code, reviewing for quality, optimizing performance, applying design patterns.

## Domains

### 1) Performance Optimization

**Patterns**:
- Profile before optimizing: `cProfile`, `py-spy`, `tracemalloc`, `memray`.
- Use generators for large sequences: `yield` over `list` for memory efficiency.
- Cache expensive computations: `functools.lru_cache`, `functools.cache`.
- Batch I/O operations: reduce filesystem and network round trips.
- Use appropriate data structures: `dict`/`set` for O(1) lookups, `deque` for queues.
- Prefer comprehensions over manual loops for simple transformations.
- Use `multiprocessing` for CPU-bound work, `asyncio` for I/O-bound work.

**Anti-patterns**:
- Premature optimization without measurement.
- String concatenation in loops (use `str.join`).
- Loading entire files into memory when streaming suffices.
- Blocking I/O in async contexts.

### 2) Testing Patterns

**Patterns**:
- AAA: Arrange → Act → Assert in every test.
- Fixtures: shared in `conftest.py`, scoped appropriately (`function`, `module`, `session`).
- Parameterized tests: `@pytest.mark.parametrize` for data-driven testing.
- Mocking: `unittest.mock.patch` for external dependencies, never mock the unit under test.
- Property-based testing: `hypothesis` for discovering edge cases.
- Markers: `@pytest.mark.slow`, `@pytest.mark.integration` for test categorization.
- Coverage: `pytest-cov` with `--cov-fail-under=80`.

**Anti-patterns**:
- Tests that depend on execution order.
- `time.sleep` for synchronization.
- Testing implementation details instead of behavior.
- Fixtures chained more than 3 levels deep.

### 3) Packaging

**Patterns**:
- `src/` layout with `pyproject.toml` as single config file.
- Entry points via `[project.scripts]` in `pyproject.toml`.
- Build with `uv build` → `py3-none-any` wheel.
- Pin dependencies in lockfile, use compatible ranges in `pyproject.toml`.
- Include `py.typed` marker for PEP 561 type stub support.
- Use `__version__.py` for version string, reference from `pyproject.toml` via `dynamic`.

**Anti-patterns**:
- `setup.py` + `setup.cfg` duplication.
- `pip install -e .` instead of `uv sync`.
- Hard-coded version strings in multiple places.

### 4) Design Patterns

**Patterns**:
- **KISS**: simplest solution that works. No speculative generality.
- **SRP**: one reason to change per module/class/function.
- **Composition over inheritance**: use protocols and dependency injection.
- **Rule of three**: don't abstract until the pattern appears three times.
- **Dependency injection**: services receive deps through constructors, not globals.
- **Layered architecture**: CLI → service → state → I/O.
- **Strategy pattern**: via `Protocol` classes for swappable implementations.
- **Factory pattern**: for complex object creation with validation.

**Anti-patterns**:
- God classes that do everything.
- Deep inheritance hierarchies (prefer composition).
- Singleton abuse (use dependency injection).
- Premature abstraction.

### 5) Code Style

**Patterns**:
- Ruff for linting and formatting (line-length 100).
- PEP 8 naming: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants.
- Google-style docstrings on all public functions and classes.
- Import organization: stdlib → third-party → local, one import per line.
- Explicit `__all__` in `__init__.py` for public API.

**Anti-patterns**:
- Mixed naming conventions.
- Missing docstrings on public APIs.
- Star imports (`from module import *`).
- Wildcard re-exports without `__all__`.

### 6) Project Structure

**Patterns**:
- One concept per file: `models.py`, `service.py`, `io.py`.
- Flat hierarchies: avoid nesting more than 3 levels.
- Explicit `__all__` for controlled public API surface.
- Separate CLI layer from business logic.
- Test files mirror source layout: `test_<module>.py` → `<module>.py`.

**Anti-patterns**:
- Files with 500+ lines handling multiple concerns.
- Circular imports between modules.
- Business logic in CLI command handlers.

### 7) Error Handling

**Patterns**:
- **Fail fast**: validate inputs at function entry with clear error messages.
- **Early validation**: Pydantic models for input validation.
- **Custom exceptions**: domain-specific exception hierarchy rooted in a base class.
- **Exception chaining**: `raise NewError("msg") from original_error`.
- **Batch partial failures**: collect errors and report at end, don't stop on first issue.
- **Context managers**: `contextlib.contextmanager` for resource cleanup.

**Anti-patterns**:
- Bare `except:` without specific exception type.
- Silent `except: pass` that swallows errors.
- Exception handling for control flow.
- Returning `None` to signal errors instead of raising.

### 8) Anti-Patterns Checklist

Before committing, verify:
- [ ] No bare `except:`.
- [ ] No scattered retry logic (centralize with decorator or utility).
- [ ] No hard-coded config values (use environment variables or config files).
- [ ] No exposed ORM/data models as API contracts (use separate DTOs).
- [ ] No mixed I/O + business logic in same function (separate concerns).
- [ ] No blocking calls in async functions.
- [ ] No mutable default arguments (`def f(items=[])` → `def f(items=None)`).
- [ ] No global mutable state.
- [ ] No string formatting for log messages (use lazy formatting: `log.info("msg %s", val)`).

### 9) Type Safety

**Patterns**:
- `from __future__ import annotations` at module top.
- Annotate all public APIs: function signatures, class attributes, return types.
- Modern union syntax: `str | None` over `Optional[str]`.
- Generics: `list[str]`, `dict[str, int]` (lowercase).
- Protocols: `typing.Protocol` for structural subtyping (duck typing with type safety).
- TypeVar bounds: `T = TypeVar("T", bound=BaseModel)` for generic constraints.
- `typing.TypeAlias` for complex type definitions.
- `ty check src/` as mandatory gate.

**Anti-patterns**:
- `Any` as escape hatch (use `object` or proper generics).
- `# type: ignore` without specific error code.
- Missing return type annotations on public functions.

### 10) Observability

**Patterns**:
- Structured logging: `structlog` for machine-parseable log output.
- Correlation IDs: thread-local or context-var for request tracing.
- Semantic log levels: DEBUG (developer), INFO (operator), WARNING (attention), ERROR (failure), CRITICAL (system down).
- Four golden signals: latency, traffic, errors, saturation.
- Metrics naming: `<domain>_<operation>_<unit>` (e.g., `install_duration_seconds`).

**Anti-patterns**:
- `print()` statements for logging.
- Logging secrets or PII.
- Missing error context in log messages.
- Log level misuse (ERROR for non-errors).

### 11) Resilience

**Patterns**:
- Retry with `tenacity`: exponential backoff with jitter for transient failures.
- Timeouts: `signal.alarm` or `asyncio.wait_for` for bounded execution.
- Fail-safe defaults: graceful degradation when optional services are unavailable.
- Circuit breaker pattern for repeated external failures.
- Idempotent operations: safe to retry without side effects.

**Anti-patterns**:
- Infinite retry loops.
- Retry on non-transient errors (validation errors, auth failures).
- Missing timeout on network calls.
- Hard failure when optional features are unavailable.

### 12) Python-Specific Idioms

**Patterns**:
- Context managers for resource lifecycle (`with` statement).
- `pathlib.Path` for all filesystem operations (cross-OS).
- `dataclasses` for simple data containers, `Pydantic` for validated models.
- F-strings for string formatting (Python 3.6+).
- Walrus operator (`:=`) for assignment in conditions (use sparingly for readability).
- `enum.Enum` for fixed option sets.
- `collections.defaultdict` and `collections.Counter` for counting patterns.

**Anti-patterns**:
- `os.path` instead of `pathlib`.
- `%` or `.format()` string formatting (use f-strings).
- Manual resource cleanup instead of context managers.

## Output Contract

- Code following the patterns above.
- Anti-pattern checklist verified.
- Type annotations on all public APIs.
- Docstrings on all public functions.
- Tests using AAA pattern with appropriate fixtures.

## Governance Notes

- This skill is the definitive Python reference for this project. When patterns conflict, this skill takes precedence over general Python advice.
- All domains apply to production code. Test code follows domain 2 only.
- `standards/framework/stacks/python.md` contains the enforceable subset.
- This skill is advisory/aspirational beyond what standards mandate.

## References

- `standards/framework/stacks/python.md` — enforceable Python baseline.
- `standards/framework/quality/python.md` — quality thresholds.
- `skills/dev/test-strategy.md` — testing details.
- `skills/review/performance.md` — performance deep-dive.
- `skills/review/security.md` — security-specific patterns.
- `agents/architect.md` — agent that uses design patterns domain.
- `agents/code-simplifier.md` — agent that uses Pythonic patterns.
- `agents/codebase-mapper.md` — agent that uses Python module system domain.
- `agents/principal-engineer.md` — agent that uses Python patterns for review.
