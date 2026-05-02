# Verify HX-04 T-3.1 Adapter Parity RED Tests

## Ordered Verification

1. `uv run pytest tests/unit/test_gate_adapter_parity.py -q`
   - `FAIL` (expected RED)

## Key Signals

- `gate pre-commit`, `gate pre-push`, and `gate all` still call the legacy `policy.gates.run_gate` path instead of the kernel-backed adapter path.
- Generated hooks still target the correct CLI boundary (`ai-eng gate ...`), so the remaining gap is in CLI/workflow-helper routing rather than hook script generation.
- `policy.gates.run_gate` still lacks an explicit deprecation warning, so the legacy path remains silent.