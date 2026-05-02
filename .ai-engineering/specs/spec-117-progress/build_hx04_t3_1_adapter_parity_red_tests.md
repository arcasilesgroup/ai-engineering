# Build Packet - HX-04 / T-3.1 / adapter-parity-red-tests

## Task ID

HX-04-T-3.1-adapter-parity-red-tests

## Objective

Write failing tests for gate CLI parity, hook adapter parity, workflow-helper parity, and legacy-engine deprecation behavior before adapter cutover begins.

## Minimum Change

- add focused adapter-parity RED tests for `gate pre-commit`, `gate pre-push`, `gate all`, and legacy `policy.gates.run_gate`
- keep one hook-generator invariant proving generated hooks still target the `ai-eng gate ...` CLI adapter boundary
- capture the current failure where CLI helpers still invoke the legacy gate engine and the legacy engine does not yet emit a deprecation warning

## Verification

- `uv run pytest tests/unit/test_gate_adapter_parity.py -q`