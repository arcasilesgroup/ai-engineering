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

## Fetch and Prune

Fetch all remotes and prune stale tracking references:

```bash
git fetch --all --prune
```

## Detect Default Branch (Enhanced)

Detect the default branch using multiple strategies:

```bash
# Strategy 1: symbolic-ref (most reliable for cloned repos)
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')

# Strategy 2: Fallback to checking common names
if [ -z "$DEFAULT_BRANCH" ]; then
  if git show-ref --verify --quiet refs/remotes/origin/main 2>/dev/null; then
    DEFAULT_BRANCH="main"
  elif git show-ref --verify --quiet refs/remotes/origin/master 2>/dev/null; then
    DEFAULT_BRANCH="master"
  fi
fi

# Strategy 3: Platform CLI (if git detection fails)
if [ -z "$DEFAULT_BRANCH" ]; then
  REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
  if echo "$REMOTE_URL" | grep -q "github.com"; then
    DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null || echo "")
  elif echo "$REMOTE_URL" | grep -qE "dev.azure.com|visualstudio.com"; then
    DEFAULT_BRANCH=$(az repos show --query "defaultBranch" -o tsv 2>/dev/null | sed 's@refs/heads/@@' || echo "")
  fi
fi

# Final fallback
if [ -z "$DEFAULT_BRANCH" ]; then
  DEFAULT_BRANCH="main"
fi
```

## Update Default Branch Without Switching

Update the local default branch ref from remote without checking it out:

```bash
# If NOT currently on the default branch:
git fetch origin "$DEFAULT_BRANCH":"$DEFAULT_BRANCH"

# If currently on the default branch:
git pull --ff-only origin "$DEFAULT_BRANCH"
```

## Identify Compliance Branches

List all compliance branches (protected, require PRs, never auto-deleted):

```bash
# Compliance branch patterns: main, master, develop, dev/*, release/*, hotfix/*
COMPLIANCE_PATTERNS="^(main|master|develop)$|^dev/|^release/|^hotfix/"
```

## Is Compliance Branch

Check if a given branch matches any compliance pattern:

```bash
is_compliance_branch() {
  local BRANCH="$1"
  if echo "$BRANCH" | grep -qE "^(main|master|develop)$|^dev/|^release/|^hotfix/"; then
    return 0  # true
  fi
  return 1  # false
}
```

## List Orphaned Local Branches

List local branches whose remote tracking branch no longer exists:

```bash
git branch -vv | grep ': gone]' | awk '{print $1}'
```

## List Merged Local Branches

List local branches fully merged into the default branch (excluding compliance and current):

```bash
CURRENT=$(git branch --show-current)
git branch --merged "$DEFAULT_BRANCH" | while read -r branch; do
  branch=$(echo "$branch" | tr -d '* ')
  # Skip compliance branches and current branch
  if echo "$branch" | grep -qE "^(main|master|develop)$|^dev/|^release/|^hotfix/"; then
    continue
  fi
  if [ "$branch" = "$CURRENT" ]; then
    continue
  fi
  echo "$branch"
done
```

## List Unpushed Branches

List local branches with no remote tracking branch:

```bash
git for-each-ref --format='%(refname:short) %(upstream:short)' refs/heads/ | awk '$2 == "" {print $1}'
```

## List Branches Ahead of Remote

List local branches that have commits not pushed to remote:

```bash
git for-each-ref --format='%(refname:short) %(upstream:track)' refs/heads/ | grep '\[ahead' | awk '{print $1}'
```

## Branch Last Commit Date

Get the last commit date and message for a branch:

```bash
LAST_COMMIT_DATE=$(git log -1 --format="%ci" "$BRANCH_NAME")
LAST_COMMIT_MSG=$(git log -1 --format="%s" "$BRANCH_NAME")
LAST_COMMIT_AGE_DAYS=$(( ($(date +%s) - $(git log -1 --format="%ct" "$BRANCH_NAME")) / 86400 ))
```

## Stale Branch Detection

List branches with no commits in the last N days (macOS + Linux compatible):

```bash
DAYS=30
CUTOFF=$(date -v-${DAYS}d +%s 2>/dev/null || date -d "-${DAYS} days" +%s 2>/dev/null)
git for-each-ref --sort=committerdate --format='%(refname:short) %(committerdate:unix)' refs/heads/ | while read -r branch date; do
  if [ "$date" -lt "$CUTOFF" ]; then
    echo "$branch"
  fi
done
```

## Remote Branches Not Merged

List remote branches not merged into the default branch:

```bash
git branch -r --no-merged "origin/$DEFAULT_BRANCH" | grep -v HEAD
```

## Branch Name Validation

Validate a branch name against allowed prefixes:

```bash
VALID_PREFIXES="feature/ fix/ bugfix/ hotfix/ release/ chore/ docs/"
BRANCH_NAME="$1"
VALID=false
for prefix in $VALID_PREFIXES; do
  if [[ "$BRANCH_NAME" == ${prefix}* ]]; then
    VALID=true
    break
  fi
done
if [ "$VALID" = false ]; then
  echo "Error: Branch name must start with one of: $VALID_PREFIXES"
fi
```

## Verify Branch Fully Merged

Check if a branch is fully merged into the default branch:

```bash
if git merge-base --is-ancestor "$BRANCH_NAME" "$DEFAULT_BRANCH"; then
  echo "Branch $BRANCH_NAME is fully merged into $DEFAULT_BRANCH"
fi
```

## Check Commits After Merge Point

Verify no additional commits exist after the merge point (detects post-merge development):

```bash
MERGE_BASE=$(git merge-base "$BRANCH_NAME" "$DEFAULT_BRANCH")
POST_MERGE_COMMITS=$(git rev-list "$MERGE_BASE".."$BRANCH_NAME" --count)
if [ "$POST_MERGE_COMMITS" -gt 0 ]; then
  echo "Branch has $POST_MERGE_COMMITS commits after merge point — active development"
fi
```

## Open PR Status (GitHub)

```bash
gh pr list --state open --json number,title,author,createdAt,reviewDecision,isDraft,headRefName,baseRefName
```

## Open PR Status (Azure DevOps)

```bash
az repos pr list --status active --top 50 --output json
```

## Completed PR Branches (GitHub)

List branches from recently merged PRs that still exist on remote:

```bash
gh pr list --state merged --json headRefName --limit 50 --jq '.[].headRefName'
```

## Completed PR Branches (Azure DevOps)

```bash
az repos pr list --status completed --top 50 --query "[].sourceRefName" -o tsv | sed 's|refs/heads/||'
```
