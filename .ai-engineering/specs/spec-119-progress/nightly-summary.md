# spec-119 — Nightly Run Summary

**Date**: 2026-05-04 (overnight autonomous run)
**Duration**: ~one session of autonomous execution
**Pipeline**: full (5 phases, 36 planned tasks)
**Result**: runtime layer fully landed; documentation surface inside `.claude/` deferred behind harness auto-mode safety policy

---

## What landed (committed under spec-119)

### Telemetry foundation (Phase 1)
- New audit-event kind `eval_run` registered across:
  - `_ALLOWED_KINDS` in canonical hook (`.ai-engineering/scripts/hooks/_lib/observability.py`)
  - `ALLOWED_EVENT_KINDS` in Python validator (`src/ai_engineering/state/event_schema.py`)
  - Both install-template mirrors under `src/ai_engineering/templates/`
- Eight discriminated sub-operations encoded in `audit-event.schema.json`: `eval_started`, `scenario_executed`, `pass_at_k_computed`, `hallucination_rate_computed`, `regression_detected`, `regression_cleared`, `eval_gated`, `baseline_updated`
- Eight `emit_eval_*` helpers in canonical + template observability with verdict-aware outcome mapping (`NO_GO → failure`, `SKIPPED → degraded`, else `success`)
- Side-effect repair: `memory_event` (spec-118) added to the Python validator and the install templates — closes a parity gap that pre-dated this work
- New top-level `evaluation:` section in `manifest.yml` per D-119-04 (k=5, threshold=0.8, hallucination_rate.max=0.1, regression_tolerance=0.05, enforcement=blocking)
- Manifest JSON schema updated with the new `evaluation` block; the existing `gates` block was also added (parity repair — manifest had it; schema didn't)
- New `.ai-engineering/schemas/lint-violation.schema.json` per D-119-05
- New optional dependency extra `eval = ["deepeval>=2.0,<3.0"]` in `pyproject.toml` (kept off the core surface to protect cold-install times for hook scripts)
- New pytest markers `eval` and `eval_slow`

### Evaluation runtime engine (Phase 2 + Phase 4)
- Brand-new module `src/ai_engineering/eval/`:
  - `__init__.py` — public re-exports
  - `replay.py` — `ReplayOutcome`, `ReplaySummary`, `build_replay_outcome`, `summarize_replay_outcomes`
  - `pass_at_k.py` — HumanEval-formula `compute_pass_at_k`
  - `scorecard.py` — `Scorecard`, `Verdict`, `build_reliability_scorecard` (verdict mapping handles threshold + tolerance + hallucination together)
  - `regression.py` — `RegressionResult`, `detect_regression`, `regression_delta`
  - `thresholds.py` — `ManifestEvaluationConfig`, `load_evaluation_config` (yaml-safe; rejects bool-as-int, out-of-unit-interval values)
  - `runner.py` — scenario-pack runner glue, `filesystem_trial_runner` for the seed scenarios
  - `gate.py` — full `/ai-eval-gate` runtime: `run_gate`, `mode_check`, `mode_report`, `mode_enforce`, `to_json`, `_aggregate` (worst-verdict-wins)
- Stdlib-only at import time; deepeval is opt-in for follow-up LLM grading

### Lint-as-prompt (Phase 3)
- New canonical renderer `src/ai_engineering/lint_violation_render.py` with `render_table` (markdown) and `render_text` (single-line) helpers
- Audit confirmed all existing prose hits are documentation, not runtime emissions — the spec-119 acceptance criterion "zero runtime hits" is satisfied by absence

### Evals scaffolding
- `.ai-engineering/evals/` directory created per D-119-08:
  - `.gitignore` — ignores `runs/` only
  - `README.md` — pack schema and authoring contract
  - `baseline.json` — seed with three scenarios for `/ai-build`, `/ai-plan`, `/ai-review` artefacts
  - `scenarios/.gitkeep` and `runs/.gitkeep`

### Tests
- `tests/unit/eval/` — 81 new tests, all green:
  - `test_emit_eval_helpers.py` — 15 tests covering all 8 helpers + verdict mapping + hash-chain integrity
  - `test_eval_module.py` — 24 tests covering ReplayOutcome / pass@k / Scorecard / regression / threshold loader / runner end-to-end
  - `test_gate.py` — 11 tests covering all three modes + advisory enforcement + missing-pack handling + filesystem grader
  - `test_gate_smoke_canonical.py` — 2 tests running the gate against the real `manifest.yml` and `baseline.json`
  - `test_lint_renderer.py` — 8 tests
  - `test_lint_violation_schema.py` — 6 tests
  - `test_manifest_evaluation_section.py` — 15 tests covering manifest, audit-event schema, Python validator
- Total surface touched by spec-119 changes: 147 tests, all green

### Documentation
- `spec-119-evaluation-layer.md` (status: approved)
- `plan-119-evaluation-layer.md`
- `spec-119-progress/` containing:
  - `spike-spec-117-funcs.md`
  - `governance-review-phase-1.md`
  - `lint-audit.md`
  - `acceptance-evidence.md`
  - `nightly-summary.md` (this file)
  - `kernel-integration-deferred.md` + `kernel-stage-0-diff.md`
  - `proposed-ai-evaluator-agent.md`
  - `proposed-ai-eval-gate-skill.md`
  - `proposed-compliance-trace-update.md`

## What was deferred (and why)

The harness auto-mode safety policy denied autonomous edits to four classes of files:

1. `.claude/agents/ai-evaluator.md` — new agent file
2. `.claude/skills/_shared/execution-kernel.md` — Stage 0 insertion
3. `.claude/skills/ai-eval-gate/SKILL.md` — new skill file
4. `.claude/skills/ai-code/handlers/compliance-trace.md` — prose update

Auto mode treats `.claude/agents/` and `.claude/skills/` as the harness's own dispatch surface and refuses self-modification without explicit foreground approval. This is a deliberate and useful safety net — it prevented an autonomous run from rewriting how Claude itself dispatches subagents.

The deferred files are not blockers:
- The runtime engine (`src/ai_engineering/eval/`) is fully landed and tested.
- The eval gate works end-to-end as proven by `test_gate_smoke_canonical.py` running against the real repo.
- Final body for each deferred file is in `spec-119-progress/proposed-*.md` and ready to copy/paste.
- `ai-eng sync-mirrors --check` should be run after the maintainer applies the proposals so the IDE mirrors stay in sync.

## What you (Dachi) need to do this morning

1. **Skim `acceptance-evidence.md`** — confirms what landed, what deferred, evidence per acceptance criterion.
2. **Review the four `proposed-*.md` files** — these are ready-to-apply documents. The longest is `proposed-ai-evaluator-agent.md` (~150 lines).
3. **Apply the four proposals**:
   - Copy the agent body from `proposed-ai-evaluator-agent.md` into `.claude/agents/ai-evaluator.md`
   - Copy the skill body from `proposed-ai-eval-gate-skill.md` into `.claude/skills/ai-eval-gate/SKILL.md` and create `run.sh` from the proposal
   - Apply the kernel diff in `kernel-stage-0-diff.md` to `.claude/skills/_shared/execution-kernel.md`
   - Apply the compliance-trace prose update from `proposed-compliance-trace-update.md`
4. **Run `uv run ai-eng sync-mirrors`** — propagates the new agent + skill to `.gemini/`, `.codex/`, `.github/`, and the install-template mirrors
5. **Wire `/ai-eval-gate` into `/ai-pr` and `/ai-release-gate`** per the integration sections in `proposed-ai-eval-gate-skill.md` (those edits also touch `.claude/skills/`, hence deferred)
6. **Register `ai-eval-gate` in `manifest.yml::skills.registry`** alongside the existing 49 entries
7. **Spec-118 follow-up gap** noted: `ai-remember` and `ai-dream` skills are on disk but not in the manifest registry. Pre-existing failure surfaced by `test_skill_count_matches_manifest`. Out of scope for spec-119 but worth filing.

## Numbers

- Phases planned: 5
- Phases delivered (runtime + tests): 5
- Phases delivered (`.claude/` documentation surface): 0 (deferred)
- Tasks: 36 planned; ~28 fully delivered, ~8 produced as proposal documents under `spec-119-progress/`
- Files added: 27 (runtime + tests + spec + plan + progress notes)
- Files modified: 9 (manifest, schemas, observability, event_schema, hook-common template, observability template, pyproject, uv.lock)
- New tests: 81 (all green)
- Pre-existing failing tests: 23 (none introduced by spec-119; documented in `acceptance-evidence.md` § T-5.4)

## Commit

The final step of the run is `/ai-commit` per your instruction (you said "en vez de ai-pr haz un ai-commit"). Commit message follows the project's conventional-commit pattern:

```
feat(eval): land spec-119 evaluation layer runtime + telemetry foundation

- New audit-event kind eval_run with 8 sub-operations
- New ai_engineering.eval module (replay, pass@k, scorecard, regression, runner, gate)
- New lint-violation.schema.json + lint_violation_render.py
- New manifest evaluation section + manifest schema validation
- 81 new tests under tests/unit/eval (all green)
- Side-effect: memory_event parity repair across Python validator and templates

Generator/Evaluator dispatch + .claude/* documentation surface deferred behind
auto-mode safety policy; final bodies prepared as proposals under
.ai-engineering/specs/spec-119-progress/.
```

That's it. Sweet dreams; this was a clean, governance-respecting overnight run. 🎯
