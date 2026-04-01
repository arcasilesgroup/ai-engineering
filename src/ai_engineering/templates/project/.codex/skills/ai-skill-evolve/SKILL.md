---
name: ai-skill-evolve
description: Use to improve any existing skill in ai-engineering based on real project pain — not theory. Reads decision-store, LESSONS.md, instincts, and proposals to understand what actually hurts, then evaluates the skill against realistic test prompts, grades the output, and rewrites the SKILL.md to be more effective. Trigger for 'evolve this skill', 'improve /ai-plan', 'make /ai-review better', 'the commit skill keeps doing X wrong', 'optimize all skills', 'batch improve skills', 'this skill isn't working well', 'evolve the framework'. Accepts a single skill name or 'all' for batch mode.
effort: max
argument-hint: "<skill-name>|all [--dry-run]"
tags: [meta, improvement, skills, optimization]
---


# ai-skill-evolve

Improve existing skills using evidence from real project pain, not guesswork. Every improvement is grounded in what the decision-store, LESSONS.md, instincts, and proposals actually say about how the skill performs (or fails) in practice.

This skill owns **pain diagnosis and rewrite strategy**. For the eval/grade/benchmark pipeline, it delegates to Anthropic's `skill-creator` which has the full infrastructure (grader agents, benchmark aggregation, HTML viewer, description optimization).

## When to Use

- A skill keeps producing bad output despite correct instructions.
- You've accumulated corrections in LESSONS.md that a skill should already know.
- After a batch of sessions where the same skill pattern failed repeatedly.
- Periodic hygiene: evolve the top 10 skills once a month.
- NOT for creating new skills from scratch — use `/ai-create`.
- NOT for platform audit — use `/ai-platform-audit`.

## Step 0: Load Stack Contexts

Follow `.ai-engineering/contexts/stack-context.md`.

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

Before touching any skill, read these 5 sources. They are the ground truth about what hurts in this project:

| Source | Path | What it tells you |
|--------|------|-------------------|
| Decision Store | `.ai-engineering/state/decision-store.json` | Formal governance decisions, risk acceptances, expired choices |
| Lessons | `.ai-engineering/LESSONS.md` | Informal patterns and corrections accumulated across sessions |
| Instincts | `.ai-engineering/instincts/instincts.yml` | Observed tool sequences and error recovery patterns |
| Proposals | `.ai-engineering/instincts/proposals.md` | Actionable improvement proposals backed by instinct evidence |
| Instinct Meta | `.ai-engineering/instincts/meta.json` | Freshness and thresholds — is the data stale? |

Also read:
- `.ai-engineering/manifest.yml` — skill registry, quality gates, ownership
- `CLAUDE.md` — workflow orchestration rules and quality gates

**Extract a pain profile**: For each source, note patterns that relate to skills:
- Lessons that say "skill X keeps doing Y" or "always do Z before invoking skill X"
- Decisions that constrain how a skill should behave (e.g., DEC-003 plan/execute split)
- Instinct sequences that reveal tool misuse or inefficiency
- Proposals that suggest concrete skill improvements

### Phase 2 — Analyze Target Skill

Read the target skill's SKILL.md. If `$ARGUMENTS` is `all`, list skills from `.codex/skills/` and process them in priority order: workflow skills first (plan, dispatch, review, verify, commit, pr), then enterprise, then meta.

For each skill, answer:
1. **Does it reference pain sources?** Skills that load context from decision-store, lessons, or instincts are more resilient. Skills that don't are flying blind.
2. **Is the output contract enforced?** Having an output template is useless if it's buried at the bottom. The "Start Here" pattern (skeleton before instructions) dramatically improves output adherence — we proved this empirically when building `ai-platform-audit` (from 40% to 100% pass rate by moving the output contract to the top).
3. **Is scope controlled?** Does the skill drift into adjacent concerns when given a narrow request?
4. **Are classifications used?** Skills that output structured verdicts (PASS/FAIL, SUPPORTED/PARTIAL, P0/P1/P2) are more actionable than prose.
5. **Does it match LESSONS.md patterns?** Cross-reference the skill's instructions against known lessons. If LESSONS.md says "always do X" and the skill doesn't mention X, that's a gap.

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

Based on the pain profile and analysis, rewrite the SKILL.md. Apply `/ai-prompt` techniques for general optimization, plus these skill-specific patterns (empirically validated during `ai-platform-audit` development):

1. **"Start Here" pattern** — If the skill has an output contract, move it BEFORE the process instructions. The agent sees the output skeleton first and fills it in as it works.

2. **Pain injection** — Weave relevant lessons and decisions directly into the skill's instructions. Don't just reference LESSONS.md — embed the specific patterns that affect this skill so the agent sees them in context.

3. **Scope gates** — Add explicit scope control when the skill handles a parameter that narrows focus. "If X is not 'all', restrict output to X only."

4. **Classification vocabulary** — Replace prose with structured labels where possible. Tables with fixed columns beat paragraphs.

5. **Explain the why** — For every instruction, explain why it matters. LLMs respond better to reasoning than to directives.

6. **Remove dead weight** — If an instruction adds no behavioral difference, remove it. Leaner skills perform better.

If `--dry-run` was passed, show the proposed diff in the report and stop here. Otherwise, apply the rewrite and continue to Phase 5.

After rewriting: run `python scripts/sync_command_mirrors.py` and verify tests pass:
```bash
source .venv/bin/activate && python -m pytest tests/unit/ -q
```

### Phase 5 — Eval with skill-creator

Delegate the eval/grade/benchmark loop to Anthropic's `skill-creator`. It has the infrastructure that would be wasteful to duplicate: parallel with/without runs, grader agents, benchmark aggregation, and an HTML viewer.

Invoke `skill-creator` with this context:
```
I have an existing skill at .codex/skills/<name>/SKILL.md that I just rewrote
based on pain analysis. Here are 2-3 test prompts to evaluate it:
[pass the test cases from Phase 3]
Run the evals, grade them, and show me the benchmark comparison.
```

**What skill-creator provides:**
- Parallel agent dispatch (with_skill + without_skill baseline)
- Structured grading with assertions (`grader.md` agent)
- Benchmark aggregation with pass rates, timing, tokens (`aggregate_benchmark`)
- Interactive HTML viewer for qualitative + quantitative comparison (`generate_review.py`)
- Description optimization loop for better triggering accuracy (`run_loop.py`)

**What ai-skill-evolve provides:**
- Pain-informed test cases grounded in real decision-store, LESSONS, and instincts
- Dimensional analysis of the skill's current weaknesses
- Rewrite strategy based on empirically validated patterns
- Project governance context that skill-creator doesn't have

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

1. List all skills from `.codex/skills/` sorted by priority tier:
   - **Tier 1** (workflow): plan, dispatch, review, verify, commit, pr, code, test
   - **Tier 2** (enterprise): security, governance, pipeline, docs, release-gate, debug
   - **Tier 3** (meta/teaching): create, learn, onboard, explain, guide, instinct
   - **Tier 4** (specialized): the rest

2. For each skill, run the full evolution loop (Phases 1-6).

3. Between skills, re-read LESSONS.md — previous improvements may have updated it.

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

## Integration

- **Reads**: decision-store.json, LESSONS.md, instincts.yml, proposals.md, manifest.yml
- **Writes**: target SKILL.md files (via rewrite), mirror sync
- **Calls**: `python scripts/sync_command_mirrors.py` after rewrites
- **Delegates to**: Anthropic `skill-creator` for eval/grade/benchmark pipeline (Phase 5)
- **Feeds into**: `/ai-learn` (improvements discovered during evolution become lessons)

$ARGUMENTS
