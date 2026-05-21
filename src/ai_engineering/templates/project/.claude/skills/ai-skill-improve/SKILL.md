---
name: ai-skill-improve
description: "Improves an existing skill based on real project pain (prior eval corpora under .ai-engineering/evals/, Engram cross-session observations, LESSONS.md, decision-store, instincts, proposals) by analysing the failure pattern, rewriting SKILL.md, and emitting the proposed delta as a PR comment only — no auto-merge. Trigger for 'improve this skill', 'improve /ai-plan', 'make /ai-review better', 'optimize all skills', 'batch improve skills'. Accepts a single skill name or 'all' for batch mode. Not for creating new skills from scratch; use /ai-scaffold instead. Not for platform audit; use /ai-ide-audit instead."
effort: mid
model_tier: sonnet
argument-hint: "[skill-name]|all [--dry-run]"
tags: [meta, improvement, skills, optimization, improve]
---

# ai-skill-improve

## Quick start

```
/ai-skill-improve ai-plan          # evolve one skill
/ai-skill-improve all --dry-run    # preview every skill
/ai-skill-improve all              # batch evolve with evals
```

## Workflow

Improve existing skills using evidence from real project pain (prior eval corpora under `.ai-engineering/evals/`, Engram cross-session observations via `MemoryPort`, `LESSONS.md` operator notes, decision-store, instincts, proposals). The skill owns pain diagnosis and rewrite strategy; it delegates the eval/grade/benchmark pipeline to Anthropic's `skill-creator`. **Output is PR-comment only — never auto-merged** (sub-007 M6).

1. **Phase 0.5** — load corpora (`.ai-engineering/evals/<skill>.jsonl`), Engram observations (`/ai-memory` MCP), and `LESSONS.md` H3 sections that mention the target skill.
2. **Phase 1** — load remaining pain context (decision-store, observations.yml, proposals.md).
3. **Phase 2** — analyze the target skill, score the 5 dimensions.
4. **Phase 3** — generate test prompts that exercise the failing pattern.
5. **Phase 4** — rewrite the skill (Start-Here, pain-injection, scope-gates, structured classification).
6. **Phase 5** — emit the proposed SKILL.md diff as a PR comment via `gh pr comment`. **Do not commit or push.** Operator review is the merge gate.
7. **Phase 6** — verify improvement on the operator's branch (pass-rate delta vs prior iteration).

> Detail: see [audit document skeleton](references/output-skeleton.md), [the six-phase protocol (load → analyze → generate → rewrite → eval → verify)](references/six-phase-protocol.md), [batch mode for `all`](references/batch-mode.md).

## When to Use

- A skill keeps producing bad output despite correct instructions.
- You've accumulated corrections in LESSONS.md that a skill should already know.
- After a batch of sessions where the same skill pattern failed repeatedly.
- Periodic hygiene: evolve the top 10 skills once a month.
- NOT for creating new skills from scratch — use `/ai-scaffold`.
- NOT for platform audit — use `/ai-ide-audit`.

Step 0 (load contexts): read `.ai-engineering/manifest.yml` `providers.stacks`; load `.ai-engineering/overrides/<stack>/conventions.md` for each stack and `.ai-engineering/overrides/_shared/conventions.md`; load `.ai-engineering/team/*.md` for team conventions.

## Common Mistakes

- Rewriting before reading the pain profile.
- Skipping `--dry-run` on batch (you'll burn rate limits).
- Inventing test prompts that mirror the skill's own examples (no drift signal).
- Leaving Phase 5 evals unrun and declaring the skill "improved".

## Examples

### Example 1 — single-skill evolution from accumulated pain

User: "the /ai-plan skill keeps producing decomposition that ignores constraint X. Improve it."

```
/ai-skill-improve ai-plan
```

Loads pain context from LESSONS.md and proposals.md, scores ai-plan on 5 dimensions, generates 2-3 test prompts that exercise the failing pattern, rewrites SKILL.md, hands off to skill-creator for eval, reports the delta.

### Example 2 — dry-run batch preview

User: "preview what improving every skill would change before I commit time to running evals"

```
/ai-skill-improve all --dry-run
```

Walks every skill in priority tier order, shows the proposed diff per skill, and stops short of running the eval pipeline.

## Integration

Reads: decision-store.json, LESSONS.md, observations.yml, proposals.md, manifest.yml. Writes: target SKILL.md files. Calls: `python scripts/sync_command_mirrors.py` after rewrites. Delegates to: Anthropic `skill-creator` (eval/grade/benchmark, Phase 5). Feeds into: `/ai-learn`. See also: `/ai-scaffold` (new skills), `/ai-ide-audit` (cross-IDE).

$ARGUMENTS
