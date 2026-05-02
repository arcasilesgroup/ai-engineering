# Verify HX-05 T-3.1 Canonical Event Contract RED Tests

## Ordered Verification

1. `uv run pytest tests/unit/test_event_plane_contract.py tests/integration/test_framework_hook_emitters.py -q`
   - `FAIL` (expected RED)

## Key Signals

- `state.event_schema.validate_event_schema()` still accepts the noncanonical `skill_invoked_malformed` kind, so event-kind normalization is not enforced yet.
- Both runtime and hook-local observability builders still preserve the legacy `github_copilot` provider id instead of normalizing to the canonical `copilot` identifier.
- The Copilot hook emitters still write events with the legacy provider id; the root-field parity assertions are now in place so `traceId` preservation stays pinned while the adapter cutover lands.
- No runtime or hook-local `emit_task_trace` surface exists yet, so task traces remain entirely unimplemented going into `T-3.2` and `T-3.3`.