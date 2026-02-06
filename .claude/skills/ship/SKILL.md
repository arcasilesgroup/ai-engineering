---
name: ship
description: "Stage, commit, push, and optionally create PR (GitHub + Azure DevOps)"
disable-model-invocation: true
---

## Context

Unified shipping workflow: stage changes, create a conventional commit, push to remote, and optionally create a pull request. Supports both GitHub and Azure DevOps.

Reference: `.claude/skills/utils/platform-detection.md` for platform detection logic.
Reference: `.claude/skills/utils/git-helpers.md` for git operations.

## Inputs

$ARGUMENTS - Optional modifiers and hints:
- No args: stage + commit + push
- `pr` or `--pr`: stage + commit + push + create PR (auto-merge ON by default)
- `pr-only`: create PR from current branch (no commit, auto-merge ON by default)
- `--no-auto-merge`: disable auto-merge when creating PR
- Additional text is used as commit message hint or PR target branch

## Steps

### 1. Determine Mode

Parse $ARGUMENTS to determine the workflow mode:
- **commit-push** (default): stage, commit, push
- **commit-push-pr** (`pr` arg): stage, commit, push, create PR
- **pr-only** (`pr-only` arg): just create a PR from the current branch

Determine auto-merge setting:
- If $ARGUMENTS contains `--no-auto-merge`: set **AUTO_MERGE=false**
- Otherwise: **AUTO_MERGE=true** (default for all PR modes)

If mode is `pr-only`, skip to Step 7.

### 2. Analyze Changes

- Run `git status` to see modified/untracked files
- Run `git diff` for unstaged changes and `git diff --cached` for staged changes
- Run `git log --oneline -5` to see recent commit message style

### 3. Determine What to Stage

- If $ARGUMENTS specifies files, stage those files
- Otherwise, identify logically related changes that form one atomic commit
- NEVER stage: `.env`, `*.key`, `*.pem`, `credentials.*`, `*secret*` files
- Prefer specific `git add <file>` over `git add -A`

### 4. Stage Files

- Stage the identified files with `git add <file>`

### 5. Secret Scanning (handled by pre-commit hook)

Secret scanning is handled automatically by the git pre-commit hook (gitleaks). No manual scan step is needed here. If secrets are detected, the commit will be blocked.

### 6. Generate Commit and Push

**Commit message:** Follow Conventional Commits format:

```
<type>[optional scope]: <description>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`

Keep the description under 72 characters. Use imperative mood ("add" not "added").

Extract work item references from branch name if present:
- GitHub: `Closes #123` or `Fixes #123`
- Azure DevOps: `AB#456`

Create the commit, then push:
- Determine current branch: `git branch --show-current`
- Push with tracking: `git push -u origin <branch>`
- If push fails due to upstream changes, inform the user and suggest `git pull --rebase`

**Pre-push Hook:** If installed, it will automatically run a vulnerability check:
- **CRITICAL vulnerabilities**: Push is **blocked** - fix before pushing
- **HIGH vulnerabilities**: Warning shown but push allowed

If mode is **commit-push** (no PR), skip to Step 9.

### 7. Detect Platform

Follow platform detection steps from `.claude/skills/utils/platform-detection.md`.

### 8. Create Pull Request

**Gather context (for pr-only mode):**
- Run `git status` to check for uncommitted changes (warn if any)
- Run `git branch --show-current` to get the current branch
- Run `git log <base>..HEAD --oneline` to see all commits
- Run `git diff <base>...HEAD --stat` to see changed files summary
- Verify branch is pushed to remote; if not, push with `git push -u origin <branch>`

**Determine target branch:**
- If $ARGUMENTS specifies a branch, use that
- Otherwise, detect default branch from git-helpers
- Fall back to `main`

**Generate PR content:**
- **Title**: Short, derived from branch name and commits (under 70 chars)
- **Body**: Use this structure:

```markdown
## Summary
- Bullet points describing what changed and why

## Changes
- List of significant changes by area

## Testing
- How the changes were tested
- [ ] Unit tests pass
- [ ] Manual testing done

## Checklist
- [ ] Code follows project standards
- [ ] Tests included
- [ ] No secrets committed
- [ ] Quality gates pass
```

**GitHub:**
```bash
PR_URL=$(gh pr create --title "<title>" --body "<body>" --base <target>)
```

**Azure DevOps:**
```bash
PR_ID=$(az repos pr create --title "<title>" --description "<body>" --target-branch <target> [--work-items <id>] --query "pullRequestId" -o tsv)
```

If an issue/work item number was detected, link it:
- GitHub: Add `Closes #123` to the body
- Azure DevOps: Add `--work-items AB#123` to the command

**Enable auto-merge (if AUTO_MERGE=true):**

After the PR is created, enable auto-merge with squash strategy:

**GitHub:**
```bash
gh pr merge --auto --squash "$PR_URL"
```

**Azure DevOps:**
```bash
az repos pr update --id "$PR_ID" --auto-complete true --merge-strategy squash
```

**Error handling:** If auto-merge fails (repo doesn't support it, branch policies prevent it, insufficient permissions):
- Warn but do NOT fail the PR creation
- Report: "Auto-merge could not be enabled: [reason]. PR created normally."
- Common reasons: auto-merge not enabled in repo settings, required reviews not met yet (this is expected — auto-merge will trigger after approval)

### 9. Report

    ## Ship Report

    **Mode:** commit-push | commit-push-pr | pr-only
    **Commit:** `<hash>` - <message> (if applicable)
    **Branch:** <branch> → <target>
    **PR:** <url> (if applicable)
    **Auto-merge:** enabled (squash) | disabled | failed: <reason> (if applicable)
    **Changes:** X files changed
    **Linked items:** #123 / AB#456 (if any)

## Verification

- No secrets in staged changes (enforced by pre-commit hook)
- Commit message follows conventional format (if applicable)
- Branch is pushed to remote
- PR is created and accessible (if applicable)
- Auto-merge is enabled (if applicable, verify with `gh pr view --json autoMergeRequest`)
- Work items/issues linked (if detected)
