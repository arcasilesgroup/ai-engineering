# Build Packet - HX-05 / T-3.1 / canonical-event-contract-red-tests

## Task ID

HX-05-T-3.1-canonical-event-contract-red-tests

## Objective

Write failing tests for canonical provider IDs, event kinds, root event fields, task trace fields, and writer-path parity across runtime and hook emitters before the event-contract cutover begins.

## Minimum Change

- add focused RED coverage for canonical event-schema kind validation so bridge-only one-off kinds stop being silently accepted by the shared schema
- pin runtime and hook-local observability builders to the canonical `copilot` provider identifier when legacy `github_copilot` inputs are still flowing in
- tighten Copilot hook integration coverage so emitted events must preserve `traceId` at the root and stay aligned with the runtime event contract
- require a first-class `task_trace` emitter surface on both runtime and hook observability paths before task-trace emission work starts

## Verification

- `uv run pytest tests/unit/test_event_plane_contract.py tests/integration/test_framework_hook_emitters.py -q`