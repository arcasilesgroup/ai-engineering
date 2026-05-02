# Build Packet - HX-05 / T-3.2 / canonical-event-contract-cutover

## Task ID

HX-05-T-3.2-canonical-event-contract-cutover

## Objective

Implement the canonical event contract and adapt all supported writers through one shared state-layer seam without adding a second audit log or chain field.

## Minimum Change

- add canonical engine normalization and event-kind allowlists in runtime `state.event_schema` and `state.observability`, plus the mirrored hook-local libraries
- normalize active and template Copilot, Codex, Gemini, and telemetry hook writers onto the canonical contract, replacing `skill_invoked_malformed` with canonical `ide_hook` warning events
- keep root `traceId` and `parentId` fields at the event root and preserve the single append-only `framework-events.ndjson` writer path
- tighten unit and integration coverage so runtime and live hook emitters stay parity-locked on canonical engines, kinds, and root trace fields

## Verification

- `uv run pytest tests/unit/test_event_plane_contract.py tests/unit/test_work_plane.py tests/unit/test_framework_emitters.py tests/unit/test_framework_observability.py tests/unit/hooks/test_telemetry_skill.py tests/integration/test_framework_hook_emitters.py -q`