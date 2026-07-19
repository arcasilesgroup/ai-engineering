---
name: ai-session-watch-sweep
description: "Consolidates the session-watch observation backlog on demand: runs /ai-session-watch --review, gates the result, and opens a draft chore PR for human review. Trigger for 'run the observation sweep', 'consolidate observations', 'session-watch sweep'. Never auto-merges, never auto-files work items, never runs unattended. Not for interactive review; use /ai-session-watch --review instead."
effort: cheap
argument-hint: "[--dry-run] [--no-pr]"
tags: [meta, session-watch]
---

# Session-Watch Sweep

Consolidates the session-watch observation backlog on demand — runs
`/ai-session-watch --review`, gates the result, and opens a draft chore PR for
human review. Use it to clear accumulated corrections; it never auto-merges,
auto-files work items, or runs unattended.

## Purpose

The session-watch `corrections` loop consolidates only when a human runs
`/ai-session-watch --review` — no reliable trigger, so operator corrections
accumulate unconsolidated (spec-165). This is a manual wrapper: run the review,
gate the result, open a **draft chore PR** so a human reviews consolidated
lessons before merge (keeps consolidation off feature branches). No scheduler —
an operator runs it; the SessionStart observation-nudge (spec-165 D-165-03)
surfaces the pending backlog.

## Hard Rules

- Never auto-merge — the PR is always `--draft`.
- Never auto-file work items — run `--review`'s extract → enrich → write steps only; the human decides what becomes an issue from the PR (spec-165 D-165-04). Unattended issue filing is forbidden.
- No corpus change → exit cleanly with a status event; never open an empty PR.

## Process

**Step 1 — Run the review (work-item creation suppressed).**
Invoke `/ai-session-watch --review`, running only steps 1-3 (extract → enrich →
write) plus the `lastReviewedAt` stamp; SKIP step 5 (create work items) —
D-165-04. If `observations.yml` is unchanged after the review, emit a
`framework_operation` event with `operation=session_watch_sweep_no_op` and
exit 0.

**Step 2 — Gate the diff.**
If the corpus changed, run the standard pre-commit gate locally:

```bash
ai-eng gate run --cache-aware --json --mode=local
```

On failure, emit `operation=session_watch_sweep_gate_failed` with the failure
summary and exit 1 — never open a PR with a broken corpus.

**Step 3 — Commit + open draft chore PR.**

```bash
/ai-commit "chore(session-watch-sweep): observation consolidation"
/ai-pr --draft --title "chore(session-watch-sweep): observation consolidation" --body "Manual session-watch consolidation. Review the consolidated corrections before merge. No work items were auto-filed (spec-165 D-165-04) — file any that warrant tracking."
```

The PR commits `observations.yml` (the tracked corpus). `meta.json` and
`observation-events.ndjson` are gitignored and stay out of the PR.

## Telemetry

Each run emits one `framework_operation` event:

| operation | when |
|-----------|------|
| `session_watch_sweep_started` | at invocation |
| `session_watch_sweep_no_op` | no corpus change, no PR opened |
| `session_watch_sweep_gate_failed` | corpus changed but gate refused |
| `session_watch_sweep_pr_opened` | happy path, includes `pr_url` |

## Common Mistakes

- Running more frequently than weekly — sub-weekly runs flood reviewers with noisy PRs (auto-merge and auto-file are already barred by Hard Rules; D-164 board-spam risk).

## Examples

User: "run the weekly observation sweep on this repo"

```
/ai-session-watch-sweep
```

Runs `/ai-session-watch --review` (work-items suppressed), gates the corpus
change, and opens a draft PR titled `chore(session-watch-sweep): observation
consolidation`. Add `--dry-run` to print the consolidated corpus diff without
staging a commit or PR — a scope preview before a full run.

## Integration

Called by: operator manually (or surfaced by the SessionStart
observation-nudge). Calls: `/ai-session-watch --review` (work-items
suppressed), `/ai-commit`, `/ai-pr --draft`. See also: `/ai-simplify-sweep`
(the sibling manual sweep this mirrors), `/ai-session-watch` (interactive
review).

- Telemetry: `framework_operation` events aggregated from `framework-events.ndjson`.

## References

- Related: `.claude/skills/ai-session-watch/SKILL.md`, `.claude/skills/ai-simplify-sweep/SKILL.md`
- Manifest entry: `.ai-engineering/manifest.yml` `skills.registry.ai-session-watch-sweep`
