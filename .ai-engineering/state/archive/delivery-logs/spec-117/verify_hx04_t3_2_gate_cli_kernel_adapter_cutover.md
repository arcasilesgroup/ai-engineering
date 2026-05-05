# Verify HX-04 T-3.2 Gate CLI Kernel Adapter Cutover

## Ordered Verification

1. `uv run pytest tests/unit/test_gate_adapter_parity.py -q`
   - `PASS`
2. `uv run pytest tests/integration/test_cli_command_modules.py -q`
   - `PASS`
3. `uv run ai-eng validate -c manifest-coherence`
   - `PASS`

## Key Signals

- `gate pre-commit`, `gate pre-push`, and `gate all` now exercise the shared kernel adapter instead of the legacy `policy.gates.run_gate` branch.
- Generated hook commands remain stable at the CLI boundary (`ai-eng gate ...`), so the cutover stays parity-first rather than rewriting the external hook contract.
- The legacy gate engine now emits an explicit `DeprecationWarning`, making the remaining fallback path visible instead of silent.