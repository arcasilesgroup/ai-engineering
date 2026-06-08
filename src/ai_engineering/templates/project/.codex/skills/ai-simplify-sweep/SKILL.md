---
name: ai-simplify-sweep
description: Sweeps stale code complexity on demand via an /ai-simplify wrapper, gates the diff, and opens a draft PR for human review. Trigger for 'run the simplify sweep', 'simplification sweep', 'simplify pass'. Never auto-merges, never runs unattended. Not for in-flight feature work; use /ai-simplify instead. Not for security cleanup; use /ai-security instead.
effort: cheap
argument-hint: "[--dry-run] [--no-pr]"
tags: [meta, simplification]
model_tier: haiku
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-simplify-sweep/SKILL.md
edit_policy: generated-do-not-edit
---


# Simplify Sweep

## Purpose

Codebases accumulate entropy: dead branches, redundant guards, copy-pasted helpers, layers of indirection. `/ai-simplify` already exists to fight that, but it requires manual invocation and humans rarely remember. This skill is a manual wrapper that runs simplify, gates the diff, and opens a draft PR so a human reviews the proposed reductions before merge. It has no scheduler — an operator triggers it.

## When to Use

- Periodic manual maintenance pass (weekly cadence recommended).
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

Capture the diff. If the diff is empty, emit a `framework_operation` event with `operation=simplify_sweep_no_op` and exit 0.

### Step 2 — Gate the diff

If the diff is non-empty, run the standard pre-commit gate locally:

```bash
ai-eng gate run --cache-aware --json --mode=local
```

If the gate fails, emit `operation=simplify_sweep_gate_failed` with the failure summary and exit 1 — do NOT open a PR with broken code.

### Step 3 — Commit + open draft PR

```bash
/ai-commit "chore(simplify-sweep): conservative simplification sweep"
/ai-pr --draft --title "chore(simplify-sweep): simplification" --body "Manual entropy sweep. Review the diff before merge."
```

The PR title and body explicitly mark this as an entropy GC pass so reviewers can apply lighter scrutiny than for feature PRs but still verify the simplifications preserve behaviour.

## Telemetry

Each run emits one of:

- `framework_operation` `operation=simplify_sweep_started` — at invocation.
- `framework_operation` `operation=simplify_sweep_no_op` — empty diff, no PR opened.
- `framework_operation` `operation=simplify_sweep_gate_failed` — diff produced but gate refused.
- `framework_operation` `operation=simplify_sweep_pr_opened` — happy path, includes `pr_url`.

## Common Mistakes

- Auto-merging the resulting PR. The skill MUST open a draft; merge requires a human.
- Running aggressive simplify modes. Conservative only — simplify-sweep trades surface area for safety.
- Running more frequently than weekly. Sub-weekly runs flood reviewers with noisy PRs.

## Examples

### Example 1 — manual weekly run

User: "run the weekly simplify sweep on this repo"

```
/ai-simplify-sweep
```

Invokes `/ai-simplify --conservative`, gates the diff, and opens a draft PR titled `chore(simplify-sweep): simplification`.

### Example 2 — dry-run preview

User: "preview what the simplify sweep would touch"

```
/ai-simplify-sweep --dry-run
```

Runs the simplify pass and prints the diff without staging a commit or PR — useful for reviewing scope before a full run.

## Integration

Called by: operator manually. Calls: `/ai-simplify` (conservative mode), `/ai-commit`, `/ai-pr --draft`. See also: `/ai-branch-cleanup` (lifecycle sweep), `/ai-skill-improve` (skill-level improvement).

- Telemetry: `framework_operation` events aggregated from `framework-events.ndjson`.

## References

- Skill source of truth: `.codex/skills/ai-simplify-sweep/SKILL.md`
- Related: `.codex/skills/ai-simplify/SKILL.md`
- Manifest entry: `.ai-engineering/manifest.yml` `skills.registry.ai-simplify-sweep`
