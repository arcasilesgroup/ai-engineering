# Build Packet - HX-05 / T-3.3 / authoritative-task-trace-emission

## Task ID

HX-05-T-3.3-authoritative-task-trace-emission

## Objective

Add first-class task-trace emission over authoritative task mutations without inventing task ids from derived reports or generic kernel outcomes.

## Minimum Change

- add canonical `emit_task_trace` helpers to runtime and hook-local observability so `task_trace` joins the shared event vocabulary instead of becoming a one-off writer path
- wire `state.work_plane.write_task_ledger(...)` to emit append-only task traces only for new or changed tasks, using the task ledger handoff and evidence refs as the authoritative artifact refs
- keep emission scoped to explicit task mutations and avoid heuristic task inference from generic kernel outcomes that do not carry authoritative task identity
- add focused unit coverage for writer-triggered task traces while preserving runtime and hook emitter parity

## Verification

- `uv run pytest tests/unit/test_event_plane_contract.py tests/unit/test_work_plane.py tests/unit/test_framework_emitters.py tests/unit/test_framework_observability.py tests/unit/hooks/test_telemetry_skill.py tests/integration/test_framework_hook_emitters.py -q`