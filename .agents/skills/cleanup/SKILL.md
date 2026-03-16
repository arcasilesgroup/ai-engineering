---
name: cleanup
version: 4.2.0
description: 'Full repository hygiene: safe migration to default branch, aggressive
  branch cleanup, and rich per-branch status report.'
tags: [git, branch, cleanup, hygiene, status]
requires:
  bins: [git]
---

# Repository Cleanup

## Purpose

Execute full repository hygiene — safely migrate to the default branch, aggressively delete all branches that can be removed without compromising existing development, and produce a rich per-branch report so the user can assess repository health at a glance.

## Trigger

- Command: `/ai:cleanup`
- Context: session start, after merging PRs, between tasks, or before `/ai:spec`.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"cleanup"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## Preconditions

- **Required**: `git` on PATH. Abort with `ai-eng doctor --fix-tools` guidance if missing.

## Procedure

### Phase 0: Safe Migration to Default Branch

1. **Detect default branch** — `main` or `master` (check `git symbolic-ref refs/remotes/origin/HEAD`).
2. **Record current branch** — save current branch name for the report.
3. **Auto-stash if dirty** — if `git status --porcelain` shows changes:
   - `git stash push -m "cleanup-auto-stash-$(date +%s)"`.
   - Record that a stash was created.
4. **Switch to default** — `git checkout <default>`.
5. **Pull latest** — `git pull --ff-only origin <default>`.
   - If ff-only fails (diverged): WARN and STOP. Do not force-pull.
6. **Restore stash** (if created in step 3) — `git stash pop`.
   - If pop conflicts: WARN, leave stash intact (`git stash list` to show it), continue cleanup. User resolves manually after cleanup.

### Phase 1: Fetch, Prune & Branch Analysis

7. **Fetch and prune** — `git fetch --prune origin` to remove stale remote-tracking refs.
8. **Enumerate all local branches** (excluding protected: `main`, `master`).
9. **Classify each branch** into one of these categories:

| Category | Criteria | Action |
|----------|----------|--------|
| **Merged** | In `git branch --merged <default>` | Delete (`git branch -d`) |
| **Squash-merged** | NOT in `--merged`, but `git diff <default>..<branch>` (two dots, tip-to-tip) has no content diff — branch tip is identical to default | Delete (`git branch -D`) |
| **Gone (safe)** | Tracking ref is `[gone]` AND `git diff <default>..<branch>` has no content diff | Delete (`git branch -D`) |
| **Gone (has dev)** | Tracking ref is `[gone]` BUT has content diff vs default | KEEP — has unmerged local development |
| **Active (remote)** | Has remote tracking branch, not merged | KEEP — active development with remote |
| **Local only** | No remote tracking, has commits ahead of default, has content diff vs default | KEEP — local-only development |
| **Protected** | `main` or `master` | SKIP — never touched |

The **Squash-merged** check applies to all non-merged branches (local-only and gone) before classifying them as kept. Use `git diff <default>..<branch>` (two dots, tip-to-tip comparison) — if the output is empty, the branch content is already fully integrated into the default branch regardless of merge strategy (squash, rebase, or cherry-pick). Note: `git cherry -v` does NOT reliably detect squash merges because the squash commit gets a different patch-id than the original commits.

10. **Delete eligible branches** — merged with `-d`, gone-safe and squash-merged with `-D`.

### Phase 2: Rich Summary Report

11. **Build per-branch table** — for every local branch that existed (excluding protected), show:

```markdown
## Repository Cleanup Report

**Default branch**: `main` (up to date with origin)
**Previous branch**: `feat/old-feature`
**Working tree**: clean | stash restored | stash pending (conflict)

### Branch Detail

| Branch | Action | Reason | Remote Status | Ahead/Behind |
|--------|--------|--------|---------------|--------------|
| `feat/merged-feature` | DELETED | Merged into main | — | — |
| `feat/squash-merged` | DELETED | Squash-merged (all commits applied) | — | — |
| `feat/gone-no-diff` | DELETED | Remote deleted, no local diff | — | — |
| `feat/active-work` | KEPT | Unmerged development (5 commits) | `origin/feat/active-work` | +5 / -2 |
| `feat/local-experiment` | KEPT | Local-only development (3 commits) | no remote | +3 |
| `fix/gone-with-changes` | KEPT | Remote deleted, has local diff | gone | +2 |
```

12. **Display report** — render the full table in terminal output. This is the primary deliverable of cleanup.

## Post-condition

- Repo is on the default branch (`main` or `master`).
- Working tree is clean (or stash pending if pop conflicted).
- All safely deletable branches are gone.
- User has a clear per-branch report of what happened and why.

## Governance Notes

- Protected branches (`main`, `master`) are never deleted.
- Merged branches: `git branch -d` (safe — git refuses if not fully merged).
- Squash-merged branches: `git branch -D` ONLY if `git diff <default>..<branch>` (tip-to-tip) shows no content diff.
- Gone branches: `git branch -D` (force) ONLY if `git diff <default>..<branch>` shows no content diff. If there is a diff, the branch is kept.
- No `--no-verify` usage.
- If `git pull --ff-only` fails, WARN and STOP — do not force-pull or rebase.
- No destructive git operations beyond branch deletion of eligible branches.

## References

- `.agents/skills/spec/SKILL.md` — spec creation composes cleanup before branch creation.
- `standards/framework/core.md` — protected branch rules and enforcement.
