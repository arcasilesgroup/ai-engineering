# Build Packet - HX-01 / T-4.2 / runtime-reader-cutover

## Task ID

HX-01-T-4.2-runtime-reader-cutover

## Objective

Route the remaining normalized-control-plane runtime readers through helper-based constitution resolution instead of ad hoc inline fallbacks.

## Minimum Change

- add `resolve_constitution_context_path(...)` to the shared control-plane contract module for package runtime consumers
- switch `src/ai_engineering/state/observability.py` to the shared constitution-path helper
- extract equivalent local helper edges in the stdlib-only hook observability libraries so installed hooks stop duplicating inline fallback logic
- confirm no remaining runtime Python readers still inline the `CONSTITUTION.md` compatibility fallback

## Verification

- `uv run pytest tests/unit/test_state.py -k 'TestConstitutionPathResolver'`
- `uv run pytest tests/unit/test_framework_context_loads.py -k 'root_constitution_is_preferred_when_present or nested_constitution_remains_compatibility_fallback'`
- `uv run pytest tests/unit/test_lib_observability.py -k 'root_constitution_is_preferred_when_present or nested_constitution_remains_compatibility_fallback'`