# Six-Phase Evolution Protocol

## Phase 1 — Load Pain Context

Before touching any skill, read these ground-truth sources: `.ai-engineering/state/state.db.decisions` (decisions/risks), `.ai-engineering/LESSONS.md` (corrections), `.ai-engineering/instincts/instincts.yml` (tool sequences/recoveries), `.ai-engineering/instincts/proposals.md` (improvement proposals), `.ai-engineering/instincts/meta.json` (freshness/thresholds), `.ai-engineering/manifest.yml` (registry/gates/ownership), `CLAUDE.md` (workflow rules).

**Extract a pain profile**: for each source, note patterns that relate to skills:

- Lessons that say "skill X keeps doing Y" or "always do Z before invoking skill X".
- Decisions that constrain how a skill should behave (e.g., DEC-003 plan/execute split).
- Instinct sequences that reveal tool misuse or inefficiency.
- Proposals that suggest concrete skill improvements.

## Phase 2 — Analyze Target Skill

Read the target skill's SKILL.md. If `$ARGUMENTS` is `all`, list skills from `.codex/skills/` and process them in priority order: workflow first (plan, dispatch, review, verify, commit, pr), then enterprise, then meta.

For each skill, score the five dimensions in the Current State Analysis table (Pain Source Awareness, Output Contract Position, Scope Control, Classification Usage, LESSONS.md Alignment). The "Start Here" pattern — skeleton before instructions — dramatically improves output adherence (empirically validated during `ai-ide-audit` development: 40% → 100% pass rate by moving the output contract to the top).

## Phase 3 — Generate Test Cases

Write 2-3 test prompts that exercise the skill in contexts where the pain sources predict failure. Make them realistic — the kind of thing a developer would actually type, with specific file paths, frustrations, and context.

**Good test prompts**:

- Reference a real pain point from LESSONS.md.
- Use the skill in a context where a decision from decision-store constrains behavior.
- Ask for something adjacent to the skill's scope to test drift resistance.

**Bad test prompts**:

- Generic "run this skill" without context.
- Identical to the skill's own examples.

## Phase 4 — Rewrite the Skill (dry-run first)

Apply `/ai-prompt` techniques plus these skill-specific patterns (validated during `ai-ide-audit` development):

1. **"Start Here" pattern** — output contract before process; agent fills skeleton as it works.
2. **Pain injection** — embed specific LESSONS.md patterns, do not just reference them.
3. **Scope gates** — explicit narrowing when a parameter restricts output.
4. **Classification vocabulary** — structured labels beat paragraphs; tables beat prose.
5. **Explain the why** — every instruction includes its motivation.
6. **Remove dead weight** — drop instructions that change no behavior.

If `--dry-run`, stop after showing the diff. Otherwise apply, run `python scripts/sync_command_mirrors.py`, verify `python -m pytest tests/unit/ -q`.

## Phase 5 — Eval with skill-creator

Delegate eval/grade/benchmark to Anthropic's `skill-creator` (parallel with/without runs, grader agents, benchmark aggregation, HTML viewer, description-optimization loop). Invoke with context:

```
The skill at .codex/skills/<name>/SKILL.md was just rewritten based on pain
analysis. Test prompts for evaluation are below:
[pass the test cases from Phase 3]
Run the evals, grade them, and produce the benchmark comparison.
```

This skill adds the pain-informed inputs (test cases from real decision-store/LESSONS/instincts, dimensional analysis, rewrite strategy, project governance) that skill-creator does not own.

## Phase 6 — Verify Improvement

After `skill-creator` returns the benchmark, check:

- with_skill pass rate > without_skill pass rate (the skill adds measurable value).
- with_skill pass rate improved vs previous iteration.
- No regression in without_skill baseline.

If the skill regressed or shows no improvement, iterate: re-read the pain profile, adjust the rewrite, and re-run Phase 5. `skill-creator` supports `--previous-workspace` for iteration-over-iteration comparison.

Record the final delta in the audit document's Improvement Delta table.
