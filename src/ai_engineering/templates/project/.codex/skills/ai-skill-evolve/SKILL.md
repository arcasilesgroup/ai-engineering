---
name: ai-skill-evolve
description: Improves an existing skill based on real project pain (decision-store, LESSONS.md, instincts, proposals) by evaluating it against realistic prompts, grading the output, and rewriting the SKILL.md. Trigger for 'evolve this skill', 'improve /ai-plan', 'make /ai-review better', 'optimize all skills', 'batch improve skills'. Accepts a single skill name or 'all' for batch mode. Not for creating new skills from scratch; use /ai-create instead. Not for platform audit; use /ai-platform-audit instead.
effort: max
argument-hint: "[skill-name]|all [--dry-run]"
tags: [meta, improvement, skills, optimization]
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-skill-evolve/SKILL.md
edit_policy: generated-do-not-edit
---


# ai-skill-evolve

## Quick start

```
/ai-skill-evolve ai-plan          # evolve one skill
/ai-skill-evolve all --dry-run    # preview every skill
/ai-skill-evolve all              # batch evolve with evals
```

## Workflow

Improve existing skills using evidence from real project pain (decision-store, LESSONS.md, instincts, proposals). The skill owns pain diagnosis and rewrite strategy; it delegates the eval/grade/benchmark pipeline to Anthropic's `skill-creator`.

1. Load pain context (Phase 1) — read decision-store, LESSONS.md, instincts.yml, proposals.md.
2. Analyze the target skill (Phase 2) — score 5 dimensions.
3. Generate test prompts (Phase 3) — exercise the failing pattern.
4. Rewrite the skill (Phase 4) — apply Start-Here, pain-injection, scope-gates patterns.
5. Hand off to skill-creator (Phase 5) — eval, grade, benchmark.
6. Verify improvement (Phase 6) — pass-rate delta vs prior iteration.

## When to Use

- A skill keeps producing bad output despite correct instructions.
- You've accumulated corrections in LESSONS.md that a skill should already know.
- After a batch of sessions where the same skill pattern failed repeatedly.
- Periodic hygiene: evolve the top 10 skills once a month.
- NOT for creating new skills from scratch — use `/ai-create`.
- NOT for platform audit — use `/ai-platform-audit`.

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

---

## Start Here — Output Structure

**Write this skeleton first, fill in as you go:**

```
# Skill Evolution Report — [SKILL_NAME] — [DATE]

## Pain Profile
[Bullet list of relevant lessons, decisions, instincts, and proposals]

## Current State Analysis
| Dimension | Assessment |
|-----------|-----------|
| Pain Source Awareness | LOW / MEDIUM / HIGH |
| Output Contract Position | TOP / MIDDLE / BOTTOM / NONE |
| Scope Control | ENFORCED / WEAK / ABSENT |
| Classification Usage | STRUCTURED / PROSE / NONE |
| LESSONS.md Alignment | N of M relevant lessons addressed |

## Test Cases
[2-3 prompts with rationale tied to pain sources]

## Eval Results
[Filled by skill-creator after Phase 5]

## Changes Applied
[Numbered list of specific changes to SKILL.md with before/after snippets]

## Improvement Delta
[Filled by skill-creator after Phase 5]
```

---

### Phase 1 — Load Pain Context

Before touching any skill, read these ground-truth sources: `.ai-engineering/state/state.db.decisions` (decisions/risks), `.ai-engineering/LESSONS.md` (corrections), `.ai-engineering/instincts/instincts.yml` (tool sequences/recoveries), `.ai-engineering/instincts/proposals.md` (improvement proposals), `.ai-engineering/instincts/meta.json` (freshness/thresholds), `.ai-engineering/manifest.yml` (registry/gates/ownership), `CLAUDE.md` (workflow rules).

**Extract a pain profile**: for each source, note patterns that relate to skills:
- Lessons that say "skill X keeps doing Y" or "always do Z before invoking skill X"
- Decisions that constrain how a skill should behave (e.g., DEC-003 plan/execute split)
- Instinct sequences that reveal tool misuse or inefficiency
- Proposals that suggest concrete skill improvements

### Phase 2 — Analyze Target Skill

Read the target skill's SKILL.md. If `$ARGUMENTS` is `all`, list skills from `.codex/skills/` and process them in priority order: workflow first (plan, dispatch, review, verify, commit, pr), then enterprise, then meta.

For each skill, score the five dimensions in the Current State Analysis table above (Pain Source Awareness, Output Contract Position, Scope Control, Classification Usage, LESSONS.md Alignment). The "Start Here" pattern — skeleton before instructions — dramatically improves output adherence (empirically validated during `ai-platform-audit` development: 40% → 100% pass rate by moving the output contract to the top).

### Phase 3 — Generate Test Cases

Write 2-3 test prompts that exercise the skill in contexts where the pain sources predict failure. These should be realistic — the kind of thing a developer would actually type, with specific file paths, frustrations, and context.

**Good test prompts:**
- Reference a real pain point from LESSONS.md
- Use the skill in a context where a decision from decision-store constrains behavior
- Ask for something adjacent to the skill's scope to test drift resistance

**Bad test prompts:**
- Generic "run this skill" without context
- Identical to the skill's own examples

### Phase 4 — Rewrite the Skill (dry-run first)

Apply `/ai-prompt` techniques plus these skill-specific patterns (validated during `ai-platform-audit` development):

1. **"Start Here" pattern** — output contract before process; agent fills skeleton as it works.
2. **Pain injection** — embed specific LESSONS.md patterns, do not just reference them.
3. **Scope gates** — explicit narrowing when a parameter restricts output.
4. **Classification vocabulary** — structured labels beat paragraphs; tables beat prose.
5. **Explain the why** — every instruction includes its motivation.
6. **Remove dead weight** — drop instructions that change no behavior.

If `--dry-run`, stop after showing the diff. Otherwise apply, run `python scripts/sync_command_mirrors.py`, verify `python -m pytest tests/unit/ -q`.

### Phase 5 — Eval with skill-creator

Delegate eval/grade/benchmark to Anthropic's `skill-creator` (parallel with/without runs, grader agents, benchmark aggregation, HTML viewer, description-optimization loop). Invoke with context:
```
The skill at .codex/skills/<name>/SKILL.md was just rewritten based on pain
analysis. Test prompts for evaluation are below:
[pass the test cases from Phase 3]
Run the evals, grade them, and produce the benchmark comparison.
```

This skill adds the pain-informed inputs (test cases from real decision-store/LESSONS/instincts, dimensional analysis, rewrite strategy, project governance) that skill-creator does not own.

### Phase 6 — Verify Improvement

After `skill-creator` returns the benchmark, check:
- with_skill pass rate > without_skill pass rate (the skill adds measurable value)
- with_skill pass rate improved vs previous iteration
- No regression in without_skill baseline

If the skill regressed or shows no improvement, iterate: re-read the pain profile, adjust the rewrite, and re-run Phase 5. `skill-creator` supports `--previous-workspace` for iteration-over-iteration comparison.

Record the final delta in the report's Improvement Delta table.

---

## Batch Mode (`all`)

When `$ARGUMENTS` is `all`:

1. List skills from `.codex/skills/` in priority order: Tier 1 workflow (plan, dispatch, review, verify, commit, pr, code, test), Tier 2 enterprise (security, governance, pipeline, docs, release-gate, debug), Tier 3 meta/teaching (create, learn, explain, guide, instinct), Tier 4 specialized.
2. Run Phases 1-6 per skill; re-read LESSONS.md between skills (previous improvements may update it).

4. After all skills: run the full test suite and produce a summary:
   ```
   ## Batch Evolution Summary
   | Skill | Before | After | Delta | Key Change |
   |-------|--------|-------|-------|-----------|
   ```

5. Rate limits are real. If you hit them, save progress and tell the user which skills are done and which remain. Use `--dry-run` first to preview changes without running evals.

---

## Quick Reference

```
/ai-skill-evolve ai-plan          # evolve one skill
/ai-skill-evolve ai-review        # evolve review skill
/ai-skill-evolve all --dry-run    # preview all skill improvements
/ai-skill-evolve all              # batch evolve with evals
```

## Examples

### Example 1 — single-skill evolution from accumulated pain

User: "the /ai-plan skill keeps producing decomposition that ignores constraint X. Evolve it."

```
/ai-skill-evolve ai-plan
```

Loads pain context from LESSONS.md and proposals.md, scores ai-plan on 5 dimensions, generates 2-3 test prompts that exercise the failing pattern, rewrites SKILL.md, hands off to skill-creator for eval, reports the delta.

### Example 2 — dry-run batch preview

User: "preview what evolving every skill would change before I commit time to running evals"

```
/ai-skill-evolve all --dry-run
```

Walks every skill in priority tier order, shows the proposed diff per skill, and stops short of running the eval pipeline.

## Integration

Reads: state.db.decisions, LESSONS.md, instincts.yml, proposals.md, manifest.yml. Writes: target SKILL.md files. Calls: `python scripts/sync_command_mirrors.py` after rewrites. Delegates to: Anthropic `skill-creator` (eval/grade/benchmark, Phase 5). Feeds into: `/ai-learn`. See also: `/ai-create` (new skills), `/ai-platform-audit` (cross-IDE).

$ARGUMENTS
