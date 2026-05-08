<!-- source: contexts/languages/python.md @ affdef6d3235a65039813845a467340fa4f70803 -->

# Python — Build Conventions

Authoritative reference for the `ai-build` agent when generating
Python code. Distilled from `contexts/languages/python.md` plus
`contexts/frameworks/{django,api-design,backend-patterns}.md`.

## Toolchain

- **Interpreter**: CPython 3.12+ unless the host pins lower. Annotate
  the floor in `pyproject.toml` `requires-python`.
- **Package manager**: `uv` for new repos; `pip` + `pip-tools` is
  acceptable in legacy. Never mix `poetry` and `uv` lockfiles.
- **Linter / formatter**: `ruff check` + `ruff format`. Ban `flake8`,
  `black`, `isort` — `ruff` replaces all three with one binary.
- **Type checker**: `mypy --strict` for libraries; `pyright` is
  acceptable for apps when the team prefers it.

## Layout

```
src/<package>/
  __init__.py
  module.py
tests/
  unit/
  integration/
pyproject.toml
```

- `src/` layout mandatory — keeps `import <package>` from picking up
  the working directory by accident.
- One package per repo; sub-packages by domain, not by layer.

## Naming (PEP 8)

| Element | Convention | Example |
|---|---|---|
| Modules / packages | lower_snake | `market_data` |
| Functions / variables | lower_snake | `fetch_market_data` |
| Classes / exceptions | UpperCamel | `MarketData`, `LookupError` |
| Constants | UPPER_SNAKE | `MAX_RETRIES` |
| Internals | leading underscore | `_helper` |

## Type hints

- Every public function signature is annotated.
- Prefer `from __future__ import annotations` for modules that import
  type-only symbols (Python 3.12 still needs it for `TYPE_CHECKING`).
- `Any` is forbidden in new code; reach for `object`, `TypedDict`, or
  `Protocol`.
- `Optional[X]` over `X | None` is fine, but be consistent within a
  module.
- Generics: parameterise (`list[int]`, `Mapping[str, User]`), don't
  use bare `list` / `dict`.

## Errors

- Raise specific exception subclasses; never bare `Exception`.
- `try`/`except` blocks catch the narrowest type that matters.
- Re-raise with `raise ... from err` when wrapping.
- Never silently `except: pass`.

## Async

- `asyncio` is the default. Never call `time.sleep()` from an async
  function — use `await asyncio.sleep()`.
- Don't block the loop with CPU-bound work; offload to
  `loop.run_in_executor` or a process pool.
- Prefer `asyncio.TaskGroup` (3.11+) over manual `gather` / cancel
  cleanup.

## Paths & I/O

- `pathlib.Path` over `os.path` strings. Open with `Path.open()`.
- Always specify text/binary mode and encoding (`encoding="utf-8"`).
- Use `with` for every file / lock / connection.

## Time

- `time.monotonic()` for durations; `time.time()` is wall-clock and
  can jump.
- Timezone-aware `datetime` (`datetime.now(UTC)`); naive datetimes are
  bugs in disguise.

## Quality gate (pre-commit)

1. `ruff check`
2. `ruff format --check`
3. `mypy` (or `pyright`) on the package
4. `pytest -x` — see `tdd_harness.md`
