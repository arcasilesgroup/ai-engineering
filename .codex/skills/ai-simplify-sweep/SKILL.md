---
name: ai-simplify-sweep
description: Sweeps stale code complexity weekly via a scheduled /ai-simplify wrapper, gates the diff, and opens a draft PR for human review. Trigger for 'weekly simplify sweep', 'scheduled simplification', 'simplification sweep', 'simplify pass'. Never auto-merges. Not for in-flight feature work; use /ai-simplify instead. Not for security cleanup; use /ai-security instead.
effort: medium
argument-hint: "[--dry-run] [--no-pr]"
tags: [meta, simplification, scheduled, autonomous]
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-simplify-sweep/SKILL.md
edit_policy: generated-do-not-edit
---


# Simplify Sweep

## Purpose

Codebases accumulate entropy: dead branches, redundant guards, copy-pasted helpers, layers of indirection. `/ai-simplify` already exists to fight that, but it requires manual invocation and humans rarely remember. This skill is a scheduled wrapper that runs simplify on a cadence, gates the diff, and opens a draft PR so a human reviews the proposed reductions before merge.

## When to Use

- Weekly automated maintenance pass (recommended cadence).
- Before a release-cut to clear obvious simplifications.
- NOT for in-flight feature work — those should call `/ai-simplify` directly.

## Hard Rules

- Never auto-merge. The PR is always opened with `--draft`.
- Never run aggressive refactors. Conservative defaults only — guard clauses, early returns, dead-code removal, single-call-site inlines.
- If the simplify diff is empty, exit cleanly with a status event; do NOT open an empty PR.

## Process

### Step 1 — Invoke `/ai-simplify` in non-interactive mode

Read `.codex/skills/ai-simplify/SKILL.md` (when present) to confirm whether an explicit `--auto` flag exists. If not, invoke with conservative defaults equivalent to:

```
/ai-simplify --conservative
```

Capture the diff. If the diff is empty, emit a `framework_operation` event with `operation=entropy_gc_no_op` and exit 0.

### Step 2 — Gate the diff

If the diff is non-empty, run the standard pre-commit gate locally:

```bash
ai-eng gate run --cache-aware --json --mode=local
```

If the gate fails, emit `operation=entropy_gc_gate_failed` with the failure summary and exit 1 — do NOT open a PR with broken code.

### Step 3 — Commit + open draft PR

```bash
/ai-commit "chore(simplify-sweep): weekly automated simplification sweep"
/ai-pr --draft --title "chore(simplify-sweep): weekly simplification" --body "Automated weekly entropy sweep. Review the diff before merge."
```

The PR title and body explicitly mark this as an automated entropy GC pass so reviewers can apply lighter scrutiny than for feature PRs but still verify the simplifications preserve behaviour.

## Scheduling

Recommended invocation pattern (run once to register the routine):

```
/schedule weekly /ai-simplify-sweep
```

This skill does NOT auto-create the cron entry — that requires user authorization via `/ai-schedule`. Operators register the routine after reviewing the skill behaviour.

## Telemetry

Each run emits one of:

- `framework_operation` `operation=entropy_gc_started` — at invocation.
- `framework_operation` `operation=entropy_gc_no_op` — empty diff, no PR opened.
- `framework_operation` `operation=entropy_gc_gate_failed` — diff produced but gate refused.
- `framework_operation` `operation=entropy_gc_pr_opened` — happy path, includes `pr_url`.

## Common Mistakes

- Auto-merging the resulting PR. The skill MUST open a draft; merge requires a human.
- Running aggressive simplify modes. Conservative only — simplify-sweep trades surface area for safety.
- Scheduling more frequently than weekly. Sub-weekly cadence floods reviewers with noisy PRs.

## Examples

### Example 1 — manual weekly run

User: "run the weekly simplify sweep on this repo"

```
/ai-simplify-sweep
```

Invokes `/ai-simplify --conservative`, gates the diff, and opens a draft PR titled `chore(simplify-sweep): weekly simplification`.

### Example 2 — dry-run before scheduling

User: "preview what the simplify sweep would touch this week"

```
/ai-simplify-sweep --dry-run
```

Runs the simplify pass and prints the diff without staging a commit or PR — useful for reviewing scope before enabling a cron entry.

## Integration

Called by: `/ai-schedule` (weekly cron) or operator manually. Calls: `/ai-simplify` (conservative mode), `/ai-commit`, `/ai-pr --draft`. See also: `/ai-cleanup` (lifecycle sweep), `/ai-skill-tune` (skill-level improvement).

- Telemetry: `framework_operation` events aggregated by the spec-120 audit index.

## Scheduled cadence (spec-121)

The schedule layer should call the deterministic wrapper, not the slash command directly:

```
0 4 * * 1   <project>/.ai-engineering/scripts/scheduled/entropy-gc.sh
```

The wrapper resolves `$AIENG_PROJECT_ROOT` (or falls back to `git rev-parse --show-toplevel`), invokes `ai-eng simplify --conservative --no-pr` when the CLI is on PATH, and emits a `framework_operation` event (`operation=entropy_gc_scheduled_run`) with `outcome=success|failure|skipped` for every cycle. Never auto-merges; PR opening stays the responsibility of the slash-command path.

Activate via `/ai-schedule weekly <project>/.ai-engineering/scripts/scheduled/entropy-gc.sh` or copy the cron line above into your scheduler.

## References

- Skill source of truth: `.codex/skills/ai-simplify-sweep/SKILL.md`
- Related: `.codex/skills/ai-simplify/SKILL.md`, `.codex/skills/ai-schedule/SKILL.md`
- Manifest entry: `.ai-engineering/manifest.yml` `skills.registry.ai-simplify-sweep`
- Scheduled wrapper: `.ai-engineering/scripts/scheduled/entropy-gc.sh` (legacy filename, kept for backwards compatibility — the wrapper is invoked by cron and renaming would break installed schedules)
