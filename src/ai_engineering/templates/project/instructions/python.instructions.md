---
applyTo: "**/*.py"
---

# Python Instructions

## Governance References

Read before generating or modifying Python code:

- `.ai-engineering/standards/framework/stacks/python.md` — stack contract, code patterns, testing patterns.

## Runtime and Tooling

- **Runtime**: Python 3.11+
- **Package manager**: `uv` (not pip, not poetry, not pipenv)
- **Lint/format**: `ruff` (line-length 100)
- **Type check**: `ty`
- **Test**: `pytest` via `uv run pytest`
- **Security**: `gitleaks`, `semgrep`, `pip-audit`

## Build / Run / Test

```bash
uv sync                           # Install dependencies
uv run pytest                     # Run tests
uv run pytest --cov               # Run tests with coverage
uv run ruff check src/ tests/     # Lint
uv run ruff format --check src/ tests/  # Format check
uv run ty check src/              # Type check
uv run pip-audit                  # Dependency vulnerabilities
```

## Code Patterns

- Use `from __future__ import annotations` in every module.
- All public functions and methods must have type annotations.
- Use `pathlib.Path` for all file operations — never `os.path`.
- File creation must use create-only semantics — never overwrite team/project content.
- Cross-OS: use `Path` operations, `shutil` for cross-platform, `subprocess` for tooling.
- Prefer dependency injection over global state.
- Architecture layers: CLI → service → state → I/O. No layer skipping.

## Complexity Limits

- Cyclomatic complexity ≤ 10 per function.
- Cognitive complexity ≤ 15 per function.
- Functions < 50 lines.
- If exceeded, extract helper functions.

## Style Rules

- Imports: stdlib → third-party → local, one import per line.
- Docstrings: Google-style for public APIs.
- Naming: `snake_case` for functions/variables, `PascalCase` for classes.
- Constants: `UPPER_SNAKE_CASE`.

## Error Handling

- Raise specific exceptions, not bare `Exception`.
- Use `typer.Exit(code=1)` for CLI error exits.
