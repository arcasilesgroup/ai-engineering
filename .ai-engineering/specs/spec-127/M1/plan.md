---
total: 28
completed: 0
---

# Plan: sub-002 M1 — Conformance rubric as code

## Pipeline: full
## Phases: 7
## Tasks: 28 (build: 22, verify: 5, guard: 1)

## Architecture

**Pattern**: Hexagonal (Ports & Adapters), four packages under `tools/`:
`skill_domain/` (pure), `skill_app/` (use cases + ports), `skill_infra/`
(adapters), `skill_lint/` (CLI shim). Layer rules enforced by M5
`tests/architecture/test_layer_isolation.py`; prefigured here by careful
imports.

**Justification**: D-127-09 layer-isolation; brief §22 split contract;
greenfield. Pure-Python domain keeps rubric testable in <1 ms per rule.

## Design

Skipped — internal tooling.

## Phase classification: full

New tooling (4 packages, 0 prior code). ≥10 files across `tools/` +
`tests/conformance/` + `pyproject.toml` + `docs/`. Conformance bar codified.

### Phase A: Scaffold

**Gate**: packages importable; layer rule documented.

- [ ] T-A.1: Create `tools/skill_domain/__init__.py` (empty docstring,
  `from __future__ import annotations`) (agent: build)
- [ ] T-A.2: Create `tools/skill_app/__init__.py` and `ports.py` with
  `ScannerPort`, `ReporterPort` `typing.Protocol` stubs (agent: build)
- [ ] T-A.3: Create `tools/skill_infra/__init__.py` (empty) (agent: build)
- [ ] T-A.4: Create `tools/skill_lint/__init__.py` and stub `cli.py` with
  `def main() -> int: return 0` (agent: build)
- [ ] T-A.5: Register console script `skill_lint = skill_lint.cli:main` in
  `pyproject.toml [project.scripts]`; add `tools/` to packages config
  (agent: build)
- [ ] T-A.6: `/ai-guard` advisory — confirm no domain→infra import in scaffold
  (agent: guard)

### Phase B: RED — Skills rubric tests

**Gate**: pytest collects, all 10 RED. TDD pair partner = umbrella T-2.10.

- [ ] T-B.1: Create `tests/conformance/__init__.py` and `conftest.py` (fixture
  `skills_root` → `.claude/skills/`) (agent: build)
- [ ] T-B.2: Write `tests/conformance/test_skills_rubric.py` — parametrized
  test class per brief §3 rule (10 rules): rule_1_frontmatter_valid,
  rule_2_third_person_cso_three_triggers, rule_3_negative_scoping,
  rule_4_line_and_token_budget, rule_5_required_sections,
  rule_6_examples_count, rule_7_refs_nesting_with_toc,
  rule_8_evals_present_threshold, rule_9_optimizer_committed,
  rule_10_no_anti_patterns. Asserts `LintSkillsUseCase(...).run()`; all FAIL
  (agent: build)
- [ ] T-B.3: Run `pytest tests/conformance/test_skills_rubric.py
  --collect-only` → MUST collect 10; full run produces 10 RED (agent: verify)

### Phase C: RED — Agents rubric tests

**Gate**: 5 RED tests collected. TDD pair partner = umbrella T-2.11.

- [ ] T-C.1: Write `tests/conformance/test_agents_rubric.py` — parametrized
  class with 5 rules: agent_rule_1 (CSO third-person), agent_rule_2 (`tools`
  whitelist), agent_rule_3 (`model: opus|sonnet`), agent_rule_4 (≥1
  dispatch-source ref in `.claude/skills/**/SKILL.md` or `AGENTS.md`),
  agent_rule_5 (no orphan). Asserts `LintAgentsUseCase(...).run()`; all FAIL
  (agent: build)
- [ ] T-C.2: Run collect-only → 5 tests; full run 5 RED (agent: verify)

### Phase D: GREEN — Domain rubric implementation

**Gate**: 15 conformance tests run; rubric grades current 50 skills correctly
(brief §2.1 baseline reproduced).

TDD pair partner = umbrella T-2.12. **GREEN constraint: DO NOT modify test
files under `tests/conformance/` from Phase B/C.**

- [ ] T-D.1: Implement `tools/skill_domain/skill_model.py` —
  `@dataclass(frozen=True) Frontmatter(name, description)`,
  `Skill(path, frontmatter, body, line_count, token_estimate, sections,
  examples_count, refs_paths, anti_pattern_hits)` (agent: build)
- [ ] T-D.2: Implement `tools/skill_domain/agent_model.py` —
  `Agent(path, frontmatter, tools, model, dispatched_by)` (agent: build)
- [ ] T-D.3: Implement `tools/skill_domain/rubric.py` — Rule abstraction
  (`name`, `predicate(skill) -> RubricResult(grade, reason)`); export
  `SKILL_RULES` (10) and `AGENT_RULES` (5). Pure stdlib, regex per Anthropic
  standard (`^[a-z0-9-]{1,64}$`, ≤1024 char description, banned substrings
  `claude`/`anthropic`, no XML tags) (agent: build)
- [ ] T-D.4: Implement `tools/skill_app/lint_skills.py` and `lint_agents.py` —
  accept `ScannerPort`, iterate output, apply rules, return
  `RubricReport(per_skill, per_agent, summary)` (agent: build)
- [ ] T-D.5: Run pytest → 15 tests assert rubric *runs and grades correctly*.
  Captured grade vector matches brief §2.1 (28 A / 14 B / 6 C / 1 D, 0/50
  examples) (agent: verify)

### Phase E: Infrastructure adapter + CLI

**Gate**: `--check` exits non-zero on baseline; `--baseline` writes report.

- [ ] T-E.1: Implement `tools/skill_infra/fs_scanner.py` — `FilesystemScanner`
  with `ThreadPoolExecutor(max_workers=8)` reading SKILL.md + agent .md in
  parallel (agent: build)
- [ ] T-E.2: Implement `tools/skill_infra/markdown_reporter.py` —
  `MarkdownReporter` formatting `RubricReport` to Markdown table (agent: build)
- [ ] T-E.3: Implement `tools/skill_lint/cli.py` — argparse with `--check`
  (exit 1 on any D, exit 2 on >2 C, exit 0 otherwise) and `--baseline` (writes
  report). Hot-path budget ≤200 ms via `time.perf_counter()` (agent: build)
- [ ] T-E.4: Run `python -m skill_lint --check` over 50 skills → expect exit 1
  (Grade D from `ai-entropy-gc`) (agent: verify)

### Phase F: Pre-commit wire (via ai-eng gate pre-commit registry)

**Gate**: `ai-eng gate pre-commit` invokes skill_lint within budget.

> Adjusted from umbrella T-2.14: repo has NO `.pre-commit-config.yaml`. Extend
> the gate's hook registry, not a YAML file.

- [ ] T-F.1: Locate pre-commit hook registry under `src/ai_engineering/`
  (likely `cli/gate.py` or `hooks/registry.py`); add `skill_lint --check` as
  parallel step (agent: build)
- [ ] T-F.2: Add `tests/unit/hooks/test_pre_commit_includes_skill_lint.py`
  asserting hook list contains `skill_lint --check` and is registered
  parallel (agent: build)
- [ ] T-F.3: Run `time ai-eng gate pre-commit` on clean tree; assert wall-time
  delta from `skill_lint --check` ≤200 ms (D-127-08) (agent: verify)

### Phase G: Baseline report + budget assertion

**Gate**: docs shipped, perf test green.

- [ ] T-G.1: Add `tests/perf/test_skill_lint_budget.py` — invokes `python -m
  skill_lint --check` via `subprocess.run`, asserts wall time ≤200 ms (with
  25 % CI tolerance per brief §14.3) (agent: build)
- [ ] T-G.2: Run `python -m skill_lint --baseline > /tmp/baseline.md`; copy
  into `docs/conformance-report.md` under `## M1 Baseline (2026-05-08)`
  (agent: build)
- [ ] T-G.3: Run full conformance suite → 15 tests GREEN; perf test GREEN;
  `docs/conformance-report.md` baseline section present (agent: verify)
- [ ] T-G.4: Self-report: paste exit codes, timing, grade vector into
  `## Self-Report` (agent: build)

## Phase Dependency Graph

```
A (scaffold) ──→ B (RED skills)  ──┐
              └→ C (RED agents) ──┴→ D (GREEN domain) ──→ E (CLI) ──→ F (pre-commit) ──→ G (baseline+perf)
```

B and C independent — may run in parallel. D depends on both — T-D.5 verifies
both test files together.

## TDD Pairing

| RED                | GREEN                                  | Constraint                                              |
| ------------------ | -------------------------------------- | ------------------------------------------------------- |
| T-B.2 (umbrella T-2.10) | T-D.1, T-D.3, T-D.4 (umbrella T-2.12) | DO NOT modify `tests/conformance/test_skills_rubric.py` |
| T-C.1 (umbrella T-2.11) | T-D.2, T-D.3, T-D.4              | DO NOT modify `tests/conformance/test_agents_rubric.py` |
| T-G.1 (perf RED)   | T-E.1, T-E.3                           | DO NOT modify `tests/perf/test_skill_lint_budget.py`    |

## Hot-path budget

`skill_lint --check` MUST complete ≤200 ms parallel walk over 50 skills
(D-127-08). Implementation guard: `ThreadPoolExecutor(max_workers=8)`, no
third-party deps, single regex pass for frontmatter, asserted by T-G.1.

## Done Conditions

- [ ] `tools/skill_domain/`, `skill_app/`, `skill_infra/`, `skill_lint/`
  packages exist with PEP 8 underscore names
- [ ] `pytest tests/conformance/` → 15 GREEN
- [ ] `python -m skill_lint --check` exits 1 on current 50 skills
- [ ] `--baseline` reproduces brief §2.1 grade vector
- [ ] `docs/conformance-report.md` ships with `## M1 Baseline` section
- [ ] `ai-eng gate pre-commit` invokes `skill_lint --check` ≤200 ms
- [ ] `tests/perf/test_skill_lint_budget.py` GREEN
- [ ] Domain layer has zero non-stdlib imports

## Self-Report
[EMPTY -- populated by Phase G T-G.4]
