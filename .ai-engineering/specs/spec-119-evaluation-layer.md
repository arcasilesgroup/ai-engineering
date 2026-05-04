---
spec: spec-119
title: Evaluation Layer - Generator/Evaluator Split, CI Eval Gates, pass@k Telemetry, Lint-as-Prompt
status: approved
effort: large
---

# Spec 119 - Evaluation Layer

## Summary

ai-engineering exposes only one weak evaluation surface today: the `ai-eval` skill at `.claude/skills/ai-eval/SKILL.md` is pure prose-instructional. It defines four modes (`define`, `check`, `report`, `regression`) but emits zero telemetry, runs no automated harness, has no scenario pack runner, and computes pass@k by manual model arithmetic. The `ai-verify` skill dispatches four specialists (`verify-deterministic`, `verifier-governance`, `verifier-architecture`, `verifier-feature`) but they validate static well-formedness — they do not validate that output behaves correctly end-to-end. spec-117 added `build_replay_outcome()`, `summarize_replay_outcomes()`, and `build_reliability_scorecard()` to `src/ai_engineering/`, but no agent, hook, or skill calls them. The audit-event schema declares twelve event kinds; none are eval-related. The manifest declares `quality:` and `gates:` sections; neither contains eval thresholds. The `.ai-engineering/evals/` directory does not exist on disk.

This spec closes the Evaluation Layer with four coordinated additions, anchored in the existing audit chain, manifest contract, and Constitution Article V SSOT:

1. **Generator/Evaluator split**: a new `ai-evaluator` agent at `.claude/agents/ai-evaluator.md` (canonical) plus mirrors. It receives the Generator (`ai-build`) Context Output Contract, runs k-trial scenarios against the deliverable, and emits structured pass@k results. Plug-in point is the execution-kernel sub-flow 2 (`build-verify-review`), between build output and `ai-verify` static gates.
2. **CI eval gates**: a new `/ai-eval-gate` skill that reads thresholds from `manifest.yml` (`evaluation:` section), runs eval scenarios, and returns a structured GO / CONDITIONAL GO / NO-GO verdict. Wires into `/ai-pr` pre-merge and `/ai-release-gate` to block deploy when pass@k or hallucination-rate thresholds fail.
3. **pass@k telemetry**: a single new audit event kind `eval_run` discriminated by `detail.operation`, mirroring the spec-118 `memory_event` precedent. New `emit_eval_*` helpers in `observability.py`. The spec-117 library functions (`build_replay_outcome`, `summarize_replay_outcomes`, `build_reliability_scorecard`) become the runtime engine consumed by `ai-evaluator`, not stranded library code.
4. **Lint-as-prompt**: a structured violation envelope `{rule_id, expected, actual, fix_hint, file?, line?, severity}` replacing the prose-only "violation detected" / "deviation" strings used by `ai-code/handlers/compliance-trace` and other compliance reporters. Generators receive actionable diffs, not labels.

## Goals

- Make `pass@k` a measured, telemetry-emitted, gate-enforceable signal across the framework — not a documented concept.
- Provide a Generator/Evaluator dispatch path so `ai-build` output is validated end-to-end (does it work?) before `ai-verify` validates static gates (is it well-formed?).
- Add CI eval gates that read `manifest.yml` thresholds and block merge/deploy on regression, mirroring the existing `/ai-release-gate` 8-dimension verdict pattern.
- Replace prose violation messages with structured envelopes that downstream Generators can act on without LLM reformatting (Codex-paper "lint-as-prompt").
- Wire the spec-117 pass@k library functions (`build_replay_outcome`, `summarize_replay_outcomes`, `build_reliability_scorecard`) into a runtime dispatch path; eliminate stranded library code.
- Preserve the audit chain: one new event kind, sub-typed via `detail.operation`, full schema coverage in `audit-event.schema.json` and `_ALLOWED_KINDS`.
- Preserve hot-path discipline: eval gate execution belongs in CI, not pre-commit. Local pre-push budget < 5s remains intact.
- Preserve human authority: `ai-evaluator` proposes regression artefacts; only `/ai-eval` mode `regression` (human invocation) updates `baseline.json`.
- Run cross-IDE: agent + skills propagate through `ai-eng sync-mirrors` to `.gemini/`, `.codex/`, `.github/`.

## Non-Goals

- LLM-as-judge evaluation (v1 uses deterministic graders: pytest, Playwright, regex assertions, JSON schema match). LLM grading is follow-up work and would need its own bias/calibration spec.
- Adversarial / red-team eval scenarios (covered by `/ai-security`, not duplicated here).
- Continuous online evaluation in production (this spec covers pre-merge / pre-release / per-build gates only).
- Replacement of `ai-verify` (verify validates static well-formedness; eval validates behavioural correctness — both run, both required).
- Replacement of `ai-eval` skill (it remains as the human-facing authoring surface for scenario packs and reports; `ai-eval-gate` and `ai-evaluator` consume what it produces).
- Cross-IDE bridge edits for Copilot/Gemini eval-gate synthesis (Phase 6 lands Claude canonical first; mirrors track via sync-mirrors only).
- Encryption of `evals/baseline.json` (relies on host filesystem encryption; documented assumption).

## Decisions

### D-119-01: One new audit event kind `eval_run`, discriminated by `detail.operation`

`_ALLOWED_KINDS` in `.ai-engineering/scripts/hooks/_lib/observability.py` gains the value `eval_run`. Sub-operations live in `detail.operation`: `eval_started`, `scenario_executed`, `pass_at_k_computed`, `hallucination_rate_computed`, `regression_detected`, `regression_cleared`, `eval_gated`, `baseline_updated`. `audit-event.schema.json` gets a matching `$defs/detail_eval_run` and an `allOf` discriminated branch.

**Rationale**: Eight new top-level kinds would inflate the union for a single subsystem. The spec-118 `memory_event` precedent (D-118-01) and the existing `framework_operation` precedent both establish sub-typing via `detail.operation` as the framework's preferred pattern. Keeping `_ALLOWED_KINDS` small protects the audit chain from churn while still letting consumers filter by sub-operation.

### D-119-02: `ai-evaluator` is a separate agent, not a verifier specialist

A new agent file at `.claude/agents/ai-evaluator.md` (canonical) — distinct from the four `verify-*` and `verifier-*` agents. It runs in the execution-kernel sub-flow 2 between `ai-build` and `ai-verify`, not as part of the verify dispatch.

**Rationale**: `ai-verify` answers "is this code well-formed against framework standards?" (static well-formedness, layer violations, governance, spec coverage). `ai-evaluator` answers "does this code do what the spec says it should do?" (behavioural correctness, k-trial reliability, regression vs baseline). Conflating them weakens both: verify becomes too slow, eval becomes too narrow. The Anthropic Generator/Evaluator pattern (cited 11/12 in source NotebookLM) requires the Evaluator to be a peer of the Generator, not a child of the static-gate dispatcher.

### D-119-03: DeepEval as the Python eval framework

Add `deepeval>=2.0,<3.0` to `[project.optional-dependencies].dev` in `pyproject.toml`. Use DeepEval's `evaluate()` and `LLMTestCase` primitives where LLM grading lands as follow-up; for v1, use DeepEval's deterministic graders (regex match, JSON schema, exact match) to avoid the calibration question.

**Rationale**: Survey of the four major frameworks (Ragas, TruLens, DeepEval, Braintrust) shows DeepEval is Python-first, has the smallest dependency surface, supports both deterministic and LLM graders behind one API, and has a CI-friendly CLI. Ragas leans heavily on LLM grading and pulls in OpenAI SDK by default. TruLens requires a backend service. Braintrust is SaaS-first. DeepEval slots into the existing pytest harness with minimal disruption.

### D-119-04: Eval thresholds live in `manifest.yml` under a new top-level `evaluation:` section

```yaml
evaluation:
  pass_at_k:
    k: 5
    threshold: 0.8
  hallucination_rate:
    max: 0.1
  regression_tolerance: 0.05
  scenario_packs:
    - .ai-engineering/evals/baseline.json
  enforcement: blocking  # blocking | advisory
```

**Rationale**: The existing `quality:` section covers static metrics (coverage, duplication, complexity). The existing `gates:` section covers pre-commit mode. Eval thresholds are a third concern with their own enforcement semantics (advisory vs blocking) and benefit from a dedicated section. Placement under `manifest.yml` (not a sidecar `evals.yml`) preserves single-source-of-truth and lets `/ai-release-gate` aggregate eval status alongside the other 8 dimensions through one read.

### D-119-05: Lint-as-prompt structured envelope schema

Compliance reporters and skill handlers emit violations as objects, not prose:

```json
{
  "rule_id": "logger-structured-args",
  "severity": "error",
  "expected": "logger.info({event, ...data})",
  "actual": "console.log(`event=${event}`)",
  "fix_hint": "Replace console.log with logger.info passing a structured object",
  "file": "src/auth/login.ts",
  "line": 42
}
```

JSON Schema definition lands at `.ai-engineering/schemas/lint-violation.schema.json`. Existing compliance reporters in `.claude/skills/ai-code/handlers/compliance-trace.md` and any other "violation detected" / "deviation" call sites are updated to emit the structured form. Markdown rendering (for human review) is a derived view, not the canonical form.

**Rationale**: The Codex paper finding that "structured violation envelopes outperform prose violation labels" is empirically grounded: Generator agents reformat prose into actions and frequently mis-paraphrase the rule. A structured `{rule_id, expected, actual, fix_hint}` is directly consumable by the Generator. Severity and file:line make the envelope CI-actionable. Choosing JSON over YAML matches the existing audit-event schema convention.

### D-119-06: Plug-in point = execution-kernel sub-flow 2 (`build-verify-review`)

The execution kernel at `.claude/skills/_shared/execution-kernel.md` defines per-task flow as `dispatch → build-verify-review → artifact collection → board sync`. The `build-verify-review` sub-flow is where `ai-evaluator` is inserted: after `ai-build` produces its Context Output Contract, before `ai-verify` and `ai-review` run their static gates. Order is `ai-build → ai-evaluator → (ai-verify || ai-review parallel)`.

**Rationale**: Inserting before `ai-verify` means evaluator failure can short-circuit the static gate work — no point validating layer violations on code that doesn't run. Inserting after `ai-build` means evaluator sees the actual deliverable, not the spec. The kernel's existing dispatch / build-verify-review / artifact / board-sync segmentation makes this a one-line insertion in the kernel doc.

### D-119-07: Reuse spec-117 pass@k library functions; do not reimplement

The `build_replay_outcome()`, `summarize_replay_outcomes()`, and `build_reliability_scorecard()` functions added under spec-117 T-3.3 (marked complete in `plan-117-hx-11-verification-and-eval-architecture.md`) are wired into `ai-evaluator` runtime. No reimplementation. If signatures need adjustment, the change lands in `src/ai_engineering/` and is verified against existing tests.

**Rationale**: spec-117 produced eval primitives but never wired them. Reimplementing duplicates code and creates SSOT violations. Wiring the existing primitives validates the spec-117 work and gives the new agent a tested foundation.

### D-119-08: `.ai-engineering/evals/` is gitignored at the user level; scenario packs are committed

The runtime eval state (run logs, last-N pass@k history, working baseline) is gitignored. Scenario packs (`baseline.json`, scenario YAML/JSON definitions) are committed source-of-truth. Layout:

```
.ai-engineering/evals/
├── baseline.json            # committed (per-project SSOT)
├── scenarios/               # committed (one file per scenario pack)
│   ├── core-skills.json
│   └── ...
├── runs/                    # gitignored (per-machine history)
│   └── 2026-05-04T*.json
└── .gitignore               # commits this file; ignores runs/
```

**Rationale**: Scenario definitions are project intent and must be reviewed in PRs. Run results are observation and would create merge churn if committed. The split mirrors the existing `tests/` / `htmlcov/` convention.

## Concerns and Phased Delivery

This spec resolves four independent concerns. Each is independently dispatchable but shares the manifest schema and audit-event additions, so Concern A delivers schema and helpers as a foundation wave.

### Concern A — Telemetry foundation (foundation wave, no dependencies)

- A1. Add `eval_run` to `_ALLOWED_KINDS` in three observability.py copies (canonical + 2 mirrors via spec-118 D-118-04 SSOT pattern).
- A2. Add `$defs/detail_eval_run` plus discriminated `allOf` branch to `audit-event.schema.json`.
- A3. Add `emit_eval_started`, `emit_scenario_executed`, `emit_pass_at_k_computed`, `emit_hallucination_rate_computed`, `emit_regression_detected`, `emit_regression_cleared`, `emit_eval_gated`, `emit_baseline_updated` helpers to `observability.py`. Each calls `append_framework_event` with `kind="eval_run"` and the appropriate `detail.operation`.
- A4. Add `evaluation:` top-level section to `manifest.yml` with the schema from D-119-04. Update manifest JSON schema if one exists; add validation tests.
- A5. Add `lint-violation.schema.json` per D-119-05.
- A6. Add `deepeval>=2.0,<3.0` to `pyproject.toml` dev deps. Verify install in CI smoke job.

### Concern B — `ai-evaluator` agent (depends on A1-A3)

- B1. Author `.claude/agents/ai-evaluator.md` following the existing agent contract pattern (frontmatter, role, inputs, outputs, dispatch surface).
- B2. Wire spec-117 `build_replay_outcome`, `summarize_replay_outcomes`, `build_reliability_scorecard` as the agent's runtime engine.
- B3. Insert `ai-evaluator` in `.claude/skills/_shared/execution-kernel.md` sub-flow 2, between `ai-build` and `ai-verify`.
- B4. Update `.claude/agents/ai-build.md` Context Output Contract section to specify the deliverable hand-off to `ai-evaluator`.
- B5. Sync mirrors via `ai-eng sync-mirrors` to `.gemini/`, `.codex/`, `.github/`.
- B6. Add agent tests under `tests/agents/test_ai_evaluator.py` covering: receives build contract, runs k-trial, emits pass@k event, returns structured verdict.

### Concern C — `/ai-eval-gate` skill (depends on A4 manifest section + B agent)

- C1. Author `.claude/skills/ai-eval-gate/SKILL.md`. Modes: `check` (compute current run vs threshold), `report` (markdown verdict), `enforce` (exit code 0/1 for CI).
- C2. Wire skill into `/ai-pr` pre-merge sequence (after `/ai-verify`, before `gh pr create`).
- C3. Wire skill into `/ai-release-gate` as the 9th dimension (existing 8: coverage, security, tests, lint, dependencies, types, docs, packaging).
- C4. Add `evals/` directory scaffolding (D-119-08): `.gitignore`, `scenarios/.gitkeep`, `runs/.gitkeep`, seed `baseline.json` with empty scenario list and schema marker.
- C5. Add skill tests under `tests/skills/test_ai_eval_gate.py`.

### Concern D — Lint-as-prompt rollout (depends on A5 schema)

- D1. Update `.claude/skills/ai-code/handlers/compliance-trace.md` (and `.github/skills/...` mirror) to emit structured violations per D-119-05.
- D2. Audit all skill handlers and hooks for prose violation strings (`grep -rn "violation detected\|violation found\|policy violation\|deviation"` across `.claude/`, `.github/`, `.ai-engineering/scripts/`); update each call site to the structured envelope.
- D3. Add a markdown renderer at `src/ai_engineering/lint_violation_render.py` that converts a list of structured envelopes to a human-readable table for skill output.
- D4. Update `/ai-review` and `/ai-verify` to consume structured envelopes instead of prose strings where they currently re-parse violation labels.
- D5. Add tests under `tests/lint/test_violation_envelope.py` covering schema conformance and renderer round-trip.

## Acceptance Criteria

- `eval_run` appears in `_ALLOWED_KINDS` (canonical + 2 mirrors) and in `audit-event.schema.json` with all 8 sub-operations validated.
- `manifest.yml` has the `evaluation:` section with the schema from D-119-04; manifest schema validation passes.
- A representative `ai-evaluator` invocation against a sample build produces:
  - One `eval_started` event,
  - N `scenario_executed` events (where N = scenarios in pack),
  - One `pass_at_k_computed` event with `detail.k`, `detail.pass_count`, `detail.total`, `detail.score`,
  - One `eval_gated` event with `detail.verdict ∈ {GO, CONDITIONAL, NO_GO}`.
- `/ai-eval-gate enforce` exits non-zero when current run pass@k drops below threshold by more than `regression_tolerance`.
- `/ai-pr` blocks merge on `/ai-eval-gate` NO_GO unless the user passes `--skip-eval-gate` (which is logged to audit chain).
- `/ai-release-gate` integrates eval as a 9th dimension; verdict aggregation handles the new dimension correctly.
- All compliance reporter call sites emit structured envelopes; `grep -rn "violation detected"` returns zero runtime hits (only documentation prose remains).
- `tests/` suite passes with new tests under `tests/agents/`, `tests/skills/`, `tests/lint/`. Coverage for new code at or above `manifest.quality.coverage` threshold.
- `ai-eng sync-mirrors --check` reports zero drift after agent + skill additions.
- spec-117 library functions (`build_replay_outcome`, `summarize_replay_outcomes`, `build_reliability_scorecard`) are imported by `ai-evaluator` runtime; no duplicated implementation.
- Hot-path budget unchanged: pre-commit `<` 1s, pre-push `<` 5s. Eval gate runs in CI, not pre-commit.

## Risks

- **DeepEval dependency weight**: Adding `deepeval` pulls a non-trivial dependency tree. Mitigation: place under `optional-dependencies.dev`, not core; verify cold install time in CI; document the install gate in `/ai-start`.
- **Wiring spec-117 functions**: T-3.3 is marked complete in plan, but unverified. If signatures or semantics differ from what `ai-evaluator` needs, scope creeps into spec-117 amendment. Mitigation: foundation wave A1-A6 includes a spike to read the actual function signatures and adjust this spec before B kicks off.
- **Scenario authoring burden**: Eval gates are only as good as their scenario packs. Empty `baseline.json` means no real signal. Mitigation: seed `baseline.json` with three reference scenarios (one per highest-traffic skill: `/ai-build`, `/ai-plan`, `/ai-review`) as part of C4.
- **Lint-as-prompt churn**: D2 audit may surface dozens of call sites. If the count is high, D becomes its own multi-task wave. Mitigation: B and C can ship without D; D rollout phases per call site batch.

## Success Metrics

- pass@k for the three seed scenarios is measured and emitted to `framework-events.ndjson` on every `ai-build` invocation.
- Within four sprints of merge, at least one regression is caught by `/ai-eval-gate` before reaching main (validates the gate is doing work).
- Lint-as-prompt envelopes reduce Generator reformatting loops by a measurable amount in `framework-events.ndjson` (operationalised as: count of `framework_error` events with kind `parse_violation_label` drops to zero post-D).
- spec-117 library functions transition from "implemented but unused" to "imported by `ai-evaluator`" as verified by static import grep.
