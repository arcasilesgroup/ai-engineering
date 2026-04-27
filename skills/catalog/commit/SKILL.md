---
name: commit
description: Use when committing, saving, or pushing code to git. Trigger for "commit my changes", "save my work", "push this to remote", "stage these files", "I'm done with this task", "ship it". Governed pipeline with ruff + gitleaks + conventional commits.
effort: medium
tier: core
capabilities: [tool_use]
---

# /ai-commit

Governed commit pipeline. Use `/ai-pr` instead when a pull request is
the goal.

## Pipeline (Hot Path < 1s)

1. **Auto-branch from protected branches** (main, master). Never commit
   directly to protected.
2. **Selective staging** — only the files relevant to the message.
3. **Format staged** — `ruff format --staged` + `bun biome format` for
   staged files.
4. **Lint staged** — `ruff check --fix --staged` + `bun biome check`.
5. **Secret scan** — `gitleaks protect --staged --no-banner`.
6. **Documentation gate** — if a public surface changed, prompt for
   `CHANGELOG.md` update.
7. **Conventional commit message** — `<type>(<scope>): <subject>` body
   focuses on WHY.
8. **Push** — unless `--only` is passed (just commit).

## Hot vs cold path

- Hot path (commit time, < 1s):
  staged-only format/lint/gitleaks/injection-guard.
- Cold path (post-commit async):
  full ruff/pytest/coverage/pip-audit/semgrep, reports to
  `framework-events.ndjson`. Failures create issues, not blocks.

## Hard rules

- NEVER `--no-verify`.
- NEVER commit secrets — gitleaks blocks them; do NOT add them to
  allowlists without `governance` skill approval.
- Conventional commits enforced.
