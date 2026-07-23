# ai-engineering

> Identity, gates, and commands. Everything else is on-demand.

## Identity

This repo uses [ai-engineering](https://github.com/arcasilesgroup/ai-engineering).
Config: `.ai-engineering/manifest.yml`. Principles: `.ai-engineering/reference/principles.md`.

## Gates (irreversible-action)

1. **Secrets:** `gitleaks protect --staged` on commit. BLOCK at CRITICAL/HIGH/MEDIUM.
2. **No suppression:** No `# noqa`, `# nosec`, `// @ts-ignore`. Refactor or risk-accept.
3. **Conventional Commits:** `<type>(<scope>): <subject>`. Never `--no-verify`.
4. **SSOT:** One writable store per datum. Derived caches labelled with rebuild command.

## Chain

```
/ai-spec-draft → /ai-brainstorm → /ai-plan → /ai-build → /ai-pr
```

- `/ai-brainstorm` → approved spec at `.ai-engineering/specs/spec.md`
- `/ai-plan` → plan at `.ai-engineering/specs/plan.md`
- `/ai-build` → code (or `/ai-autopilot` for ≥3 concerns)
- `/ai-pr` → PR with quality gate

## Quick Reference

| Need | Command |
|------|---------|
| New feature | `/ai-brainstorm` |
| Execute plan | `/ai-build` |
| Run tests | `/ai-test` |
| Debug issue | `/ai-debug` |
| Open PR | `/ai-pr` |
| Commit WIP | `/ai-commit` |

## Surfaces

Skills: `.claude/skills/ai-<name>/SKILL.md`
Agents: `.claude/agents/ai-<name>.md`
Hooks: `.ai-engineering/scripts/hooks/`

<!-- ide-extras:start -->
<!-- ide-extras:end -->
