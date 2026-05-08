---
name: ai-cleanup
description: "Tidies the repository safely: switches to default branch, prunes merged and squash-merged branches, syncs to remote, sweeps stale specs, rotates `.ai-engineering/runtime/` per retention policy. Trigger for 'tidy up', 'clean up branches', 'sync to main', 'delete old branches', 'start fresh', 'rotate runtime'. Auto-invoked by /ai-pr after merge. Not for committing changes; use /ai-commit instead. Not for code-level dead-code removal; use /ai-simplify instead."
effort: medium
argument-hint: "--branches|--sync|--specs|--runtime|--all"
tags: [git, branch, cleanup, hygiene, status, delivery]
requires:
  bins:
  - git
---


# Repository Cleanup

## Quick start

```
/ai-cleanup              # full: sync + branch cleanup + spec sweep + runtime rotate + report
/ai-cleanup --sync       # sync to default branch only
/ai-cleanup --branches   # branch cleanup only
/ai-cleanup --specs      # spec lifecycle sweep
/ai-cleanup --runtime    # rotate .ai-engineering/runtime/ per retention policy
```

Full repository hygiene: safely migrate to the default branch, delete merged and squash-merged branches, rotate runtime artifacts, and produce a per-branch status report. No destructive operations without confirmation.

## When to Use

- Session start, after merging PRs, between tasks, before `/ai-brainstorm`.
- NOT for committing -- use `/ai-commit`.

## Process

Default (no flags) is equivalent to `--all`: runs sync, branch cleanup, and report.

### Phase 0: Safe Migration (`--sync` or `--all`)

1. **Detect default branch** -- `git symbolic-ref refs/remotes/origin/HEAD` (main or master).
2. **Record current branch** for the report.
3. **Auto-stash if dirty** -- `git stash push -m "cleanup-auto-stash-$(date +%s)"`.
4. **Switch to default** -- `git checkout <default>`.
5. **Pull latest** -- `git pull --ff-only origin <default>`. If ff-only fails: WARN and STOP.
6. **Restore stash** -- `git stash pop`. If conflict: WARN, leave stash, continue cleanup.

### Phase 1: Branch Analysis (`--branches` or `--all`)

7. **Fetch and prune** -- `git fetch --prune origin`.
8. **Enumerate** all local branches (excluding `main`, `master`).
9. **Classify each branch**:

| Category | Criteria | Action |
|----------|----------|--------|
| Merged | In `git branch --merged <default>` | Delete (`git branch -d`) |
| Squash-merged | Not in `--merged` but `git diff <default>..<branch>` is empty | Delete (`git branch -D`) |
| Gone (safe) | Tracking ref `[gone]` AND no content diff | Delete (`git branch -D`) |
| Gone (has dev) | Tracking ref `[gone]` BUT has content diff | KEEP |
| Active | Has remote tracking, not merged | KEEP |
| Local only | No remote, has commits ahead | KEEP |

10. **Delete eligible** -- merged with `-d`, squash-merged and gone-safe with `-D`.

### Phase 3: Spec sweep (`--specs` or `--all`)

Reap stale spec drafts so the lifecycle ledger does not accumulate
abandonware. Invoke `python .ai-engineering/scripts/spec_lifecycle.py sweep`:
DRAFTs older than 14 days move to ABANDONED; counts are returned as JSON
and emitted as a `framework_operation` audit event. **Fail-open**: a missing
script or locked sidecar logs and continues — branch cleanup is the
load-bearing hot path here.

### Phase 4: Runtime rotation (`--runtime` or `--all`)

Rotate `.ai-engineering/runtime/` so transient observability data does
not bloat the working tree. Invoke
`python .ai-engineering/scripts/runtime_rotate.py`:

| Subtree                           | Retention          | Action      |
|-----------------------------------|--------------------|-------------|
| `runtime/tool-outputs/*.txt`      | 7 days             | unlink      |
| `runtime/autopilot/sub-*`         | 30 days            | rmtree      |
| `runtime/tool-history.ndjson`     | 10000 lines / 5 MB | tail-truncate |

Hot-path budget <100 ms; stdlib only; idempotent; fail-open on missing
dirs; emits a `runtime-rotate` `framework_event` per run.

### Phase 2: Status Report

11. **Build per-branch table**:

```markdown
## Repository Cleanup Report

**Default branch**: `main` (up to date)
**Previous branch**: `feat/old-feature`
**Working tree**: clean | stash restored | stash pending

| Branch | Action | Reason | Remote | Ahead/Behind |
|--------|--------|--------|--------|--------------|
| `feat/done` | DELETED | Merged | -- | -- |
| `feat/squashed` | DELETED | Squash-merged | -- | -- |
| `feat/active` | KEPT | Unmerged (5 commits) | origin/feat/active | +5/-2 |
```

## Quick Reference

```
/ai-cleanup              # full: sync + branch cleanup + spec sweep + runtime rotate + report
/ai-cleanup --sync       # sync to default branch only
/ai-cleanup --branches   # branch cleanup only (no migration)
/ai-cleanup --specs      # spec lifecycle sweep only (DRAFT > 14d → ABANDONED)
/ai-cleanup --runtime    # runtime rotation only
/ai-cleanup --all        # explicit full cleanup
```

## Common Mistakes

- Force-pulling when ff-only fails -- STOP and resolve manually.

## Examples

### Example 1 — full hygiene at session start

User: "tidy up before I start a new task"

```
/ai-cleanup
```

Switches to `main`, ff-pulls, prunes merged + squash-merged branches, sweeps stale spec drafts, prints the per-branch report.

### Example 2 — branches only after a long session

User: "just clean up old branches, leave the specs alone"

```
/ai-cleanup --branches
```

Skips sync and spec sweep; runs branch classification + delete + report only.

## Integration

Called by: `/ai-pr` (auto after merge), `/ai-start` (session bootstrap). Calls: `git`, `python .ai-engineering/scripts/spec_lifecycle.py sweep`, `python .ai-engineering/scripts/runtime_rotate.py`. See also: `/ai-brainstorm` (run before new spec), `/ai-simplify` (code-level cleanup).

## References

- `.ai-engineering/manifest.yml` -- protected branch rules.
- `.claude/skills/ai-brainstorm/SKILL.md` -- spec creation composes cleanup.
$ARGUMENTS
