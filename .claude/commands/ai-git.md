# /ai-git — Git Way-of-Working Skill

This skill provides a comprehensive set of git maintenance, health-check, and hygiene sub-commands. It helps keep repositories clean, identifies risks, and surfaces actionable recommendations. It is opinionated about safety: it will auto-delete only what is provably safe, and it will report everything else for manual decision.

---

## Session Preamble (execute silently)

Before any user-visible action, silently internalize project context:

1. Read `.ai-engineering/knowledge/learnings.md` — lessons learned during development
2. Read `.ai-engineering/knowledge/patterns.md` — established conventions (especially branching patterns)
3. Read `.ai-engineering/knowledge/anti-patterns.md` — known mistakes to avoid
4. Identify the current branch and working tree state

Do not report this step to the user. Internalize it as context for decision-making.

---

## Trigger

- `/ai-git` — Run the full report (fetch, cleanup, health, recommendations).
- `/ai-git cleanup` — Run branch cleanup only.
- `/ai-git health` — Run health check only.

---

## Progressive Disclosure

Start with the **Quick Health Summary** — a 5-line overview of the repository state. Only expand into detailed sub-reports when:

- The user explicitly requests details (`/ai-git health`, `/ai-git cleanup`)
- The quick summary reveals issues that need attention (CRITICAL or HIGH findings)
- The user asks follow-up questions

```
Quick Health Summary:
  Branch: feature/auth (3 ahead, 0 behind origin)
  Working tree: clean
  Branches: 12 local (4 merged, 2 stale)
  PRs: 3 open (1 stale)
  Risk: LOW — no unpushed work, no critical issues

  Run `/ai-git cleanup` for branch cleanup or `/ai-git health` for full analysis.
```

---

## Prerequisites

Before any sub-command, verify:

- The current directory is a git repository (`git rev-parse --git-dir`).
- At least one remote is configured (`git remote -v`). If no remote exists, report it and limit operations to local analysis.
- The user has network access to remotes (attempt `git fetch` and report if it fails rather than silently skipping).

---

## /ai-git cleanup — Branch Cleanup

This sub-command identifies branches that can be safely deleted and removes them. It never deletes branches that might contain unmerged work.

### Step 1: Fetch and Prune

```bash
# Fetch all remotes and prune stale tracking references
git fetch --all --prune
```

- Report the result: how many tracking references were pruned, if any.
- If fetch fails (network error, auth failure), warn the user and proceed with local-only analysis. Note the limitation in the report.

### Step 2: Identify the Default Branch

Use the **3-tier default branch detection** from the Git Helpers shared utility:

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

- If all tiers fail, ask the user to specify the default branch. Do not guess.

### Step 3: Identify Merged Branches (Safe to Delete)

A branch is **safe to delete** if:

1. It has been merged into the default branch (all commits are reachable from the default branch).
2. It has no commits after the merge point.
3. It is not the current branch.
4. It is not a protected branch.

```bash
# Local branches merged into default
git branch --merged <default-branch> | grep -v -E '^\*|main|master|develop|release/|hotfix/'

# Remote branches merged into default (tracking references)
git branch -r --merged <default-branch> | grep -v -E 'HEAD|main|master|develop|release/|hotfix/'
```

**Action:** Auto-delete these branches (both local and remote tracking) with user confirmation.

```bash
# Delete local merged branch
git branch -d <branch-name>

# Delete remote merged branch
git push origin --delete <branch-name>
```

- Always use `-d` (safe delete), never `-D` (force delete).
- Present the full list before deleting and ask for confirmation: "The following N branches are fully merged and safe to delete. Proceed? [y/N]"
- If the user declines, skip deletion and report the list for manual handling.

### Step 4: Identify Merged Branches with Post-Merge Commits

A branch is **merged but has diverged** if:

1. The merge base with the default branch contains all of the branch's original commits.
2. But the branch has additional commits after the merge point.

```bash
# For each branch, compare merge-base to branch tip
git log <default-branch>..<branch-name> --oneline
```

**Action:** Do NOT auto-delete. Report these branches with details:

```
Merged but diverged branches (manual review required):
  feature/auth-v2 — merged to main, but has 3 commits after merge point
    abc1234 fix: address review comments
    def5678 refactor: extract helper
    ghi9012 test: add edge case
  Recommendation: Verify these post-merge commits are intentional or delete manually.
```

### Step 5: Identify Unmerged Branches

A branch is **unmerged** if it contains commits not reachable from the default branch.

```bash
# Local branches NOT merged into default
git branch --no-merged <default-branch>
```

**Action:** Never auto-delete. Report with context:

```
Unmerged branches (not safe to auto-delete):
  feature/payment-gateway — 12 commits ahead of main, last activity 5 days ago
  experiment/new-ui — 3 commits ahead of main, last activity 45 days ago
  Recommendation: Review and decide — merge, rebase, or manually delete.
```

### Step 6: Report Summary

Produce a summary of all actions taken and pending decisions:

```
Branch Cleanup Summary
──────────────────────
Pruned tracking references:  4
Deleted merged branches:     7 (local: 5, remote: 2)
Merged but diverged:         2 (manual review required)
Unmerged branches:           3 (no action taken)
Protected branches skipped:  2 (main, develop)
```

---

## /ai-git health — Repository Health Check

This sub-command analyzes the repository state and surfaces risks, staleness, and pending work.

### Check 1: Unpushed Work

Identify local branches with commits that are not on any remote:

```bash
# For each local branch, check if it has an upstream and if it's ahead
git for-each-ref --format='%(refname:short) %(upstream:short) %(upstream:track)' refs/heads/
```

Report branches with unpushed commits:

```
Unpushed work:
  feature/search — 4 commits not pushed to origin/feature/search
  bugfix/null-check — no remote tracking branch (entirely local, 2 commits)
  Risk: If this machine is lost, these changes are lost.
  Recommendation: Push branches to remote for backup.
```

### Check 2: Branches Ahead of Remote

Identify branches where local is ahead of the remote tracking branch:

```bash
git for-each-ref --format='%(refname:short) %(upstream:short) %(upstream:trackshort)' refs/heads/ | grep '>'
```

```
Branches ahead of remote:
  feature/search — 4 commits ahead of origin/feature/search
  develop — 1 commit ahead of origin/develop
  Recommendation: Push pending changes.
```

### Check 3: Stale Branches

Identify branches with no activity in the last 30 days:

```bash
# For each branch, get the date of the most recent commit
git for-each-ref --sort=-committerdate --format='%(refname:short) %(committerdate:relative) %(committerdate:iso8601)' refs/heads/
```

Report branches older than 30 days:

```
Stale branches (>30 days inactive):
  experiment/new-ui — last activity 45 days ago (Dec 24, 2025)
  spike/redis-cache — last activity 62 days ago (Dec 7, 2025)
  Recommendation: Delete if no longer needed, or rebase onto current default branch if work should continue.
```

Configurable threshold: if the project specifies a different staleness threshold, use it. Default is 30 days.

### Check 4: Compliance Branch Status

Check the state of long-lived branches relative to the default branch:

```bash
# Commits on default branch not on the compliance branch
git log <compliance-branch>..<default-branch> --oneline --count

# Commits on compliance branch not on default branch
git log <default-branch>..<compliance-branch> --oneline --count
```

Compliance branches include: `develop`, `staging`, `release/*`, and any configured in the project.

```
Compliance branch status:
  develop — 3 commits behind main, 7 commits ahead
    Behind: main has 3 commits not in develop (merged PRs: #140, #141, #142)
    Ahead: develop has 7 commits not in main (pending release)
    Recommendation: Merge main into develop to pick up recent fixes.

  release/2.1 — 0 behind main, 15 ahead
    Status: Ready for release (no missing main commits)
```

### Check 5: Open Pull Requests

Query the platform for open PRs:

```bash
# GitHub
gh pr list --state open --json number,title,createdAt,author,reviewDecision,headRefName,baseRefName,isDraft

# Azure DevOps
az repos pr list --status active --output json
```

Report PR status with staleness indicators:

```
Open pull requests:
  #143 feat: add JWT token refresh (feature/token-refresh → main)
    Author: @alice | Created: 2 days ago | Status: Review requested
    Reviews: 1 approved, 1 changes requested

  #138 fix: correct timezone handling (bugfix/timezone → main)
    Author: @bob | Created: 14 days ago | Status: STALE
    Reviews: None
    Recommendation: This PR is 14 days old with no reviews. Ping reviewers or close.

  #135 chore: upgrade dependencies (chore/deps → develop)
    Author: @carol | Created: 21 days ago | Status: STALE, DRAFT
    Reviews: None
    Recommendation: Convert from draft or close if abandoned.
```

Staleness thresholds:

- **Active:** Created within the last 7 days or has review activity within the last 3 days.
- **Aging:** 7-14 days with no recent activity.
- **Stale:** More than 14 days with no recent activity.
- **Abandoned:** More than 30 days with no activity.

### Check 6: Actionable Recommendations

Based on all health checks, produce a prioritized list of recommendations:

```
Recommendations (ordered by priority):
  1. CRITICAL: 2 branches have unpushed work. Push to remote immediately.
  2. HIGH: PR #138 is stale (14 days, no reviews). Ping reviewers or close.
  3. MEDIUM: develop is 3 commits behind main. Merge main into develop.
  4. LOW: 2 stale branches (>30 days). Review and clean up.
  5. LOW: PR #135 is a stale draft (21 days). Convert or close.
```

Priority levels:

- **CRITICAL:** Risk of data loss (unpushed work, local-only branches).
- **HIGH:** Blocking work or significantly stale (abandoned PRs, failing compliance branches).
- **MEDIUM:** Maintenance needed but not urgent (branches behind, aging PRs).
- **LOW:** Housekeeping (stale branches, old drafts, minor divergence).

---

## /ai-git (No Arguments) — Full Report

When invoked without arguments, run all sub-commands in sequence and produce a combined report.

### Execution Order

1. **Fetch and prune** all remotes.
2. **Update default branch** reference.
3. **Run cleanup** (Steps 1-6 from `/ai-git cleanup`).
4. **Run health** (Checks 1-6 from `/ai-git health`).
5. **Generate combined recommendations.**

### Combined Report Format

```
Git Repository Report — <repo-name>
Generated: 2026-02-07 14:30 UTC
Default branch: main
Remotes: origin (github.com/org/repo)
════════════════════════════════════

CLEANUP SUMMARY
────────────────
Pruned tracking references:  4
Deleted merged branches:     7
Merged but diverged:         2 (review needed)
Unmerged branches:           3

HEALTH STATUS
─────────────
Unpushed work:               2 branches (CRITICAL)
Branches ahead of remote:    3
Stale branches (>30 days):   2
Compliance branches behind:  1 (develop, 3 behind main)
Open PRs:                    3 (1 active, 1 aging, 1 stale)

RECOMMENDATIONS
───────────────
1. CRITICAL: Push feature/search and bugfix/null-check to remote.
2. HIGH: PR #138 needs reviewer attention (14 days stale).
3. MEDIUM: Merge main into develop (3 commits behind).
4. MEDIUM: Review 2 merged-but-diverged branches for post-merge commits.
5. LOW: Clean up 2 stale branches (experiment/new-ui, spike/redis-cache).
6. LOW: Close or convert draft PR #135 (21 days, no activity).
```

---

## Protected Branches

The following branches are never deleted by cleanup operations:

- `main`, `master` — default branches
- `develop`, `development` — integration branches
- `staging`, `production` — environment branches
- `release/*` — release branches (only deleted after explicit release confirmation)
- `hotfix/*` — hotfix branches (only deleted after merge confirmation)
- The current branch (never delete the branch you are on)

If the project configures additional protected branch patterns, respect them.

---

## Safety Rules

These are hard constraints that cannot be overridden:

1. **Never force-delete branches.** Always use `git branch -d` (safe delete). If it fails because the branch is not merged, report it and let the user decide.
2. **Never auto-delete unmerged branches.** Unmerged work is sacred until the user explicitly confirms deletion.
3. **Never delete remote branches without confirmation.** Always present the list and get explicit approval.
4. **Never force-push.** This skill does not push to branches other than to delete merged remote branches.
5. **Never modify commit history.** No rebase, no squash, no amend. Those are separate operations requiring explicit user intent.
6. **Always fetch before analyzing.** Stale local state leads to wrong decisions. If fetch fails, note the limitation prominently.

---

## Error Recovery

| Failure                      | Action                                                                     |
| ---------------------------- | -------------------------------------------------------------------------- |
| Network error on fetch       | Warn user. Proceed with local-only analysis. Note limitation in report.    |
| Cannot detect default branch | Ask user to specify. Do not assume.                                        |
| Branch delete fails          | Report the error (likely unmerged). Skip and continue with other branches. |
| Remote branch delete fails   | Report the error (likely permissions). Skip and continue.                  |
| CLI not available (gh/az)    | Skip PR checks. Note in report that PR status was not checked.             |
| Not authenticated            | Skip remote operations. Note limitation.                                   |
| Empty repository             | Report "No branches to analyze" and stop.                                  |

---

## Enhanced Cleanup: Conflict Detection

When running cleanup or health, also check for potential merge conflicts between active branches:

```bash
# For each unmerged branch, check if it would conflict with the default branch
git merge-tree $(git merge-base <default-branch> <branch>) <default-branch> <branch> 2>/dev/null
```

Report branches with potential conflicts:

```
Potential merge conflicts:
  feature/auth vs main — conflicts in: src/config/env.ts, src/app.ts
  feature/search vs main — clean merge expected
  Recommendation: Rebase feature/auth onto main to resolve conflicts early.
```

---

## Learning Capture (on completion)

If during execution you discovered something useful for the project:

1. **New pattern** (e.g., branching convention, branch naming) → Propose adding to `knowledge/patterns.md`
2. **Recurring error** (e.g., branches always stale from same author) → Propose adding to `knowledge/anti-patterns.md`
3. **Lesson learned** (e.g., specific branches should be protected) → Propose adding to `knowledge/learnings.md`

Ask the user before writing to these files. Never modify them silently.

---

## What This Skill Does NOT Do

- It does not create branches. Use standard git commands or other skills for that.
- It does not merge branches. Merging is a deliberate action requiring user intent.
- It does not rebase or squash. History modification is never automatic.
- It does not push code changes. It only pushes branch deletions (with confirmation).
- It does not resolve merge conflicts. That requires human judgment.
- It does not modify any files in the working tree. It operates only on git metadata.
