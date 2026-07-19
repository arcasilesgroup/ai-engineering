---
name: ai-simplify-sweep
description: "Sweeps stale code complexity on demand via an /ai-simplify wrapper, gates the diff, and opens a draft PR for human review. Trigger for 'run the simplify sweep', 'simplification sweep', 'simplify pass'. Never auto-merges, never runs unattended. Not for in-flight feature work; use /ai-simplify instead. Not for security cleanup; use /ai-security instead."
effort: cheap
argument-hint: "[--dry-run] [--no-pr]"
tags: [meta, simplification]
---

# Simplify Sweep

Sweeps stale code complexity on demand via an `/ai-simplify` wrapper, gates the diff, and opens a draft PR for human review. Use it for an operator-triggered simplification pass — never auto-merges, never runs unattended.

## Purpose

Codebases accumulate entropy: dead branches, redundant guards, copy-pasted helpers, layers of indirection. `/ai-simplify` fights that but needs manual invocation. This skill is a manual wrapper that runs simplify, gates the diff, and opens a draft PR so a human reviews the proposed reductions before merge. No scheduler — an operator triggers it.

## Workflow

Principles applied: §10.1 KISS (conservative reductions only — the sweep trades surface area for safety).

### Step 1 — Invoke `/ai-simplify` non-interactively

Read `.claude/skills/ai-simplify/SKILL.md` (when present) to confirm whether an `--auto` flag exists. Otherwise invoke with conservative defaults:

```
/ai-simplify --conservative
```

Capture the diff. If empty, emit `framework_operation operation=simplify_sweep_no_op` and exit 0.

### Step 2 — Gate the diff

Non-empty diff: run the pre-commit gate locally.

```bash
ai-eng gate run --cache-aware --json --mode=local
```

If the gate fails, emit `operation=simplify_sweep_gate_failed` with the failure summary and exit 1 — never open a PR with broken code.

### Step 3 — Commit + open draft PR

```bash
/ai-commit "chore(simplify-sweep): conservative simplification sweep"
/ai-pr --draft --title "chore(simplify-sweep): simplification" --body "Manual entropy sweep. Review the diff before merge."
```

The title/body mark this as an entropy GC pass so reviewers apply lighter scrutiny than a feature PR while still verifying behaviour is preserved.

## Hard Rules

- Never auto-merge — the PR is always `--draft`.
- Conservative defaults only — guard clauses, early returns, dead-code removal, single-call-site inlines. No aggressive refactors.
- Empty simplify diff: exit cleanly with a status event; do NOT open an empty PR.

## Telemetry

Each run emits one `framework_operation`:

- `operation=simplify_sweep_started` — at invocation.
- `operation=simplify_sweep_no_op` — empty diff, no PR.
- `operation=simplify_sweep_gate_failed` — diff produced but gate refused.
- `operation=simplify_sweep_pr_opened` — happy path, includes `pr_url`.

## Common Mistakes

- Running more often than weekly — sub-weekly runs flood reviewers with noisy PRs (auto-merge and aggressive modes are already barred by Hard Rules).

## Examples

### Example — dry-run preview

User: "preview what the simplify sweep would touch"

```
/ai-simplify-sweep --dry-run
```

Runs the simplify pass and prints the diff without staging a commit or PR — useful for reviewing scope before a full run.

## Integration

Called by: operator manually. Calls: `/ai-simplify` (conservative mode), `/ai-commit`, `/ai-pr --draft`. See also: `/ai-branch-cleanup` (lifecycle sweep), `/ai-skill-improve` (skill-level improvement).

- Telemetry: `framework_operation` events aggregated from `framework-events.ndjson`.

## References

- Related: `.claude/skills/ai-simplify/SKILL.md`
- Manifest entry: `.ai-engineering/manifest.yml` `skills.registry.ai-simplify-sweep`
