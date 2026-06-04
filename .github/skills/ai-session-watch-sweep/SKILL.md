---
name: ai-session-watch-sweep
description: "Consolidates the session-watch observation backlog on a schedule: runs /ai-session-watch --review, gates the result, and opens a draft chore PR for human review. Trigger for 'weekly observation sweep', 'scheduled consolidation', 'consolidate observations on a cadence', 'session-watch sweep'. Never auto-merges, never auto-files work items. Not for interactive review; use /ai-session-watch --review instead."
effort: cheap
argument-hint: "[--dry-run] [--no-pr]"
mode: agent
tags: [meta, session-watch, scheduled, autonomous]
model_tier: haiku
mirror_family: copilot-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-session-watch-sweep/SKILL.md
edit_policy: generated-do-not-edit
---


# Session-Watch Sweep

## Purpose

The session-watch `corrections` loop only consolidates when a human runs
`/ai-session-watch --review` — it has no reliable trigger, so operator
corrections accumulate unconsolidated (spec-165). This skill is a scheduled
wrapper that runs the review on a cadence, gates the result, and opens a
**draft chore PR** so a human reviews the consolidated lessons before merge —
keeping consolidation off feature branches.

## When to Use

- Weekly automated consolidation pass (recommended cadence).
- Before a release-cut to capture accumulated session lessons.
- NOT for interactive review — that should call `/ai-session-watch --review`
  directly (which keeps work-item creation).

## Hard Rules

- Never auto-merge. The PR is always opened with `--draft`.
- Never auto-file work items. The sweep runs `--review`'s extract → enrich →
  write steps only; the human decides what becomes an issue from the PR
  (spec-165 D-165-04). Unattended issue filing is forbidden.
- If the review produces no corpus change, exit cleanly with a status event;
  do NOT open an empty PR.

## Process

### Step 1 — Run the review (work-item creation suppressed)

Invoke the consolidation in non-interactive mode:

```
/ai-session-watch --review
```

Run only steps 1-3 (extract → enrich → write) plus the `lastReviewedAt`
stamp; SKIP step 5 (create work items) — D-165-04. If `observations.yml`
is unchanged after the review, emit a `framework_operation` event with
`operation=session_watch_sweep_no_op` and exit 0.

### Step 2 — Gate the diff

If the corpus changed, run the standard pre-commit gate locally:

```bash
ai-eng gate run --cache-aware --json --mode=local
```

If the gate fails, emit `operation=session_watch_sweep_gate_failed` with the
failure summary and exit 1 — do NOT open a PR with a broken corpus.

### Step 3 — Commit + open draft chore PR

```bash
/ai-commit "chore(session-watch-sweep): scheduled observation consolidation"
/ai-pr --draft --title "chore(session-watch-sweep): observation consolidation" --body "Automated weekly session-watch consolidation. Review the consolidated corrections before merge. No work items were auto-filed (spec-165 D-165-04) — file any that warrant tracking."
```

The PR commits `observations.yml` (the tracked corpus). `meta.json` and
`observation-events.ndjson` are gitignored and stay out of the PR.

## Scheduling

Recommended invocation pattern (run once to register the routine):

```
/schedule weekly /ai-session-watch-sweep
```

This skill does NOT auto-create the cron entry — that requires user
authorization via `/ai-schedule`. Operators register the routine after
reviewing the skill behaviour. Until it is registered, the SessionStart
observation-nudge (spec-165 D-165-03) is the safety net that surfaces the
pending backlog.

## Telemetry

Each run emits one of:

- `framework_operation` `operation=session_watch_sweep_started` — at invocation.
- `framework_operation` `operation=session_watch_sweep_no_op` — no corpus change, no PR opened.
- `framework_operation` `operation=session_watch_sweep_gate_failed` — corpus changed but gate refused.
- `framework_operation` `operation=session_watch_sweep_pr_opened` — happy path, includes `pr_url`.

## Common Mistakes

- Auto-merging the resulting PR. The skill MUST open a draft; merge requires a human.
- Auto-filing work items in the unattended run. Suppressed by design (D-164 board-spam risk).
- Scheduling more frequently than weekly. Sub-weekly cadence floods reviewers with noisy PRs.

## Examples

### Example 1 — manual weekly run

User: "run the weekly observation sweep on this repo"

```
/ai-session-watch-sweep
```

Runs `/ai-session-watch --review` (work-items suppressed), gates the corpus
change, and opens a draft PR titled `chore(session-watch-sweep): observation consolidation`.

### Example 2 — dry-run before scheduling

User: "preview what the observation sweep would consolidate this week"

```
/ai-session-watch-sweep --dry-run
```

Runs the review and prints the consolidated corpus diff without staging a
commit or PR — useful for reviewing scope before enabling a cron entry.

## Integration

Called by: `/ai-schedule` (weekly cron) or operator manually. Calls:
`/ai-session-watch --review` (work-items suppressed), `/ai-commit`,
`/ai-pr --draft`. See also: `/ai-simplify-sweep` (the sibling scheduled
sweep this mirrors), `/ai-session-watch` (interactive review).

- Telemetry: `framework_operation` events aggregated from `framework-events.ndjson`.

## Scheduled cadence

The schedule layer should call the deterministic wrapper, not the slash
command directly:

```
0 4 * * 2   <project>/.ai-engineering/scripts/scheduled/session-watch-sweep.sh
```

The wrapper resolves `$AIENG_PROJECT_ROOT` (or falls back to
`git rev-parse --show-toplevel`) and emits a `framework_operation` event
(`operation=session_watch_sweep_scheduled_run`) with
`outcome=success|failure|skipped` for every cycle. Never auto-merges; PR
opening stays the responsibility of the slash-command path.

Activate via `/ai-schedule weekly <project>/.ai-engineering/scripts/scheduled/session-watch-sweep.sh` or copy the cron line above into your scheduler.

## References

- Skill source of truth: `.github/skills/ai-session-watch-sweep/SKILL.md`
- Related: `.github/skills/ai-session-watch/SKILL.md`, `.github/skills/ai-simplify-sweep/SKILL.md`
- Manifest entry: `.ai-engineering/manifest.yml` `skills.registry.ai-session-watch-sweep`
- Scheduled wrapper: `.ai-engineering/scripts/scheduled/session-watch-sweep.sh`
