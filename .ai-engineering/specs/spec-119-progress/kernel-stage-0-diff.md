# Stage 0 Insertion Diff — apply manually to `.claude/skills/_shared/execution-kernel.md`

Locate the heading `## Sub-flow 2: Build-verify-review loop (per task)` and replace the section through the end of the "If either stage fails" paragraph with:

```markdown
## Sub-flow 2: Build-verify-review loop (per task)

After the dispatched agent completes, run a behavioural-eval pass first, then two-stage review on the deliverable BEFORE marking the task DONE.

### Stage 0 -- Behavioural evaluation (spec-119 D-119-06)

Dispatch `ai-evaluator` against the build Context Output Contract. The evaluator runs the manifest-configured scenario packs through deterministic graders, computes pass@k via `ai_engineering.eval`, and returns a Scorecard verdict (`GO`, `CONDITIONAL`, `NO_GO`, `SKIPPED`).

- **GO**: continue to Stage 1.
- **CONDITIONAL**: continue to Stage 1; surface the regression delta to the consumer for visibility.
- **NO_GO**: short-circuit. Mark the task `BLOCKED` with reason `eval_no_go` and STOP. Do not run Stage 1 / Stage 2 -- there is no point validating layer violations on code that does not run.
- **SKIPPED**: only valid when the manifest sets `evaluation.enforcement: advisory`, when no scenario packs apply to the deliverable, or when the consumer passes `--skip-eval-gate` (audited via `eval_run/eval_gated` event with `verdict: SKIPPED`).

Telemetry: every Stage 0 invocation emits a structured `eval_run` event sequence -- one `eval_started`, N `scenario_executed`, one `pass_at_k_computed`, one `eval_gated`. See `.ai-engineering/scripts/hooks/_lib/observability.py` `emit_eval_*` helpers.

### Stage 1 -- Spec compliance
- Deliverable matches the task description?
- Acceptance criteria from `spec.md` satisfied?
- File-scope boundaries respected (no out-of-scope changes)?

### Stage 2 -- Code quality
- Stack validation passes (`ruff`, `tsc`, `cargo check`, `dotnet build`, etc.)
- No new lint warnings introduced
- Test coverage maintained or improved
- No governance advisory warnings from `ai-guard`
- Lint findings emitted as structured envelopes per `.ai-engineering/schemas/lint-violation.schema.json` (spec-119 D-119-05) -- prose violation labels are deprecated.

If any stage fails: dispatch a fix attempt and re-review. Max 2 retries per stage. After 2 failed retries, mark task BLOCKED and STOP execution -- never loop silently, never retry the same approach more than twice.
```

This insertion was prepared by spec-119 T-2.3 but blocked from autonomous edit by the harness safety policy on shared kernel files. Apply during a maintainer review pass.
