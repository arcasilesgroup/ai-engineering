# Verify HX-04 T-3.3 Hook Entry Thin Adapter Cutover

## Ordered Verification

1. `uv run pytest tests/unit/test_gate_adapter_parity.py -q`
   - `PASS`
2. `uv run pytest tests/unit/test_gates.py tests/integration/test_gates_integration.py tests/integration/test_cli_command_modules.py -q`
   - `PASS`
3. `uv run ai-eng validate -c manifest-coherence`
   - `PASS`

## Key Signals

- `gate commit-msg` no longer routes through the generic legacy `policy.gates.run_gate` branch.
- The legacy gate wrapper still provides compatibility, but it delegates `commit-msg` through the dedicated adapter-owned path instead of retaining a generic hook-entry decision branch.
- Generated git hook scripts remain unchanged at the boundary (`ai-eng gate ...`), so the T-3.3 cutover tightened internals without rewriting the external hook contract.