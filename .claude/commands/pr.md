---
description: Create a pull request with structured description
---

## Context

Creates a pull request on GitHub or Azure DevOps with a well-structured description based on the commits and changes in the current branch.

## Inputs

$ARGUMENTS - Optional: target branch, PR title hint, or issue number to link

## Steps

### 1. Gather Context

- Run `git status` to check for uncommitted changes (warn if any)
- Run `git branch --show-current` to get the current branch
- Determine the base branch (default: `main` or `master`)
- Run `git log <base>..HEAD --oneline` to see all commits in this branch
- Run `git diff <base>...HEAD --stat` to see changed files summary

### 2. Check Remote

- Verify the branch is pushed to remote: `git rev-parse --abbrev-ref @{u}`
- If not pushed, push with: `git push -u origin <branch>`

### 3. Generate PR Content

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

### 4. Create PR

Using `gh pr create`:

```bash
gh pr create --title "<title>" --body "<body>"
```

If an issue number was provided, link it in the body.

### 5. Report

Output the PR URL and a summary.

## Verification

- PR is created and accessible
- Description accurately reflects the changes
- All commits are included
