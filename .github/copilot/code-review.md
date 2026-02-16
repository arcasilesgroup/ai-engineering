# Code Review Instructions

## Canonical Source

Use `.ai-engineering/` as the single source of truth for project governance and context.

## References

- `.ai-engineering/standards/framework/core.md` — governance, ownership, lifecycle.
- `.ai-engineering/standards/framework/quality/core.md` — quality contract, gate structure.
- `.ai-engineering/standards/framework/quality/python.md` — Python-specific checks, complexity thresholds.

## Skills and Agents

- Apply `.ai-engineering/agents/principal-engineer.md` persona for thorough reviews.
- Use `.ai-engineering/skills/dev/code-review.md` for structured review procedure.
- Reference `.ai-engineering/skills/review/security.md` for security-focused reviews.

## Review Checklist

### Security Non-Negotiables

- No secrets, tokens, or credentials in code or configuration.
- Dependencies must not introduce known vulnerabilities (verify with `pip-audit`).
- Remote skill sources are content-only; no unsafe remote execution.
- Security findings cannot be dismissed without `state/decision-store.json` risk acceptance.

### Quality Gates

- Lint and format: `ruff check` and `ruff format --check` must pass.
- Type checking: `ty check` must pass.
- Tests: `uv run pytest` must pass with ≥ 80% coverage.
- Security scans: `gitleaks` and `semgrep` must pass.

### Complexity

- Cyclomatic complexity ≤ 10 per function.
- Cognitive complexity ≤ 15 per function.
- Functions < 50 lines.
- Duplication ≤ 3%.

### Ownership Safety

- Changes to team-managed files (`.ai-engineering/standards/team/**`) require team approval.
- Changes to project-managed files (`.ai-engineering/context/**`) require project-level review.
- Framework-managed files should only change through governed update flows.

### General

- Prefer small, focused changes over large sweeping refactors.
- Ensure public APIs have type annotations and docstrings.
- Verify backward compatibility for any interface changes.
- Architecture layers must not be violated (CLI → service → state → I/O).
