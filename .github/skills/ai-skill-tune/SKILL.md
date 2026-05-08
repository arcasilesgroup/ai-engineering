---
name: ai-skill-tune
description: Tunes an existing skill based on real project pain (decision-store, LESSONS.md, instincts, proposals) by evaluating it against realistic prompts, grading the output, and rewriting the SKILL.md. Trigger for 'tune this skill', 'improve /ai-plan', 'make /ai-review better', 'optimize all skills', 'batch tune skills'. Accepts a single skill name or 'all' for batch mode. Not for creating new skills from scratch; use /ai-create instead. Not for platform audit; use /ai-ide-audit instead.
effort: max
argument-hint: "[skill-name]|all [--dry-run]"
mode: agent
tags: [meta, improvement, skills, optimization, tune]
mirror_family: copilot-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-skill-tune/SKILL.md
edit_policy: generated-do-not-edit
---


# ai-skill-tune

## Quick start

```
/ai-skill-tune ai-plan          # evolve one skill
/ai-skill-tune all --dry-run    # preview every skill
/ai-skill-tune all              # batch evolve with evals
```

## Workflow

Improve existing skills using evidence from real project pain (decision-store, LESSONS.md, instincts, proposals). The skill owns pain diagnosis and rewrite strategy; it delegates the eval/grade/benchmark pipeline to Anthropic's `skill-creator`.

1. **Phase 1** — load pain context (decision-store, LESSONS.md, instincts.yml, proposals.md).
2. **Phase 2** — analyze the target skill, score the 5 dimensions.
3. **Phase 3** — generate test prompts that exercise the failing pattern.
4. **Phase 4** — rewrite the skill (Start-Here, pain-injection, scope-gates, structured classification).
5. **Phase 5** — hand off to `skill-creator` (eval, grade, benchmark).
6. **Phase 6** — verify improvement (pass-rate delta vs prior iteration).

> Detail: see [audit document skeleton](references/output-skeleton.md), [the six-phase protocol (load → analyze → generate → rewrite → eval → verify)](references/six-phase-protocol.md), [batch mode for `all`](references/batch-mode.md).

## When to Use

- A skill keeps producing bad output despite correct instructions.
- You've accumulated corrections in LESSONS.md that a skill should already know.
- After a batch of sessions where the same skill pattern failed repeatedly.
- Periodic hygiene: evolve the top 10 skills once a month.
- NOT for creating new skills from scratch — use `/ai-create`.
- NOT for platform audit — use `/ai-ide-audit`.

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

## Common Mistakes

- Rewriting before reading the pain profile.
- Skipping `--dry-run` on batch (you'll burn rate limits).
- Inventing test prompts that mirror the skill's own examples (no drift signal).
- Leaving Phase 5 evals unrun and declaring the skill "improved".

## Examples

### Example 1 — single-skill evolution from accumulated pain

User: "the /ai-plan skill keeps producing decomposition that ignores constraint X. Tune it."

```
/ai-skill-tune ai-plan
```

Loads pain context from LESSONS.md and proposals.md, scores ai-plan on 5 dimensions, generates 2-3 test prompts that exercise the failing pattern, rewrites SKILL.md, hands off to skill-creator for eval, reports the delta.

### Example 2 — dry-run batch preview

User: "preview what tuning every skill would change before I commit time to running evals"

```
/ai-skill-tune all --dry-run
```

Walks every skill in priority tier order, shows the proposed diff per skill, and stops short of running the eval pipeline.

## Integration

Reads: state.db.decisions, LESSONS.md, instincts.yml, proposals.md, manifest.yml. Writes: target SKILL.md files. Calls: `python scripts/sync_command_mirrors.py` after rewrites. Delegates to: Anthropic `skill-creator` (eval/grade/benchmark, Phase 5). Feeds into: `/ai-learn`. See also: `/ai-create` (new skills), `/ai-ide-audit` (cross-IDE).

$ARGUMENTS
