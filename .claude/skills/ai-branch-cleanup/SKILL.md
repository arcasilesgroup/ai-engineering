---
name: ai-branch-cleanup
description: "Cleans branches safely: switches to the default branch, prunes merged and squash-merged branches, syncs to remote, sweeps stale specs, rotates `.ai-engineering/runtime/` per retention policy. Trigger for 'tidy up', 'tidy branches', 'sync to main', 'delete old branches', 'start fresh', 'rotate runtime'. Auto-invoked by /ai-pr after merge. Not for committing changes; use /ai-commit instead. Not for code-level dead-code removal; use /ai-simplify instead."
effort: cheap
model_tier: haiku
argument-hint: "--branches|--sync|--specs|--runtime|--consolidate-spec <slug>|--all"
tags: [git, branch, cleanup, hygiene, status, delivery]
requires:
  bins:
  - git
---


# Branch Cleanup

## Quick start

```
/ai-branch-cleanup              # full: sync + branch cleanup + spec sweep + runtime rotate + report
/ai-branch-cleanup --sync       # sync to default branch only
/ai-branch-cleanup --branches   # branch cleanup only
/ai-branch-cleanup --specs      # spec lifecycle sweep + _history.md rotation
/ai-branch-cleanup --runtime    # rotate .ai-engineering/runtime/ per retention policy
/ai-branch-cleanup --consolidate-spec <slug>   # delete finalised spec, append _history row
```

Full repository hygiene: safely migrate to the default branch, delete merged and squash-merged branches, rotate runtime artifacts, and produce a per-branch status report. No destructive operations without confirmation.

## When to Use

- Session start, after merging PRs, between tasks, before `/ai-brainstorm`.
- NOT for committing -- use `/ai-commit`.

## Process

Default (no flags) is equivalent to `--all`: runs sync, branch cleanup, and report.

### Phase 0a: Instinct consolidation (default / `--all`, fail-open)

0. **Consolidate session learnings BEFORE switching branches** -- if
   `.ai-engineering/observations/observations.yml` exists, run
   `/ai-session-watch --review` to fold this session's observations
   (especially the LLM-only `corrections` family) into the corpus. This
   closes the no-commit/no-PR gap: a session that ends at tidy-up time —
   without a `/ai-commit` or `/ai-pr` having run `--review` — still
   consolidates its learnings instead of losing them. Skip silently when
   the file is absent (fail-open) or when a single-purpose flag
   (`--branches` / `--sync` / `--specs` / `--runtime` /
   `--consolidate-spec`) was passed without `--all`. Mirrors the
   `/ai-pr` Step 2 and `/ai-commit` Step 2 gate.

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

### Phase 5: Spec consolidation (`--specs` or `--all`)

First **reconcile merged-but-unshipped specs**, then **consolidate** — `ai-eng cleanup specs` runs both verbs in order (`reconcile_merged` then `consolidate_shipped`). The composite phase ORDER is unchanged (the D-161-04 fix is gh-aware classification, NOT resequencing). The reconcile pass (`python .ai-engineering/scripts/spec_lifecycle.py reconcile_merged`) is the D-153-03 backstop: for any non-terminal sidecar (DRAFT/APPROVED/IN_PROGRESS), it classifies merge state primarily via `gh` PR state (`gh pr list --head <branch> --state merged`), which SURVIVES the Phase-1 branch prune; the local-ref check (`git branch --merged` + squash-merge emptiness) is the FALLBACK when `gh` is absent. On a merged classification it resolves the PR via `gh` and calls `mark_shipped` — catching specs merged via the GitHub UI that `/ai-pr` never marked, including those whose local branch Phase 1 already deleted. Then `python .ai-engineering/scripts/spec_lifecycle.py consolidate_shipped` appends the canonical 7-col `_history.md` row for any SHIPPED record (including the ones reconcile just marked) and emits the `framework_operation` audit event. **Verification-only step** — actual lifecycle writes live in `spec_lifecycle.py`; this skill calls the entry point. Idempotent: already-SHIPPED records are a no-op. **Fail-open**: missing script or locked sidecar logs and continues. See `.claude/skills/_shared/consolidate-spec.md` for the shared handler; the `--consolidate-spec <slug>` flag exposes the explicit post-merge action via `spec_lifecycle.py mark_shipped`.

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
/ai-branch-cleanup              # full: sync + branch cleanup + spec sweep + runtime rotate + report
/ai-branch-cleanup --sync       # sync to default branch only
/ai-branch-cleanup --branches   # branch cleanup only (no migration)
/ai-branch-cleanup --specs      # spec lifecycle sweep + _history.md rotation (DRAFT > 14d → ABANDONED; SHIPPED → row appended)
/ai-branch-cleanup --runtime    # runtime rotation only
/ai-branch-cleanup --consolidate-spec <slug>  # manual spec consolidation via _shared/consolidate-spec.md
/ai-branch-cleanup --all        # explicit full cleanup
```

### Phase 6: Spec consolidation (`--consolidate-spec`)

When invoked with `--consolidate-spec <slug>`, read `.claude/skills/_shared/consolidate-spec.md` and execute the shared handler: resolve the spec record, append/upsert the `_history.md` row via `spec_lifecycle.py mark_shipped`, clear `.ai-engineering/specs/spec.md` and `plan.md` to placeholders. Fail-open on missing script.

## Common Mistakes

- Force-pulling when ff-only fails -- STOP and resolve manually.

## Examples

### Example 1 — full hygiene at session start

User: "tidy up before I start a new task"

```
/ai-branch-cleanup
```

Switches to `main`, ff-pulls, prunes merged + squash-merged branches, sweeps stale spec drafts, prints the per-branch report.

### Example 2 — branches only after a long session

User: "just clean up old branches, leave the specs alone"

```
/ai-branch-cleanup --branches
```

Skips sync and spec sweep; runs branch classification + delete + report only.

## Integration

Called by: `/ai-pr` (auto after merge), `/ai-start` (session bootstrap). Calls: `/ai-session-watch --review` (Phase 0a, fail-open instinct consolidation), `git`, `python .ai-engineering/scripts/spec_lifecycle.py sweep`, `python .ai-engineering/scripts/runtime_rotate.py`. See also: `/ai-brainstorm` (run before new spec), `/ai-simplify` (code-level cleanup).

## References

- `.ai-engineering/manifest.yml` -- protected branch rules.
- `.claude/skills/ai-brainstorm/SKILL.md` -- spec creation composes cleanup.
$ARGUMENTS
