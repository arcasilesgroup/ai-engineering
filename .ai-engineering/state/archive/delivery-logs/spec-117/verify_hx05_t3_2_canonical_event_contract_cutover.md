# Verify HX-05 T-3.2 Canonical Event Contract Cutover

## Ordered Verification

1. `uv run pytest tests/unit/test_event_plane_contract.py tests/unit/test_work_plane.py tests/unit/test_framework_emitters.py tests/unit/test_framework_observability.py tests/unit/hooks/test_telemetry_skill.py tests/integration/test_framework_hook_emitters.py -q`
   - `PASS` (`50 passed`)

## Key Signals

- The shared event schema now rejects noncanonical event kinds such as `skill_invoked_malformed`.
- Runtime plus active and template hook writers normalize the legacy `github_copilot` provider id to canonical `copilot`.
- Codex, Gemini, and telemetry malformed prompt paths now emit canonical `ide_hook` warning events instead of bespoke bridge-only kinds.
- Runtime and live hook emitters stayed aligned on root `traceId` and `parentId` fields while continuing to write through the existing append-only `framework-events.ndjson` path.