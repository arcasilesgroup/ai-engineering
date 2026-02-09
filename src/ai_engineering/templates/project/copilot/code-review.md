# Code Review Instructions

## Canonical Source

Use `.ai-engineering/` as the single source of truth for project governance and context.

## References

- `.ai-engineering/standards/framework/core.md`
- `.ai-engineering/standards/framework/quality/core.md`
- `.ai-engineering/standards/framework/quality/python.md`

## Review Checklist

### Security Non-Negotiables

- No secrets, tokens, or credentials in code or configuration.
- Dependencies must not introduce known vulnerabilities (verify with `pip-audit`).
- Remote skill sources are content-only; no unsafe remote execution.

### Quality Gates

- Lint and format: `ruff check` and `ruff format --check` must pass.
- Type checking: `ty check` must pass.
- Tests: `uv run pytest` must pass.
- Security scans: `gitleaks` and `semgrep` must pass.

### Ownership Safety

- Changes to team-managed files (`.ai-engineering/standards/team/**`) require team approval.
- Changes to project-managed files (`.ai-engineering/context/**`) require project-level review.
- Framework-managed files should only change through governed update flows.

### General

- Prefer small, focused changes over large sweeping refactors.
- Ensure public APIs have type annotations and docstrings.
- Verify backward compatibility for any interface changes.
