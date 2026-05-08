---
total: 38
completed: 0
---

# Plan: sub-007 M6 — Eval harness + self-improvement loop

## Pipeline: full
## Phases: 9
## Tasks: 38

## Architecture

Hexagonal (consistent with M5).
- Domain (tools/skill_domain/): EvalCase, EvalCorpus, BaselineEntry,
  RegressionReport. Zero I/O.
- Application (tools/skill_app/): generator, runner, regression_gate.
  Calls ports only.
- Ports (tools/skill_app/ports/): OptimizerPort, LLMPort, GitLogPort,
  LessonsPort.
- Infrastructure (tools/skill_infra/): skill_creator_adapter,
  llm_adapter, git_log_adapter, lessons_md_parser.
- Orchestration: scripts/run_loop_skill_evals.py CLI.
- CI gate: .github/workflows/skill-evals.yml.

## Phase classification: full

New artifact tree (evals/), new skill mode (--skill-set), new CI workflow,
optimizer adapter, 46 corpora, regression gate test.

### Phase 0: Pre-flight

Gate: sub-003 shipped; sub-007 in-progress; M4 rename confirmed.

- [ ] T-0.1: Verify sub-003 shipped (agent: verify)
- [ ] T-0.2: Confirm skill-creator scripts reachable; capture upstream SHA
  into adapter docstring (agent: build)
- [ ] T-0.3: Confirm M4 rename status; if ai-skill-tune exists use it;
  else legacy name + TODO (agent: verify)
- [ ] T-0.4: Create empty evals/ with .gitkeep (agent: build)

### Phase 1: Optimizer adapter + domain types

Gate: layering test green; adapter round-trips synthetic 1-case corpus.

- [ ] T-1.1: RED test for 4 dataclasses (immutability, JSON round-trip)
  (agent: build)
- [ ] T-1.2: Implement tools/skill_domain/eval_types.py pure dataclasses.
  Constraint: no test edits from T-1.1 (agent: build)
- [ ] T-1.3: Define 4 ports as Protocols (agent: build)
- [ ] T-1.4: RED adapter test — synthetic 1-case round-trip (agent: build)
- [ ] T-1.5: Implement skill_creator_adapter subprocess wrapper, pinned SHA
  in docstring. Constraint: no test edits from T-1.4 (agent: build)
- [ ] T-1.6: Verify pytest green (agent: verify)

### Phase 2: Regression gate test (TDD RED)

Gate: regression-gate test written and FAILING.

- [ ] T-2.1: RED test — fixture: synthetic 5-skill 5-case corpus, baseline
  pass-at-1 = 1.0; mutate one skill description to drop pass-at-1 to 0.93;
  assert gate returns non-zero exit + RegressionReport (agent: build)
- [ ] T-2.2: Verify test fails with import error (agent: verify)

### Phase 3: GREEN — gate + runner + CLI

Gate: T-2.1 green; generator produces 16-case JSONL for pilot skill.

GREEN constraint: no edits to regression-gate test from T-2.1.

- [ ] T-3.1: Implement regression_gate.py calling OptimizerPort + comparing
  against baseline; threshold from baseline thresholds default 5.0
  (agent: build)
- [ ] T-3.2: Implement runner.py orchestrator (agent: build)
- [ ] T-3.3: Implement run_loop_skill_evals.py CLI; flags --skill,
  --regression, --baseline, --corpus-root, --out (agent: build)
- [ ] T-3.4: Verify regression gate test green (agent: verify)

### Phase 4: Pilot corpus (5 skills) — gate before scaling

Gate: 5 corpora valid 16-line JSONL (8 should / 8 near-miss); optimizer
round-trip reports defensible per-skill pass-at-1.

Hard rule: no Phase 5 until pilot lands and operator inspects corpora.

- [ ] T-4.1: Implement git_log_adapter.py — find_near_miss_phrases since 12
  months ago (agent: build)
- [ ] T-4.2: Implement lessons_md_parser.py regex H3 walker (agent: build)
- [ ] T-4.3: Implement llm_adapter.py — sonnet, structured output, 16-case
  JSONL generator (agent: build)
- [ ] T-4.4: Implement generator.py orchestrating 3 ports (agent: build)
- [ ] T-4.5: Generate 5 pilot corpora — ai-debug, ai-test, ai-verify,
  ai-review, ai-commit (agent: build)
- [ ] T-4.6: Run optimizer over pilots; commit transient pilot baseline
  (agent: build)
- [ ] T-4.7: Verify pilot corpora valid via test_corpus_shape (agent: verify)
- [ ] T-4.8: Operator gate — manual inspection (agent: manual)

### Phase 5: Corpus scale-out (41 skills, 6 waves)

Gate: 46 corpora total; conform to JSONL shape test; aggregate pass-at-1 sane.

- [ ] T-5.1: Wave 1 (8 workflow tier-1) (agent: build)
- [ ] T-5.2: Wave 2 (8 enterprise) (agent: build)
- [ ] T-5.3: Wave 3 (8 meta) (agent: build)
- [ ] T-5.4: Wave 4 (8 specialized A) (agent: build)
- [ ] T-5.5: Wave 5 (8 specialized B) (agent: build)
- [ ] T-5.6: Wave 6 (final 1 + sweep): ai-ide-audit; revalidate Wave 1-5
  (agent: build)
- [ ] T-5.7: Verify corpus shape test green over all 46 (agent: verify)
- [ ] T-5.8: Verify aggregate pass-at-1 sane — no skill below 0.50
  (agent: verify)

### Phase 6: Operator review (manual, 50-min budget)

Gate: top-10 near-miss per skill reviewed; revisions committed; signed off.
Per D-127-07 human-in-the-loop guarantee.

Budget: 46 × 10 = 460 cases × 6 sec eyeball = 46 min. Cap 50 min.

- [ ] T-6.1: Operator opens each corpus, walks 8 near-miss cases, flags
  wrong-shaped (agent: manual)
- [ ] T-6.2: Operator commits revisions inline (agent: manual)
- [ ] T-6.3: After signoff, rerun corpus shape test (agent: verify)

### Phase 7: ai-eval --skill-set + ai-skill-tune integration

Gate: /ai-eval --skill-set works end to end; /ai-skill-tune consumes
baseline + LESSONS + Engram and outputs PR comment.

- [ ] T-7.1: Extend ai-eval SKILL.md with --skill-set mode; preserve four
  feature modes; ≤120 lines (agent: build)
- [ ] T-7.2: Update ai-skill-tune SKILL.md Phase 0.5: load corpora + LESSONS
  + Engram; Phase 5 outputs PR comment only; ≤120 lines (agent: build)
- [ ] T-7.3: Run mirror sync (agent: build)
- [ ] T-7.4: Verify count parity test green (agent: verify)

### Phase 8: CI workflow + baseline capture

Gate: skill-evals.yml triggers on PRs touching skills; runs --regression;
fails on >5pp regression; baseline captured.

- [ ] T-8.1: Author skill-evals.yml mirroring ci-check.yml patterns;
  timeout-minutes 25; single job invoking run_loop_skill_evals.py
  --skill all --regression (agent: build)
- [ ] T-8.2: Capture initial evals/baseline.json on integration HEAD; commit
  (agent: build)
- [ ] T-8.3: Smoke-test gate by intentional regression on throwaway branch;
  confirm fail; revert (agent: verify)
- [ ] T-8.4: Update docs/conformance-report.md with M6 baseline section
  (agent: build)
- [ ] T-8.5: Update manifest: sub-007 status shipped (agent: build)

## Phase Dependency Graph

P0 → P1 → P2 (RED) → P3 (GREEN) → P4 (pilot) → operator gate T-4.8 →
P5 (scale) → P6 (review 50min) → P7 (skills) → P8 (CI + baseline)

P4 → P5 gated by manual operator signoff at T-4.8. P5 → P6 also manual gate.

## TDD Pairing

- T-1.1 → T-1.2; T-1.4 → T-1.5
- T-2.1 → T-3.1, T-3.2, T-3.3, T-3.4 — canonical regression gate pair.
  Constraint: no edits to regression-gate test from T-2.1.

## Manual Tasks

- T-4.8: pilot corpus inspection
- T-6.1: top-10 near-miss review per skill (50-min budget)
- T-6.2: operator commits revisions

## Done Conditions

- [ ] evals/<skill>.jsonl ≥16 cases for 46 skills (46 files, 736 cases)
- [ ] Regression gate test green; gate fails on >5pp regression
- [ ] skill-evals.yml active on PRs touching skills
- [ ] evals/baseline.json captured at sub-007 close
- [ ] /ai-eval --skill-set mode works end to end
- [ ] /ai-skill-tune consumes baseline + LESSONS + Engram; PR-only output
- [ ] Operator signoff on T-4.8 + T-6.1 recorded in self-report

## Self-Report
[EMPTY -- populated by Phase 4]
