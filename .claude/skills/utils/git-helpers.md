# Git Helpers

Reusable git operations referenced by skills.

## Default Branch

Detect the default branch (main or master):

```bash
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
if [ -z "$DEFAULT_BRANCH" ]; then
  # Fallback: check if main exists, otherwise use master
  if git show-ref --verify --quiet refs/remotes/origin/main 2>/dev/null; then
    DEFAULT_BRANCH="main"
  else
    DEFAULT_BRANCH="master"
  fi
fi
```

## Current Branch

```bash
CURRENT_BRANCH=$(git branch --show-current)
```

## Uncommitted Changes

Check if there are uncommitted changes:

```bash
if [ -n "$(git status --porcelain)" ]; then
  echo "Warning: You have uncommitted changes"
fi
```

## Remote Tracking

Check if the current branch has a remote tracking branch:

```bash
UPSTREAM=$(git rev-parse --abbrev-ref @{u} 2>/dev/null || echo "")
if [ -z "$UPSTREAM" ]; then
  echo "Branch is not tracking a remote branch"
fi
```

## Push with Tracking

```bash
git push -u origin "$(git branch --show-current)"
```

## Work Item Extraction

Extract work item IDs from branch names:

```bash
BRANCH_NAME=$(git branch --show-current)

# GitHub issues: feature/123-description or fix/GH-123-description
GITHUB_ISSUE=$(echo "$BRANCH_NAME" | grep -oE '#?[0-9]+' | head -1 | tr -d '#')

# Azure DevOps: feature/AB#123-description
AZDO_ITEM=$(echo "$BRANCH_NAME" | grep -oE 'AB#[0-9]+' | head -1)
```

## Commits Since Base Branch

```bash
# Get all commits not in the base branch
git log "$DEFAULT_BRANCH"..HEAD --oneline

# Get changed files summary
git diff "$DEFAULT_BRANCH"...HEAD --stat
```

## Safe Branch Check

Check if on a protected branch:

```bash
CURRENT=$(git branch --show-current)
if [ "$CURRENT" = "main" ] || [ "$CURRENT" = "master" ]; then
  echo "Warning: You are on a protected branch"
fi
```
