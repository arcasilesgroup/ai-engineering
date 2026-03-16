# Commit Message Instructions

## References

- `.github/prompts/ai-commit.prompt.md` — full commit workflow procedure.
- `.github/prompts/ai-pr.prompt.md` — PR creation procedure.

## Format

Use conventional commit format:

```
<type>(<scope>): <short summary>
```

When working on a spec, prefix with spec identifier:

```
spec-001: Task X.Y — <description>
```

## Types

- `feat`: new feature or capability.
- `fix`: bug fix.
- `docs`: documentation-only change.
- `refactor`: code change that neither fixes a bug nor adds a feature.
- `test`: adding or updating tests.
- `chore`: maintenance, tooling, or dependency updates.
- `ci`: CI/CD configuration changes.

## Rules

- Keep the subject line under 72 characters.
- Use imperative mood ("add", "fix", "update", not "added", "fixed", "updated").
- Scope should reflect the affected module (e.g., `installer`, `state`, `skills`, `cli`).
- Do not include ticket numbers unless explicitly requested.
- Body is optional; use it for context on *why*, not *what*.
- One task = one atomic commit (in spec-driven work).
