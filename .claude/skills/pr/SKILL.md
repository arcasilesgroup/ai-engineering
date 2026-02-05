---
name: pr
description: Create a pull request with structured description (GitHub + Azure DevOps)
disable-model-invocation: true
---

## Context

Creates a pull request on GitHub or Azure DevOps with a well-structured description based on the commits and changes in the current branch.

Reference: `.claude/skills/utils/platform-detection.md` for platform detection logic.

## Inputs

$ARGUMENTS - Optional: target branch, PR title hint, or issue/work item number to link

## Steps

### 1. Gather Context

- Run `git status` to check for uncommitted changes (warn if any)
- Run `git branch --show-current` to get the current branch
- Determine the base branch (default: `main` or `master`)
- Run `git log <base>..HEAD --oneline` to see all commits in this branch
- Run `git diff <base>...HEAD --stat` to see changed files summary

### 2. Detect Platform

Follow platform detection steps from `.claude/skills/utils/platform-detection.md`.

### 3. Check Remote

- Verify the branch is pushed to remote: `git rev-parse --abbrev-ref @{u}`
- If not pushed, push with: `git push -u origin <branch>`

### 4. Generate PR Content

**Title:** Short, descriptive (under 70 characters). Derive from branch name and commits.

**Body:** Use this structure:

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

### 5. Create PR

**GitHub:**
```bash
gh pr create --title "<title>" --body "<body>" --base <target-branch>
```

**Azure DevOps:**
```bash
az repos pr create --title "<title>" --description "<body>" --target-branch <target-branch> [--work-items <id>]
```

If an issue/work item number was provided, link it:
- GitHub: Add `Closes #123` to the body
- Azure DevOps: Add `--work-items AB#123` to the command

### 6. Report

Output the PR URL and a summary.

## Verification

- PR is created and accessible
- Description accurately reflects the changes
- All commits are included
- Work items/issues linked (if applicable)
