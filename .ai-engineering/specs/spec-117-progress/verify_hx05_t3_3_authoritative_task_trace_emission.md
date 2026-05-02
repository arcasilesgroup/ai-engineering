# Verify HX-05 T-3.3 Authoritative Task Trace Emission

## Ordered Verification

1. `uv run pytest tests/unit/test_event_plane_contract.py tests/unit/test_work_plane.py tests/unit/test_framework_emitters.py tests/unit/test_framework_observability.py tests/unit/hooks/test_telemetry_skill.py tests/integration/test_framework_hook_emitters.py -q`
   - `PASS` (`50 passed`)

## Key Signals

- Runtime and hook-local observability now both expose canonical `emit_task_trace` helpers with the same root field and detail contract.
- `write_task_ledger(...)` appends `task_trace` events only when a task is new or its authoritative lifecycle phase or artifact refs change.
- Task-trace artifact refs come directly from task-ledger handoff and evidence refs, so the append-only view stays downstream of authoritative work-plane state instead of derived summaries.
- No generic kernel outcome was heuristically mapped onto a task id; task-trace emission remains constrained to explicit authoritative task mutations until a task-aware kernel surface exists.