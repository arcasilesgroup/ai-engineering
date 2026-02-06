---
name: git
description: "Git workflow management: sync, branch, cleanup, and health checks (GitHub + Azure DevOps)"
---

## Context

Git way-of-working enforcement for AI and human engineers. Handles repository synchronization, branch creation from the default branch, merged-branch cleanup with smart deletion logic, and repository health audits. Supports both GitHub and Azure DevOps.

Reference: `.claude/skills/utils/git-helpers.md` for git operations.
Reference: `.claude/skills/utils/platform-detection.md` for platform detection logic.
Reference: `standards/global.md` (Git Conventions section) for branching strategy and compliance branches.

## Inputs

$ARGUMENTS - Subcommand and optional parameters:
- (no args): Run full workflow — sync + cleanup + health
- `sync`: Fetch, prune, pull latest on current branch and default branch
- `branch <type/name>`: Create a new branch from the default branch (e.g., `feature/add-login`)
- `cleanup`: Delete merged branches locally and remotely using smart deletion logic
- `health`: Full repository health report

## Steps

### 1. Determine Mode

Parse $ARGUMENTS:
- If empty or `all` → mode = **full** (sync + cleanup + health, in that order)
- If starts with `sync` → mode = **sync**
- If starts with `branch` → mode = **branch**
- If starts with `cleanup` → mode = **cleanup**
- If starts with `health` → mode = **health**

### 2. Pre-flight Checks

- Verify inside a git repository: `git rev-parse --is-inside-work-tree`
- Detect the **default branch** using the enhanced detection from git-helpers (symbolic-ref → fallback → platform CLI). Store as `$DEFAULT_BRANCH`. Never hardcode "main".
- Detect **platform** using platform-detection.md. Store as `$PLATFORM` (github, azure, unknown).
- Check for uncommitted changes: `git status --porcelain`
  - If changes exist: warn the user but continue (do NOT block)

---

### 3. Sync Remote State (runs in: sync, full)

**Fetch and prune all remotes:**
```bash
git fetch --all --prune
```

**Update the default branch:**
- If currently on `$DEFAULT_BRANCH`:
  ```bash
  git pull --ff-only origin "$DEFAULT_BRANCH"
  ```
- If on a different branch:
  ```bash
  git fetch origin "$DEFAULT_BRANCH":"$DEFAULT_BRANCH"
  ```
  - If this fails (e.g., local changes on default branch), warn and skip

**Update develop branch (if it exists):**
```bash
if git show-ref --verify --quiet refs/remotes/origin/develop 2>/dev/null; then
  git fetch origin develop:develop 2>/dev/null || true
fi
```

**Pull current branch (if tracking a remote):**
```bash
UPSTREAM=$(git rev-parse --abbrev-ref @{u} 2>/dev/null || echo "")
if [ -n "$UPSTREAM" ]; then
  git pull --ff-only || echo "Warning: Could not fast-forward current branch"
fi
```

Report: which branches were updated, current branch status.

---

### 4. Create Branch (runs in: branch)

Parse branch name from $ARGUMENTS (everything after `branch`).

**Validate branch name** against allowed prefixes using git-helpers Branch Name Validation:
- `feature/`, `fix/`, `bugfix/`, `hotfix/`, `release/`, `chore/`, `docs/`
- If name doesn't start with a valid prefix: suggest the correct format and stop

**Determine base branch:**
- Default: `$DEFAULT_BRANCH`
- If $ARGUMENTS includes `from <branch>` or specifies a compliance branch, use that instead
- Validate the base is a compliance branch or the default branch

**Create the branch:**
```bash
git fetch origin "$BASE_BRANCH":"$BASE_BRANCH" 2>/dev/null || git pull --ff-only origin "$BASE_BRANCH"
git checkout -b "<branch-name>" "$BASE_BRANCH"
```

Report: new branch name, base branch, base commit SHA.

---

### 5. Cleanup Merged Branches (runs in: cleanup, full)

For each local branch (excluding current and compliance branches), apply the **Smart Deletion Decision Tree**:

#### 5a. Identify Compliance Branches

Using git-helpers Is Compliance Branch check, identify all compliance branches in the repo. These are NEVER deleted.

#### 5b. Local Cleanup — Auto-delete (100% safe)

For each non-compliance, non-current local branch:

1. **Check if remote tracking is gone:**
   ```bash
   git branch -vv | grep ': gone]'
   ```

2. **Verify fully merged into default branch:**
   ```bash
   git merge-base --is-ancestor "$BRANCH" "$DEFAULT_BRANCH"
   ```

3. **Verify no post-merge commits:**
   ```bash
   MERGE_BASE=$(git merge-base "$BRANCH" "$DEFAULT_BRANCH")
   POST_MERGE=$(git rev-list "$MERGE_BASE".."$BRANCH" --count)
   ```

4. **Decision:**
   - Remote gone + fully merged + zero post-merge commits → **auto-delete** with `git branch -d "$BRANCH"`
   - Fully merged but has post-merge commits → **report** as "active development on merged branch"
   - Not merged → **report** as "unmerged branch"

#### 5c. Remote Cleanup — Auto-delete (100% safe)

Query completed/merged PRs from the platform:

**GitHub:**
```bash
gh pr list --state merged --json headRefName --limit 50 --jq '.[].headRefName'
```

**Azure DevOps:**
```bash
az repos pr list --status completed --top 50 --query "[].sourceRefName" -o tsv | sed 's|refs/heads/||'
```

For each branch from a merged PR that still exists on remote:
1. Verify the branch is NOT a compliance branch
2. Verify no additional commits after the merge (compare remote branch tip with merge commit)
3. If safe → **auto-delete**: `git push origin --delete "$BRANCH"`

If platform CLI is not available, skip remote cleanup with a warning.

#### 5d. Report Cleanup Results

List what was auto-deleted and what was reported for manual decision.

---

### 6. Health Check (runs in: health, full)

Run all health checks and collect findings:

#### 6a. Unpushed Branches

List local branches with no remote tracking:
```bash
git for-each-ref --format='%(refname:short) %(upstream:short)' refs/heads/ | awk '$2 == "" {print $1}'
```
Exclude compliance branches from warnings (they are expected to be local).

#### 6b. Branches Ahead of Remote

List local branches that have commits not pushed:
```bash
git for-each-ref --format='%(refname:short) %(upstream:track)' refs/heads/ | grep '\[ahead' | awk '{print $1}'
```

#### 6c. Stale Branches

List branches with no commits in the last 30 days using git-helpers Stale Branch Detection (macOS + Linux compatible).

#### 6d. Remote Branches Not Merged

```bash
git branch -r --no-merged "origin/$DEFAULT_BRANCH" | grep -v HEAD
```
Exclude compliance branches (release/*, hotfix/*) from the "unmerged" report — they have their own lifecycle.

#### 6e. Compliance Branch Status

For each compliance branch that exists:
- Check if `develop` is behind/ahead of `$DEFAULT_BRANCH`
- Check if `release/*` branches have been merged back
- Report divergence with commit counts

#### 6f. Open PR Status

**GitHub:**
```bash
gh pr list --state open --json number,title,author,createdAt,reviewDecision,isDraft,headRefName,baseRefName
```

**Azure DevOps:**
```bash
az repos pr list --status active --top 50 --output json
```

Flag:
- PRs older than 7 days without review → "needs review"
- PRs with changes requested not addressed → "changes requested"
- Draft PRs older than 14 days → "stale draft"

If platform CLI is not available, skip PR checks with a warning.

---

### 7. Report

    ## Git Report

    **Mode:** sync | branch | cleanup | health | full
    **Platform:** GitHub | Azure DevOps | Unknown
    **Default branch:** <detected branch name>

    ### Sync (if applicable)
    - Fetched and pruned all remotes
    - Default branch ($DEFAULT_BRANCH): up to date | updated to <sha>
    - Develop: up to date | updated | not present
    - Current branch: up to date | updated | warning

    ### Branch (if applicable)
    - Created: `<branch-name>` from `<base-branch>` @ `<sha>`

    ### Cleanup (if applicable)
    **Auto-deleted (100% safe):**
    | Branch | Reason |
    |--------|--------|
    | feature/old-thing | merged, remote gone, no post-merge commits |

    **Reported (manual decision needed):**
    | Branch | State | Issue |
    |--------|-------|-------|
    | feature/wip | merged | has 2 post-merge commits |
    | fix/pending | not merged | unmerged, consider creating PR |

    ### Health (if applicable)
    **Unpushed work:**
    | Branch | Last commit | Age |
    |--------|-------------|-----|
    | feature/local-only | "add user model" | 2 days |

    **Branches ahead of remote:**
    | Branch | Commits ahead |
    |--------|---------------|
    | fix/in-progress | 3 ahead |

    **Stale branches (>30 days):**
    | Branch | Last activity | Location |
    |--------|---------------|----------|
    | feature/abandoned | 45 days | local + remote |

    **Compliance branch status:**
    | Branch | State | Behind default | Ahead of default |
    |--------|-------|---------------|-----------------|
    | develop | diverged | 5 behind | 3 ahead |

    **Open PRs:**
    | PR | Title | Target | Age | Status |
    |----|-------|--------|-----|--------|
    | #42 | Add login | main | 8 days | needs review |

    ### Recommendations
    - [ ] Push branch `feature/local-only` or delete if abandoned
    - [ ] Review PR #42 (pending 8 days)
    - [ ] Delete stale branch `feature/abandoned`
    - [ ] Sync develop with default branch

## Verification

- Sync completed without errors (fetch, prune, pull)
- Default branch detected dynamically (not hardcoded)
- No compliance branches were deleted
- No force-deletes performed (only `git branch -d`)
- Auto-deleted branches were verified: merged + no post-merge commits + remote gone
- Branch names validated against naming convention
- Health report is accurate (cross-checked with actual git state)
- Platform-specific commands used correctly (GitHub or Azure DevOps)
