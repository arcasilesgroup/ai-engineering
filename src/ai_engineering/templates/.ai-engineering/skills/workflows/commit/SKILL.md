---
name: commit
description: "Execute governed commit workflow: stage, lint, secret-detect, commit, and push current branch."
version: 1.0.0
category: workflows
tags: [git, commit, push, hooks]
metadata:
  ai-engineering:
    requires:
      bins: [gitleaks, ruff]
    scope: read-write
    token_estimate: 800
---

# Commit Workflow

## Purpose

Execute the `/commit` governed workflow: stage all changes, run mandatory pre-commit checks, commit with a well-formed message, and push to the current branch. The `--only` variant stages and commits without pushing.

## Trigger

- Command: `/commit` or `/commit --only`
- Context: user requests committing current changes with governance enforcement.

## Procedure

### `/commit` (default: stage + commit + push)

1. **Stage changes** — `git add -A` (or selective staging if user specifies files).
2. **Run formatter** — `ruff format .` to auto-fix formatting.
3. **Run linter** — `ruff check . --fix` to auto-fix safe lint issues. If unfixable issues remain, report and stop.
4. **Run secret detection** — `gitleaks protect --staged --no-banner`. If secrets found, report and stop.
5. **Commit** — `git commit -m "<message>"` with a well-formed commit message following project conventions.
   - If active spec exists, use format: `spec-NNN: Task X.Y — <description>`.
   - Otherwise, use conventional commit format: `type(scope): description`.
6. **Push** — `git push origin <current-branch>`.
   - If current branch is `main` or `master`, **block** and report protected branch violation.

### `/commit --only` (stage + commit, no push)

Follow steps 1–5 above. Skip step 6.

## Output Contract

- Terminal output showing each step's result (pass/fail).
- On success: commit hash and branch name displayed.
- On failure: specific check that failed with remediation guidance.

## Governance Notes

- Protected branch push is always blocked. No exceptions.
- Secret detection (`gitleaks`) failure is a hard stop. No bypass.
- Formatter and linter run with auto-fix before checking; only unfixable issues block.
- If `ruff` or `gitleaks` is not installed, attempt auto-remediation: `uv tool install ruff` / `brew install gitleaks` / `winget install gitleaks` as appropriate.
- All quality gate failures must be fixed locally before retrying.

## References

- `standards/framework/core.md` — non-negotiables and enforcement rules.
- `standards/framework/stacks/python.md` — Python-specific checks.
- `standards/framework/quality/core.md` — gate structure (pre-commit gate).
- `skills/workflows/acho/SKILL.md` — alias workflow.
- `agents/verify-app.md` — agent that validates commit workflow execution.
