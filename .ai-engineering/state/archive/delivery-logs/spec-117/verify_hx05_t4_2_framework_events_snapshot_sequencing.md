# Verify HX-05 T-4.2 Framework Events Snapshot Sequencing

## Ordered Verification

1. `uv run pytest tests/unit/test_work_plane.py -k framework_events_lock tests/unit/test_skills_maintenance.py -k framework_events_lock -q`
   - `PASS` (`2 passed, 25 deselected`)
2. `uv run pytest tests/unit/test_event_plane_contract.py tests/unit/test_framework_observability.py tests/unit/test_harness_sequencing.py tests/unit/test_work_plane.py tests/unit/test_skills_maintenance.py tests/integration/test_skills_integration.py -q`
   - `PASS` (`57 passed`)

## Key Signals

- `write_task_ledger(...)` now serializes the authoritative ledger write and any downstream `task_trace` append on the canonical `framework-events` lock.
- `append_framework_event(...)` supports the already-locked path, preserving the existing hash-chain writer while avoiding recursive locking.
- `maintenance.report` now reads task-ledger and framework-events inputs under the same snapshot barrier before deriving scorecards or counting recent events.
- Validation-emitted `control_outcome` and audit-writer events still use the same framework-events family, so report reducers now observe a coherent event stream instead of an interleaved partial append.