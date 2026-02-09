# Code Generation Instructions

## Canonical Source

Use `.ai-engineering/` as the single source of truth for project governance and context.

## References

Before generating code, consult:

- `.ai-engineering/standards/framework/core.md`
- `.ai-engineering/standards/framework/stacks/python.md`
- `.ai-engineering/standards/team/core.md`

## Ownership Safety

- Framework-managed paths (`.ai-engineering/standards/framework/**`) may be overwritten by the framework.
- Team-managed paths (`.ai-engineering/standards/team/**`) must never be overwritten by automated flows.
- Project-managed paths (`.ai-engineering/context/**`) must never be overwritten by automated flows.

## Tooling Baseline

- Runtime and packaging: `uv`
- Lint and format: `ruff`
- Type checking: `ty`
- Dependency vulnerability check: `pip-audit`

## Style

- Follow `ruff` rules configured in `pyproject.toml`.
- Use type annotations on all public functions and methods.
- Prefer `from __future__ import annotations` for modern annotation syntax.
- Keep functions small and single-purpose.
