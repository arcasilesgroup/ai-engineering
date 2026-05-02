# Build Packet - HX-05 / T-4.2 / framework-events-snapshot-sequencing

## Task ID

HX-05-T-4.2-framework-events-snapshot-sequencing

## Objective

Encode safe sequencing for event-emitting validations, audit writers, and downstream report generation so hash-chain and derived-view integrity are preserved.

## Minimum Change

- keep `framework-events.ndjson` as the single audit writer family and reuse its lock as the snapshot barrier for authoritative task-ledger writes plus downstream `task_trace` append
- allow the authoritative task writer to append `task_trace` while already holding the framework-events lock instead of recursively reacquiring it
- make maintenance-report scorecard generation and recent-event counting read ledger plus event data under the same lock, so reducers observe a coherent before-or-after snapshot
- pin the sequencing contract with focused unit coverage over the write path and the reducer read path

## Verification

- `uv run pytest tests/unit/test_work_plane.py -k framework_events_lock tests/unit/test_skills_maintenance.py -k framework_events_lock -q`
- `uv run pytest tests/unit/test_event_plane_contract.py tests/unit/test_framework_observability.py tests/unit/test_harness_sequencing.py tests/unit/test_work_plane.py tests/unit/test_skills_maintenance.py tests/integration/test_skills_integration.py -q`