---
description: "Audits git repository health, auto-cleans 100% safe branches, and reports detailed analysis for branches requiring engineer decisions"
tools: [Bash, Read, Glob, Grep]
---

## Objective

Perform a comprehensive audit of the git repository state across local and remote. Auto-delete branches that are 100% safe to remove (communicate what was deleted and why). For everything else, produce a rich analysis with purpose, risk, trade-offs, and suggested actions so engineers have full context to make decisions. Works with both GitHub and Azure DevOps.

## Process

### 1. Detect Environment

- Verify git repository: `git rev-parse --is-inside-work-tree`
- Detect the **default branch** using multiple strategies:
  1. `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'`
  2. Fallback: check `refs/remotes/origin/main`, then `refs/remotes/origin/master`
  3. Platform CLI: `gh repo view --json defaultBranchRef` or `az repos show --query defaultBranch`
- Detect **platform** from remote URL: `github.com` → GitHub, `dev.azure.com`/`visualstudio.com` → Azure DevOps
- Verify platform CLI availability (`gh --version` or `az --version`)
- Fetch latest remote state: `git fetch --all --prune`

### 2. Identify All Branches

**List and classify every branch:**

For each local branch:
- Get name, last commit date, last commit message, tracking status
- Classify as compliance branch if it matches: `main`, `master`, `develop`, `dev/*`, `release/*`, `hotfix/*`
- Check if remote tracking branch exists or is gone
- Check if fully merged into the default branch: `git merge-base --is-ancestor <branch> $DEFAULT_BRANCH`
- If merged, check for post-merge commits: `git rev-list <merge-base>..<branch> --count`

For each remote branch (not already tracked locally):
- Get name, last commit date
- Check if merged into the default branch

### 3. Auto-Clean Safe Branches

A branch is **100% safe to delete** when ALL of these are true:
- It is NOT a compliance branch (main, master, develop, dev/*, release/*, hotfix/*)
- It is NOT the current branch
- It IS fully merged into the default branch (or its target compliance branch)
- It has ZERO commits after the merge point
- Its remote tracking reference is gone (PR was completed and branch deleted in platform)

For each safe branch:
- Delete with `git branch -d "$BRANCH"` (safe delete only, never `-D`)
- Record: branch name, why it was safe, what the branch was for (infer from branch name prefix and last commit messages)

### 4. Analyze Branches Requiring Decisions

For each branch that is NOT 100% safe to delete, produce a detailed analysis:

**Branch purpose:** Infer from the branch name prefix and commit messages:
- `feature/*` → "Feature: [description from commits]"
- `fix/*` or `bugfix/*` → "Bug fix: [description from commits]"
- `chore/*` → "Maintenance: [description from commits]"
- Read the last 3 commit messages: `git log -3 --format="%s" <branch>`

**Current state:**
- Merged / unmerged into the default branch
- Ahead / behind remote (if tracking exists)
- Last activity: date and age in days
- Number of unique commits not in the default branch

**Target branch:** Which compliance branch this should merge into:
- By default: the default branch
- If branch name starts with `hotfix/*` → may target a release branch
- If `develop` exists → feature branches may target develop

**Risk if deleted:**
- If unmerged: "Would lose X commits not in any compliance branch" — list the commit subjects
- If merged with post-merge commits: "Would lose X post-merge commits" — list them
- If fully merged, no post-merge: "No risk, all changes are in the default branch"

**Risk if kept:**
- If stale (>30 days): "Stale branch cluttering the repo, last activity X days ago"
- If active: "Active development, should not be touched"
- If merged with post-merge: "May cause confusion — appears merged but has new work"

**Suggested action:** One of:
- "Delete locally" — safe, all work is merged
- "Delete locally and remotely" — safe, PR merged, no new work
- "Push to remote" — has local-only commits that may be lost
- "Create PR to [target branch]" — unmerged work that should be reviewed
- "Rebase on [default branch]" — branch is behind and may have conflicts
- "Review with team" — complex state requiring human judgment
- "Close and archive" — stale work that is likely abandoned

**Trade-offs:** What you gain vs. lose with each action option.

### 5. Check Compliance Branch Health

For each compliance branch present in the repo:

- **Default branch:** baseline, always up to date by definition
- **develop:** Check commits behind/ahead of default branch. Report divergence.
- **release/*:** Check if merged back into default after release completion. Flag if stale.
- **hotfix/*:** Check if merged into both default and develop (if exists). Flag if orphaned.
- **dev/*:** Check sync status with default branch.

Report any compliance branches that are diverged, behind, or out of sync.

### 6. Check Open PR Status

**GitHub:**
```bash
gh pr list --state open --json number,title,author,createdAt,reviewDecision,isDraft,headRefName,baseRefName
```

**Azure DevOps:**
```bash
az repos pr list --status active --top 50 --output json
```

Classify each PR:
- **Needs review:** No reviews yet, open > 2 days
- **Stale:** No activity > 7 days
- **Changes requested:** Review returned with changes, not yet addressed
- **Draft abandoned:** Draft PR with no activity > 14 days
- **Ready to merge:** Approved, all checks pass (if detectable)

For each PR: state the age, status, target branch, and what action the engineer should take.

If platform CLI is not available, skip PR checks with a note explaining how to install.

### 7. Cross-Reference

- Match local branches to open PRs (by branch name)
- Identify branches with open PRs that should not be deleted
- Identify branches with no PR (unpushed or PR not created)
- Identify PRs whose source branch has been deleted (orphaned PRs)

### 8. Report

    ## Git Hygiene Report

    **Timestamp:** <current datetime>
    **Platform:** GitHub | Azure DevOps | Unknown (PR checks skipped)
    **Default branch:** <detected name>
    **Total local branches:** X
    **Total remote branches:** Y
    **Open PRs:** Z

    ### Auto-cleaned (safe deletions performed)
    | Branch | Last Purpose | Reason Safe |
    |--------|-------------|-------------|
    | feature/done-thing | Feature: added user auth (3 commits) | Fully merged, remote gone, no post-merge commits |
    | fix/resolved-bug | Bug fix: fixed null ref in login | Fully merged, remote gone, no post-merge commits |

    **X branches safely deleted.**

    ### Branches Requiring Decision

    | Branch | Purpose | State | Target | Suggested Action | Risk if Deleted |
    |--------|---------|-------|--------|-----------------|----------------|
    | feature/wip | Feature: user dashboard | Merged + 2 post-merge commits | main | Review post-merge commits, then create new PR | Would lose 2 commits |
    | feature/old | Feature: API v2 refactor | Unmerged, stale (45d) | main | Review with team or close & archive | Would lose 8 commits |
    | fix/pending | Bug fix: timeout issue | Unmerged, active (2d) | main | Create PR | Would lose 3 commits |

    #### Detailed Analysis

    **feature/wip** — Feature: user dashboard
    - Created from: main (inferred)
    - Commits: 5 total, 3 merged into main, 2 post-merge
    - Post-merge commits: "add dashboard filters", "fix chart rendering"
    - Last activity: 3 days ago
    - Risk if deleted: Would lose 2 commits not in main
    - Risk if kept: May cause confusion — branch appears merged but has new work
    - **Suggested:** Review the 2 post-merge commits. If they should be in main, create a new PR. If they were experimental, delete the branch.
    - **Trade-off:** Keeping it preserves work-in-progress; deleting it risks losing unmerged changes

    (... similar analysis for each branch ...)

    ### Compliance Branch Status
    | Branch | State | Behind Default | Ahead of Default | Action Needed |
    |--------|-------|---------------|-----------------|---------------|
    | develop | diverged | 5 commits | 3 commits | Sync with default branch |
    | release/v1.1 | merged | 0 | 0 | Safe to delete after verification |

    ### Open PRs Needing Attention
    | PR | Title | Target | Age | Status | Suggested Action |
    |----|-------|--------|-----|--------|-----------------|
    | #42 | Add user login | main | 8 days | Needs review | Request review from team |
    | #38 | Fix auth timeout | main | 3 days | Changes requested | Address reviewer feedback |
    | #35 | Draft: API refactor | main | 16 days | Stale draft | Complete or close |

    ### Summary
    - **X** branches safely auto-cleaned
    - **X** branches need engineer decision
    - **X** compliance branches checked (Y need attention)
    - **X** open PRs need attention

## Success Criteria

- Default branch detected dynamically (never hardcoded)
- All local and remote branches analyzed with accurate status
- Only 100% safe branches were auto-deleted (merged, no post-merge commits, remote gone)
- Every auto-deletion is communicated with branch name, purpose, and safety reason
- Non-safe branches have detailed analysis: purpose, risk, trade-offs, and suggested action
- Compliance branches are NEVER auto-deleted, only audited
- Open PRs retrieved and classified (if platform CLI available)
- Cross-reference between branches and PRs is correct
- Report is actionable with specific names and clear recommendations

## Constraints

- NEVER use `git branch -D` (force delete) — only `git branch -d` (safe delete)
- NEVER delete compliance branches (main, master, develop, dev/*, release/*, hotfix/*)
- NEVER delete the current branch
- NEVER delete a branch that has unmerged commits
- NEVER delete a branch that has post-merge commits (report it instead)
- NEVER push or modify commits — only delete branches that are fully merged
- If platform CLI is not available, skip PR checks gracefully (do not fail)
- Handle errors gracefully — if one branch analysis fails, continue with the rest
- Use macOS-compatible date commands (support both `date -v` and `date -d`)
