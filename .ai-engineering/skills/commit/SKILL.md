---
name: commit
description: "Execute governed commit workflow: stage, lint, secret-detect, commit, and push current branch."
version: 1.0.0
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

## When NOT to Use

- **Creating pull requests** — use `/pr` instead. Commit pushes to current branch; PR creates a pull request.
- **Quick push alias** — use `/acho` instead for identical behavior with shorter invocation.
- **Governance content changes without active spec** — create a spec first with `govern:create-spec`.

## Procedure

### `/commit` (default: stage + commit + push)

1. **Stage changes** — `git add -A` (or selective staging if user specifies files).
2. **Run formatter** — `ruff format .` to auto-fix formatting.
3. **Run linter** — `ruff check . --fix` to auto-fix safe lint issues. If unfixable issues remain, report and stop.
4. **Run secret detection** — `gitleaks protect --staged --no-banner`. If secrets found, report and stop.
5. **Documentation gate** — evaluate and update documentation for OSS GitHub users.
   a. Analyze staged changes and classify documentation scope:
      - **CHANGELOG + README**: new features, breaking changes, new CLI commands, skill/agent additions or removals, config schema changes, architecture changes visible to users.
      - **CHANGELOG only**: any other functional change — src/ modifications, API changes, dependency bumps with behavioral impact, governance surface changes, workflow behavior changes.
      - **No updates needed**: changes with zero functional impact — typo fixes in comments, whitespace-only changes, test-only additions that don't change public behavior, CI config formatting. Log: "Documentation gate evaluated — no functional changes detected."
   b. Update **CHANGELOG.md** (when scope requires it):
      - If `CHANGELOG.md` exists: add entries to `[Unreleased]` section per `skills/docs/changelog/SKILL.md` format. Stage the updated file.
      - If `CHANGELOG.md` does NOT exist: create it following Keep a Changelog format. Stage the new file.
   c. Update **README.md** (when scope includes README):
      - If `README.md` exists AND changes include new features, breaking changes, new CLI commands, or skill catalog changes: update relevant sections. Stage the updated file.
      - If `README.md` does NOT exist AND changes are non-trivial: create it targeting OSS GitHub audience. Stage the new file.
   d. **External documentation portal**:
      - Ask: "Do you have an external documentation portal (docs site, wiki, separate repo)? Provide the repo URL, or 'skip'."
      - If URL provided: clone, branch, update, commit + push + create PR with auto-complete, report URL.
      - If 'skip': continue without external docs.
6. **Commit** — `git commit -m "<message>"` with a well-formed commit message following project conventions.
   - If active spec exists, use format: `spec-NNN: Task X.Y — <description>`.
   - Otherwise, use conventional commit format: `type(scope): description`.
7. **Push** — `git push origin <current-branch>`.
   - If current branch is `main` or `master`, **block** and report protected branch violation.

### `/commit --only` (stage + commit, no push)

Follow steps 1–6 above. Skip step 7.

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
- `skills/docs/changelog/SKILL.md` — changelog entry formatting (used by documentation gate).
- `skills/docs/writer/SKILL.md` — README and documentation update procedure for OSS GitHub users (used by documentation gate).
- `skills/workflows/acho/SKILL.md` — alias workflow.
- `agents/verify-app.md` — agent that validates commit workflow execution.
