---
name: ai-entropy-gc
description: "Scheduled wrapper around /ai-simplify that runs weekly, gates the resulting diff, and opens a draft PR for human review. Trigger for 'weekly entropy sweep', 'scheduled simplification', 'entropy gc'. Hard rule: never auto-merges; always opens a draft PR. Recommended cadence: weekly via /schedule."
model: sonnet
effort: medium
color: teal
argument-hint: "[--dry-run] [--no-pr]"
mode: agent
tags: [meta, simplification, entropy, scheduled, autonomous]
tools: [Bash, Read]
mirror_family: copilot-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-entropy-gc/SKILL.md
edit_policy: generated-do-not-edit
---


# Entropy GC

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

Read `.github/skills/ai-simplify/SKILL.md` (when present) to confirm whether an explicit `--auto` flag exists. If not, invoke with conservative defaults equivalent to:

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
/ai-commit "chore(entropy-gc): weekly automated simplification sweep"
/ai-pr --draft --title "chore(entropy-gc): weekly simplification" --body "Automated weekly entropy sweep. Review the diff before merge."
```

The PR title and body explicitly mark this as an automated entropy GC pass so reviewers can apply lighter scrutiny than for feature PRs but still verify the simplifications preserve behaviour.

## Scheduling

Recommended invocation pattern (run once to register the routine):

```
/schedule weekly /ai-entropy-gc
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
- Running aggressive simplify modes. Conservative only — entropy GC trades surface area for safety.
- Scheduling more frequently than weekly. Sub-weekly cadence floods reviewers with noisy PRs.

## Integration

- **Calls**: `/ai-simplify` (conservative mode), `ai-eng gate run`, `/ai-commit`, `/ai-pr --draft`.
- **Scheduled by**: `/ai-schedule` via the `/schedule weekly /ai-entropy-gc` invocation pattern.
- **Telemetry**: `framework_operation` events are aggregated by the spec-120 audit index.

## References

- Skill source of truth: `.github/skills/ai-entropy-gc/SKILL.md`
- Related: `.github/skills/ai-simplify/SKILL.md`, `.github/skills/ai-schedule/SKILL.md`
- Manifest entry: `.ai-engineering/manifest.yml` `skills.registry.ai-entropy-gc`
