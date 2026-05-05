# HX-02 T-5.1 Wave 1 Ledger-Aware Active Spec Gate - Exploration Handoff

## Current Anchor

- Owning seam: `src/ai_engineering/policy/orchestrator.py`
- Nearest decision points:
  - Wave 1 active-spec gate in `src/ai_engineering/policy/orchestrator.py`
  - Immediate caller in the same file that already has explicit `project_root`
- CLI reach already flows through this seam via `src/ai_engineering/cli_commands/gate.py`

## Local Hypothesis

Wave 1 still treats placeholder `spec.md` as the authoritative readiness gate. A resolved work plane with placeholder `spec.md` and a readable `task-ledger.json` containing any non-done task should still count as active for `spec-verify`.

## Recommended Next Slice

- Name the slice `wave1-ledger-aware-active-spec-gate`.
- Keep ownership inside `src/ai_engineering/policy/orchestrator.py`.
- Reuse `read_task_ledger(...)` and the resolved work plane instead of placeholder prose alone.
- Treat placeholder plus readable ledger with any non-done task as active.
- Preserve true idle behavior for placeholder plus empty or no-live ledger.
- Keep the change local to Wave 1 gating; do not widen into other runtime readers yet.

## Allowed Write Scope

- `src/ai_engineering/policy/orchestrator.py`
- `tests/unit/test_orchestrator_wave1.py`

## Failing-Test-First Candidate

- Add one pointer-aware unit test where the resolved work plane has placeholder `spec.md`, a readable ledger with one `in_progress` task, and explicit `project_root`; expect Wave 1 to invoke `spec-verify`.
- Keep the existing true-idle placeholder skip path green.

## Cheapest Validation

- `uv run pytest tests/unit/test_orchestrator_wave1.py -k ledger_aware_active_spec_gate -q`
- `uv run pytest tests/unit/test_orchestrator_wave1.py -q`

## Boundaries

- Do not touch validator code.
- Do not touch `src/ai_engineering/work_items/service.py` in this slice.
- Do not widen into CLI wrappers, resolver, models, or templates.