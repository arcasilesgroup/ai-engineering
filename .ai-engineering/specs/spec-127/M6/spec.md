---
id: sub-007
parent: spec-127
milestone: M6
title: "Eval harness + self-improvement loop"
status: planning
files:
  - scripts/run_loop_skill_evals.py
  - evals/
  - evals/baseline.json
  - tests/integration/test_eval_regression_gate.py
  - .github/workflows/skill-evals.yml
  - .claude/skills/ai-eval/SKILL.md
  - .claude/skills/ai-skill-tune/SKILL.md
depends_on:
  - sub-003
---

# Sub-Spec 007: M6 — Eval harness + self-improvement loop

## Scope

Per D-127-07 (LLM-generated + human review on top-confusion cases). Implement
`scripts/run_loop_skill_evals.py` driving the `skill-creator` optimizer over
each skill's description. Generate `evals/<skill>.jsonl` with 16 cases × 46
skills (8 should-trigger / 8 near-miss) via LLM pass. Generate near-miss
trigger phrases per skill via `git log --grep` over 12 months of user commit
messages — feed into eval generator as adversarial prompts.

Operator review of top-10 near-miss cases per skill (manual gate; output
committed). Ship `tests/integration/test_eval_regression_gate.py` asserting
`>5%` pass@1 regression fails CI. Implement `/ai-eval --skill-set` mode
running optimizer pass@k against eval corpus. Add CI workflow step: on PR
touching `.claude/skills/**`, run `ai-eval --skill-set --regression`; fail
loud on >5% pass@1 regression.

Update `/ai-skill-tune` (renamed from `/ai-skill-evolve`) to consume prior
evals + Engram observations + `LESSONS.md` and propose description deltas as
PR-only output (no auto-merge). Capture baseline pass@1 in `evals/baseline.json`.

## Exploration

### Current eval surface (`/ai-eval`)

- `.claude/skills/ai-eval/SKILL.md` ships four feature-eval modes: `define`,
  `check`, `report`, `regression` (per `<feature>.md` + `<feature>.log` under
  `.ai-engineering/evals/`). NO skill-set mode. Sub-007 adds
  `--skill-set [skill|all] [--regression]` as fifth mode without breaking the
  four feature modes.
- Storage today: `.ai-engineering/evals/<feature>.{md,log}` + `baseline.json`.
  Sub-007 introduces parallel root: `evals/<skill>.jsonl` (one corpus per
  skill, one line per case) + `evals/baseline.json` (pass@1 per skill).
- Grader policy: should-trigger uses code grader (deterministic); near-miss
  uses code grader negative (no skill selected, OR correct alternative
  selected). No model grader needed — reduces to multi-class classification.

### Current optimizer surface (`/ai-skill-evolve` → `/ai-skill-tune` post-M4)

- Phase 5 already delegates to Anthropic's `skill-creator`
  (`~/.claude/skills/skill-creator/`). Confirmed scripts: `run_loop.py`,
  `improve_description.py`, `run_eval.py`, `aggregate_benchmark.py`,
  `generate_report.py`. Sub-007 does NOT reimplement — just drives.
- `scripts/run_loop_skill_evals.py` is a thin driver:
  1. Iterates 46 skills in `.claude/skills/`
  2. For each, loads `evals/<skill>.jsonl`
  3. Shells out to `skill-creator/scripts/run_loop.py --skill-path
     .claude/skills/<name>` + JSONL corpus
  4. Aggregates per-skill pass@1 into `evals/baseline.json`
- `/ai-skill-tune` (post-M4) gains Phase 0.5: read `evals/<skill>.jsonl` +
  last `evals/baseline.json` row + LESSONS.md + Engram top-confusion notes.
  Output is description delta as PR comment (no auto-merge).
- External dependency: `~/.claude/skills/skill-creator/` is user-installed.
  Recommended: vendor adapter `tools/skill_infra/skill_creator_adapter.py`
  exposing `run_loop`, `run_eval`, `aggregate_benchmark` via subprocess.
  Pin upstream commit SHA in module docstring for drift detection.

### LESSONS.md (read-only)

`.ai-engineering/LESSONS.md` is flat markdown with `### <pattern>` H3 headers,
each with `**Context:**`, `**Learning:**`, `**Rule:**` triple. Parser is
regex-only — match H3 against skill names, extract Learning paragraph as
near-miss `should_not_trigger` rationale.

### Existing layouts

- `evals/` does not exist at repo root today.
- `.github/workflows/` has 10 workflows (`ci-check.yml` 806 lines is
  canonical). Pattern: `dorny/paths-filter`, `concurrency` group, pinned
  SHAs, `astral-sh/setup-uv`. `skill-evals.yml` mirrors `ci-check.yml` with
  `paths` filter narrowed to `.claude/skills/**` + `tools/skill_app/**` +
  `evals/**`, single job invoking
  `python scripts/run_loop_skill_evals.py --regression --baseline
  evals/baseline.json` with `timeout-minutes: 25`.
- `tests/integration/` has integration tests with pytest markers. New
  `test_eval_regression_gate.py` follows pattern: temp `evals/` fixture +
  synthetic baseline.json + mutate one skill desc to drop pass@1 by 6% →
  assert gate exits non-zero with structured report.

### Near-miss generation (D-127-07)

Two complementary sources:

1. **`git log --grep`** over 12 months. For each skill, query trigger phrases
   from SKILL.md `description` field. Off-target adjacent commits become gold
   near-miss prompts.
2. **LESSONS.md mining** — every "skill X did Y wrong" lesson becomes a
   should-not-trigger case. Real confusion patterns.

LLM generator (sonnet, structured-output) takes SKILL.md + should-trigger
seeds + git-log near-miss + LESSONS near-miss → 16 JSONL lines:

```json
{"prompt": "...", "expected_skill": "ai-debug", "kind": "should_trigger"}
{"prompt": "...", "expected_skill": null, "kind": "near_miss",
 "rationale": "looks like /ai-debug but user wants /ai-test"}
```

### Scale (46 skills × 16 cases = 736 case files)

- `evals/<skill>.jsonl` flat layout. 46 files. ~150 KB committed total.
- Generation batched 5–10 skills per ai-build invocation. 46 / 8 ≈ 6 batches.

### `evals/baseline.json` schema

```json
{
  "captured_at": "...",
  "captured_commit": "abc1234",
  "skill_creator_adapter_pin": "anthropic-skill-creator@<sha>",
  "skills": {
    "ai-debug": {"pass_at_1": 0.875, "pass_at_3": 0.9375,
                 "should_trigger_passed": 7, "should_trigger_total": 8,
                 "near_miss_passed": 7, "near_miss_total": 8, "case_count": 16}
  },
  "aggregate": {"pass_at_1_mean": 0.84, "pass_at_1_min": 0.625, "skill_count": 46},
  "thresholds": {"pass_at_1_regression_pct": 5.0}
}
```

### Dependencies

- Depends on sub-003 (M2 CSO pass): eval cases need optimized descriptions
  to be meaningful.
- Coordinates with M4 rename: integration uses post-rename `ai-skill-tune`.
