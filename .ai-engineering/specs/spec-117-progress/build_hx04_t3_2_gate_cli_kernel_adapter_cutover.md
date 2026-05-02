# Build Packet - HX-04 / T-3.2 / gate-cli-kernel-adapter-cutover

## Task ID

HX-04-T-3.2-gate-cli-kernel-adapter-cutover

## Objective

Move the gate CLI helper commands and workflow-helper flow onto the shared kernel-backed execution path while preserving the generated hook boundary and making the legacy gate engine explicitly deprecated.

## Minimum Change

- route `gate pre-commit`, `gate pre-push`, and the `gate all` helper flow through a shared kernel adapter in `cli_commands/gate.py`
- keep generated hooks pointing at `ai-eng gate ...` so the boundary stays stable while the internals cut over
- add an explicit deprecation warning to `policy.gates.run_gate`
- update the nearby CLI command module tests to patch the new routing seam

## Verification

- `uv run pytest tests/unit/test_gate_adapter_parity.py -q`
- `uv run pytest tests/integration/test_cli_command_modules.py -q`
- `uv run ai-eng validate -c manifest-coherence`