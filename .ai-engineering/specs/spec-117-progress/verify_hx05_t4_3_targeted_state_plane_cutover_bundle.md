# Verify HX-05 T-4.3 Targeted State Plane Cutover Bundle

## Ordered Verification

1. `uv run pytest tests/unit/test_state_plane_contract.py tests/unit/test_state_plane_artifact_paths.py tests/unit/test_event_plane_contract.py tests/unit/test_framework_observability.py tests/unit/test_harness_sequencing.py tests/unit/test_work_plane.py tests/unit/test_skills_maintenance.py tests/unit/hooks/test_telemetry_skill.py tests/integration/test_framework_hook_emitters.py tests/integration/test_skills_integration.py -q`
   - `PASS` (`92 passed`)

## Coverage Map

- `tests/unit/test_state_plane_contract.py`
  - durable versus derived versus residue classification contract
- `tests/unit/test_state_plane_artifact_paths.py`
  - canonical spec-local evidence pathing and compatibility shim resolution
- `tests/unit/test_event_plane_contract.py`
  - canonical event kinds, canonical engine normalization, and task-trace emitter parity
- `tests/unit/test_framework_observability.py`
  - runtime canonical framework-event builders and append behavior
- `tests/unit/test_harness_sequencing.py`
  - framework-events writer serialization contract
- `tests/unit/test_work_plane.py`
  - authoritative task-ledger mutation plus `task_trace` emission and sequencing
- `tests/unit/test_skills_maintenance.py`
  - derived task scorecard and maintenance-report reducer behavior
- `tests/unit/hooks/test_telemetry_skill.py`
  - hook-local telemetry/event emission contract
- `tests/integration/test_framework_hook_emitters.py`
  - runtime and template hook emitter integration parity
- `tests/integration/test_skills_integration.py`
  - maintenance report generation against installed-project layouts

## Key Signals

- The normalized HX-05 state plane now classifies authoritative, derived, residue, and spec-local evidence surfaces through executable contracts.
- Canonical events normalize provider IDs and kinds consistently across runtime and hook writers, with `task_trace` remaining an append-only downstream view.
- Maintenance scorecards remain derived and now read a coherent ledger plus framework-events snapshot instead of racing an in-flight append.
- The Phase 4 gate is fully proven, so the next slice can focus on strict consumer cutover rather than more contract discovery.