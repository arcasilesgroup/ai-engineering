# Verify HX-01 T-4.2 Runtime Reader Cutover

## Ordered Verification

1. `uv run pytest tests/unit/test_state.py -k 'TestConstitutionPathResolver'`
   - `PASS`
2. `uv run pytest tests/unit/test_framework_context_loads.py -k 'root_constitution_is_preferred_when_present or nested_constitution_remains_compatibility_fallback'`
   - `PASS`
3. `uv run pytest tests/unit/test_lib_observability.py -k 'root_constitution_is_preferred_when_present or nested_constitution_remains_compatibility_fallback'`
   - `PASS`

## Key Signals

- Source-runtime constitution resolution now routes through `ai_engineering.state.control_plane.resolve_constitution_context_path(...)`.
- The stdlib hook observability libraries now use one helper edge each instead of duplicating inline fallback logic inside the event builder.
- A focused runtime search found no remaining Python readers still inlining the root-versus-workspace constitution fallback.