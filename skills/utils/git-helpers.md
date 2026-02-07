# Git Helpers — Shared Utilities

These utilities are referenced by multiple skills. Use them instead of duplicating git logic.

---

## Default Branch Detection (3-Tier Fallback)

Always detect the default branch using this sequence. Never hardcode `main` or `master`.

```bash
# Tier 1: symbolic-ref (fastest, works when remote HEAD is set)
DEFAULT_BRANCH="$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || true)"

# Tier 2: show-ref for common names
if [[ -z "$DEFAULT_BRANCH" ]]; then
  if git show-ref --verify --quiet refs/remotes/origin/main 2>/dev/null; then
    DEFAULT_BRANCH="main"
  elif git show-ref --verify --quiet refs/remotes/origin/master 2>/dev/null; then
    DEFAULT_BRANCH="master"
  fi
fi

# Tier 3: Platform CLI
if [[ -z "$DEFAULT_BRANCH" ]]; then
  DEFAULT_BRANCH="$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null || true)"
fi
if [[ -z "$DEFAULT_BRANCH" ]]; then
  DEFAULT_BRANCH="$(az repos show --query 'defaultBranch' -o tsv 2>/dev/null | sed 's@refs/heads/@@' || true)"
fi

# Fallback
if [[ -z "$DEFAULT_BRANCH" ]]; then
  DEFAULT_BRANCH="main"
fi
```

---

## Current Branch and Status

```bash
# Current branch name
CURRENT_BRANCH="$(git branch --show-current 2>/dev/null || echo "")"

# Check for uncommitted changes
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
  echo "You have uncommitted changes."
fi

# Check for untracked files
UNTRACKED="$(git ls-files --others --exclude-standard 2>/dev/null)"
```

---

## Remote Tracking

```bash
# Check if current branch tracks a remote
UPSTREAM="$(git rev-parse --abbrev-ref @{upstream} 2>/dev/null || echo "")"

# Push with tracking (set upstream if needed)
if [[ -z "$UPSTREAM" ]]; then
  git push -u origin HEAD
else
  git push
fi

# Check if branch is ahead/behind remote
AHEAD="$(git rev-list --count @{upstream}..HEAD 2>/dev/null || echo 0)"
BEHIND="$(git rev-list --count HEAD..@{upstream} 2>/dev/null || echo 0)"
```

---

## Compliance Branch Detection

A compliance branch is a long-lived branch that follows the project's branching strategy.

```bash
is_compliance_branch() {
  local branch="$1"
  case "$branch" in
    "$DEFAULT_BRANCH"|develop|development|staging|production)
      return 0 ;;
    release/*|hotfix/*)
      return 0 ;;
    *)
      return 1 ;;
  esac
}
```

---

## Work Item Extraction

Extract work item references from branch names and commit messages.

### GitHub Issues

```bash
# Extract #123 references from branch name or text
GITHUB_ISSUES="$(echo "$TEXT" | grep -oE '#[0-9]+' || true)"

# Generate closing keywords for PR body
# e.g., "Closes #123, Closes #456"
```

### Azure DevOps Work Items

```bash
# Extract AB#123 references from branch name
AZDO_ITEMS="$(echo "$BRANCH_NAME" | grep -oE 'AB#[0-9]+' || true)"

# Extract numeric IDs for az CLI --work-items flag
AZDO_IDS="$(echo "$BRANCH_NAME" | grep -oE 'AB#[0-9]+' | sed 's/AB#//' || true)"
```

---

## Branch Validation

```bash
# Check if a branch exists locally
git show-ref --verify --quiet "refs/heads/$BRANCH_NAME" 2>/dev/null

# Check if a branch exists on remote
git show-ref --verify --quiet "refs/remotes/origin/$BRANCH_NAME" 2>/dev/null

# Check if branch is fully merged into target
git merge-base --is-ancestor "$BRANCH_NAME" "$TARGET_BRANCH" 2>/dev/null
```

---

## Stale Branch Detection

```bash
# Get last commit date for a branch (ISO format)
LAST_COMMIT="$(git log -1 --format='%ci' "$BRANCH_NAME" 2>/dev/null || echo "")"

# Branches with no activity in 30+ days
STALE_THRESHOLD=$(date -v-30d +%s 2>/dev/null || date -d '30 days ago' +%s 2>/dev/null || echo 0)
BRANCH_DATE=$(git log -1 --format='%ct' "$BRANCH_NAME" 2>/dev/null || echo 0)
if [[ "$BRANCH_DATE" -lt "$STALE_THRESHOLD" ]]; then
  echo "Branch $BRANCH_NAME is stale (>30 days)"
fi
```

---

## PR Status Commands

Use the platform-detection utility to determine which commands to run.

### GitHub

```bash
# List open PRs
gh pr list --state open

# View specific PR
gh pr view <number>

# Check PR checks status
gh pr checks <number>

# Create PR
gh pr create --title "..." --body "..." --base "$DEFAULT_BRANCH"

# Enable auto-merge
gh pr merge --auto --squash <number>
```

### Azure DevOps

```bash
# List open PRs
az repos pr list --status active

# View specific PR
az repos pr show --id <id>

# Create PR
az repos pr create --title "..." --description "..." --source-branch "$CURRENT_BRANCH" --target-branch "$DEFAULT_BRANCH"

# Enable auto-complete (auto-merge equivalent)
az repos pr update --id <id> --auto-complete true --merge-strategy squash
```

---

## Diff Analysis

```bash
# Changes on current branch vs default branch
git diff "$DEFAULT_BRANCH"..HEAD --stat
git diff "$DEFAULT_BRANCH"..HEAD --name-only

# Commits on current branch not in default
git log "$DEFAULT_BRANCH"..HEAD --oneline --no-merges

# Full diff for analysis
git diff "$DEFAULT_BRANCH"..HEAD
```
