---
name: cleanup
description: "Full repository hygiene: status snapshot, sync, prune, and branch cleanup; use at session start, after merging PRs, between tasks, or before /create-spec."
metadata:
  version: 3.0.0
  tags: [git, branch, cleanup, hygiene, status]
  ai-engineering:
    requires:
      bins: [git]
    scope: read-write
    token_estimate: 1200
---

# Repository Cleanup Workflow

## Purpose

Execute full repository hygiene — branch cleanup and remote status assessment. The single session-start primitive for the framework. Replaces the former `/pre-implementation` flow (which was absorbed into `/cleanup` + `/create-spec`).

## Trigger

- Command: `/cleanup`.
- Context: after merging a pull request, between tasks, at session start, or when preparing for `/create-spec`.

## Preconditions (MUST verify before proceeding)

- **Required binaries**: `git` — must be available on PATH.
- Abort with remediation guidance if missing. Run `ai-eng doctor --fix-tools` to auto-install.

## Procedure

### Phase 0: Status

1. **Repository health snapshot** — run `uv run ai-eng maintenance repo-status`. Do NOT use ad-hoc shell commands for branch analysis — the CLI handles stale detection, ahead/behind, and PR listing in Python, avoiding zsh escaping issues with `!=` operators.
   - Remote branches: list with ahead/behind relative to default branch.
   - Open PRs: list via VCS CLI (GitHub: `gh pr list`, Azure DevOps: `az repos pr list`; graceful fallback if neither available).
   - Stale branches: branches with no commits in >30 days.
   - Cleanup candidates: merged + stale branches.
2. **Display status** — the CLI renders a Markdown summary automatically.
3. **Informational only** — this phase does not block subsequent phases.

### Phase 1: Sync

4. **Identify base branch** — determine the default branch (`main` or `master`).
5. **Check working tree** — if dirty, warn and stop. Do not stash automatically.
6. **Switch to base** — `git checkout <base-branch>`.
7. **Pull latest** — `git pull --ff-only origin <base-branch>`.

### Phase 2: Prune

8. **Fetch and prune** — `git fetch --prune origin` to remove stale remote-tracking references.

### Phase 3: Cleanup

9. **Run branch cleanup** — `uv run ai-eng maintenance branch-cleanup`.
   - Deletes branches fully merged into base (`git branch -d`).
   - Deletes squash-merged branches whose remote is `[gone]` (`git branch -D`).
   - Excludes protected branches (`main`, `master`).
   - Reports: branches deleted (merged), branches deleted (gone), refs pruned, branches skipped.

## Examples

### Example 1: Session-start hygiene

User says: "Run /cleanup before I start the next task."
Actions:

1. Capture repo status snapshot, then sync base branch and prune remote references.
2. Run branch cleanup and report deleted, skipped, and protected branches.
   Result: Repository is synchronized and cleaned for the next governed workflow.

## Output Contract

- Terminal output showing each phase result.
- Phase 0: repository status snapshot (remote branches, PRs, stale, candidates).
- Phase 3: branch cleanup summary (deleted count, pruned count, skipped count).
- Final confirmation: current branch and status.

## Governance Notes

- Protected branches (`main`, `master`) are never deleted.
- Only `git branch -d` (safe delete) for merged branches; `git branch -D` (force) only for `[gone]` branches whose remote was already deleted.
- No destructive git operations beyond branch deletion.
- No `--no-verify` usage.
- If `git pull --ff-only` fails (diverged history), warn and stop — do not force-pull.
- Spec reset (archival + `_active.md` clearing) has been moved to `/pr` so changes reach origin through the PR.

## References

- `skills/spec/SKILL.md` — spec creation that composes `/cleanup` before branch creation.
- `standards/framework/core.md` — protected branch rules and enforcement.
