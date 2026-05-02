# Verify HX-01 T-4.3 Targeted Verification

## Ordered Verification

1. `uv run ai-eng sync --check`
   - `PASS`
2. `uv run pytest tests/unit/test_template_parity.py -q`
   - `PASS`
3. `uv run ai-eng validate -c manifest-coherence`
   - `PASS`
4. `uv run pytest tests/unit/test_state.py::TestConstitutionPathResolver tests/unit/test_framework_context_loads.py::TestDeclaredContextLoads::test_root_constitution_is_preferred_when_present tests/unit/test_framework_context_loads.py::TestDeclaredContextLoads::test_nested_constitution_remains_compatibility_fallback tests/unit/test_lib_observability.py::TestEmitDeclaredContextLoads::test_root_constitution_is_preferred_when_present tests/unit/test_lib_observability.py::TestEmitDeclaredContextLoads::test_nested_constitution_remains_compatibility_fallback -q`
   - `PASS`

## Key Signals

- Live and template hook assets stayed in sync after the T-4.2 runtime-reader cutover.
- `manifest-coherence` passed with both generated projections matching their computed contracts and the normalized control-plane authority contract intact.
- The root-first constitution path and workspace-charter compatibility fallback both stayed green in the package runtime and the stdlib hook runtime.
- The only non-failing note in `manifest-coherence` remains the expected active-task-ledger warning for the current spec buffer.