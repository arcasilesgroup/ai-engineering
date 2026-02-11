# Code Generation Instructions

## Canonical Source

Use `.ai-engineering/` as the single source of truth for project governance and context.

## References

Before generating code, consult:

- `.ai-engineering/standards/framework/core.md` — governance structure, ownership, lifecycle.
- `.ai-engineering/standards/framework/stacks/python.md` — stack contract, code patterns, testing patterns.
- `.ai-engineering/standards/team/core.md` — team-specific standards.
- `.ai-engineering/standards/framework/quality/python.md` — complexity thresholds.

## Skills and Agents

- Use `.ai-engineering/skills/utils/python-patterns.md` for comprehensive Python patterns.
- Apply `.ai-engineering/agents/code-simplifier.md` persona for complexity reduction.
- Follow `.ai-engineering/skills/dev/refactor.md` when restructuring code.

## Ownership Safety

- Framework-managed paths (`.ai-engineering/standards/framework/**`) may be overwritten by the framework.
- Team-managed paths (`.ai-engineering/standards/team/**`) must never be overwritten by automated flows.
- Project-managed paths (`.ai-engineering/context/**`) must never be overwritten by automated flows.
- File creation uses create-only semantics — never overwrite existing team/project content.

## Tooling Baseline

- Runtime and packaging: `uv`
- Lint and format: `ruff` (line-length 100)
- Type checking: `ty`
- Dependency vulnerability check: `pip-audit`

## Code Patterns

- Use `from __future__ import annotations` in every module.
- All public functions and methods must have type annotations.
- Use Pydantic `BaseModel` for data structures (not dataclasses, not TypedDict).
- Use Typer for CLI commands with `Annotated[type, typer.Option(...)]`.
- Use `pathlib.Path` for all file operations — never `os.path`.
- Architecture layers: CLI → service → state → I/O. No layer skipping.
- Prefer dependency injection over global state.

## Complexity Limits

- Cyclomatic complexity ≤ 10 per function.
- Cognitive complexity ≤ 15 per function.
- Functions < 50 lines.

## Style

- Follow `ruff` rules configured in `pyproject.toml`.
- Use type annotations on all public functions and methods.
- Keep functions small and single-purpose.
- Google-style docstrings for public APIs.
