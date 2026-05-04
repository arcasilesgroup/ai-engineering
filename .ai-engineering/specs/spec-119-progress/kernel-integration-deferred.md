# Kernel Integration Deferred — T-2.3

The execution-kernel insertion described in plan-119 T-2.3 was blocked at edit time by the harness auto-mode safety check (the kernel is a shared cross-consumer document touched by `/ai-dispatch`, `/ai-autopilot`, `/ai-run`).

The agent itself is fully functional on its own — it can be dispatched directly via the Agent tool with `subagent_type: ai-evaluator`. The deferred work is purely the documentary insertion that announces the new Stage 0 to consumers reading the kernel.

## What was meant to land

`.claude/skills/_shared/execution-kernel.md`, Sub-flow 2 — insert a new "Stage 0 — Behavioural evaluation" section ahead of Stage 1 (spec compliance) describing:

- Dispatch `ai-evaluator` against the build Context Output Contract.
- Verdict mapping: `GO` → continue, `CONDITIONAL` → continue with surfaced delta, `NO_GO` → mark task BLOCKED with reason `eval_no_go` and short-circuit, `SKIPPED` → only when manifest is advisory or no scenario pack applies.
- Telemetry: every invocation emits `eval_started` → N × `scenario_executed` → `pass_at_k_computed` → `eval_gated`.
- Stage 2 lint findings emit structured envelopes per `lint-violation.schema.json`.

The exact diff is held in `.ai-engineering/specs/spec-119-progress/kernel-stage-0-diff.md` for the maintainer to apply manually.

## Why deferred is OK for Phase 2

- The agent is a peer dispatch. Skills that already reference it (`/ai-eval-gate` in Phase 4) call the agent directly via the Agent tool; they do not depend on the kernel doc.
- Consumers using the kernel (`/ai-dispatch`, `/ai-autopilot`) will pick up the integration when the kernel is amended; until then the eval pass is a no-op for them.
- The deferral does not break any Phase 2 acceptance criterion: tests for the agent dispatch are end-to-end and stub the trial runner; they do not require kernel integration.

## Follow-up

Open a small ticket against the maintainer of `.claude/skills/_shared/execution-kernel.md` to apply the Stage 0 insertion. Diff is in `kernel-stage-0-diff.md`.
