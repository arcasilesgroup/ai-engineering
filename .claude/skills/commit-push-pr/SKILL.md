---
name: commit-push-pr
description: "Full cycle: secret scan, commit, push, and create PR (GitHub + Azure DevOps)"
disable-model-invocation: true
---

## Context

Complete git cycle in one skill: scan for secrets, stage and commit changes, push to remote, and create a pull request. Supports both GitHub and Azure DevOps.

Reference: `.claude/skills/utils/platform-detection.md` for platform detection logic.
Reference: `.claude/skills/utils/git-helpers.md` for git operations.

## Inputs

$ARGUMENTS - Optional: target branch for the PR (defaults to default branch: main/master)

## Steps

### 1. Secret Scan

Before anything else, scan for leaked secrets:
- Look for patterns: API keys (`AKIA`, `sk-`, `ghp_`, `xox`), connection strings, private keys
- If `gitleaks` is available, run: `gitleaks detect --source . --no-git --verbose`
- If secrets are found, **STOP** and report them. Do NOT proceed.

### 2. Detect Platform

Detect the git platform from remote URL:
- `git remote get-url origin`
- If contains `github.com` → GitHub (use `gh` CLI)
- If contains `dev.azure.com` or `visualstudio.com` → Azure DevOps (use `az repos` CLI)
- Verify the CLI is available and authenticated
- If platform cannot be detected, ask the user

### 3. Analyze and Stage Changes

- Run `git status` to see modified/untracked files
- Run `git diff` and `git diff --cached` to understand changes
- Identify logically related changes that form one atomic commit
- NEVER stage: `.env`, `*.key`, `*.pem`, `credentials.*`, `*secret*` files
- Stage with specific `git add <file>` commands (not `git add -A`)

### 4. Generate Conventional Commit

- Run `git log --oneline -5` to match recent commit style
- Follow Conventional Commits: `<type>[scope]: <description>`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`
- Keep under 72 characters, imperative mood
- Extract work item references from branch name if present:
  - GitHub: `Closes #123` or `Fixes #123`
  - Azure DevOps: `AB#456`

### 5. Commit

Create the commit with the generated message.

### 6. Push

- Determine current branch: `git branch --show-current`
- Push with tracking: `git push -u origin <branch>`

### 7. Create Pull Request

Determine target branch:
- If $ARGUMENTS specifies a branch, use that
- Otherwise, detect default branch: `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'`
- Fall back to `main`

Generate PR content:
- **Title**: Short, derived from branch name and commits (under 70 chars)
- **Body**: Summary of changes, testing checklist, linked items

**GitHub:**
```bash
gh pr create --title "<title>" --body "<body>" --base <target>
```

**Azure DevOps:**
```bash
az repos pr create --title "<title>" --description "<body>" --target-branch <target> [--work-items <id>]
```

### 8. Report

    ## Commit + PR Report

    **Commit:** `<hash>` - <message>
    **Branch:** <branch> → <target>
    **PR:** <url>
    **Changes:** X files changed
    **Linked items:** #123 / AB#456 (if any)

## Verification

- No secrets in committed files
- Commit message follows conventional format
- Branch is pushed to remote
- PR is created and accessible
- Work items/issues linked (if detected)
