# Python — TDD Harness

`ai-build` runs RED → GREEN → REFACTOR through pytest. Tests are
deterministic, parallel-safe, and never reach the network.

## Runner

- **Default**: `pytest`. Do not introduce `unittest`-style test
  classes for new tests; pytest collects free functions and
  parametrises them more cleanly.
- **Plugins permitted by default**: `pytest-cov`, `pytest-xdist`
  (parallel), `pytest-asyncio` (async tests), `pytest-mock` (cleaner
  monkeypatch).
- Forbid: `pytest-randomly` unless determinism is explicitly handled.

## Layout

```
tests/
  unit/
    test_<unit>.py
  integration/
    test_<feature>.py
  conftest.py
```

- Co-locate fixtures in `tests/conftest.py` (root) or per-directory
  `conftest.py` for scoped fixtures.
- Mirror `src/` layout in `tests/unit/` so the test file path tells
  you what's under test.

## Naming

- File: `test_<unit>.py`.
- Function: `test_<behaviour>_<condition>` — assertion-first phrasing,
  e.g. `test_returns_none_when_input_empty`.
- Fixtures: noun, lowercase: `client`, `temp_workspace`.

## RED → GREEN → REFACTOR

1. **RED** — write the failing test. Run `pytest tests/unit/test_x.py::test_y -x`.
   Confirm the failure message matches the assertion.
2. **GREEN** — minimum code to pass. Do not modify the test.
3. **REFACTOR** — restructure with the suite green.

## Flags

- `-x` stop on first failure during local TDD.
- `-q` quiet output; `-v` verbose for CI.
- `-k <expr>` filter by test name.
- `--lf` rerun last failures only.
- `-n auto` parallel via `pytest-xdist` when tests are isolated.

## Fixtures

- Prefer fixtures over `setUp`/`tearDown`.
- Scope intentionally: `function` (default), `module`, `session`.
- Use `yield` for teardown:
  ```python
  @pytest.fixture
  def client():
      c = build_client()
      yield c
      c.close()
  ```
- `tmp_path` for filesystem; `monkeypatch` for env vars; `caplog` for
  log assertions.

## Parametrise

```python
@pytest.mark.parametrize(
    "value,expected",
    [(1, 2), (2, 4), (0, 0)],
)
def test_double(value, expected):
    assert double(value) == expected
```

## Async

```python
import pytest

@pytest.mark.asyncio
async def test_handler_returns_user():
    result = await handler.run()
    assert result.id == "u-1"
```

## Mocks

- `pytest-mock`'s `mocker` fixture over `unittest.mock` directly.
- Patch where the symbol is *used*, not where it's *defined*.
- `mocker.patch.object` for class attributes.

## Coverage

- `pytest --cov=<package> --cov-report=term-missing`.
- Floor: 85 % statements on touched files.
