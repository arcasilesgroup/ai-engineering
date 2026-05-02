# Build Packet - HX-04 / T-3.3 / hook-entry-thin-adapter-cutover

## Task ID

HX-04-T-3.3-hook-entry-thin-adapter-cutover

## Objective

Move the remaining git-hook entry path onto a thin adapter and retire the last generic hook decision branch from the legacy gate engine while keeping generated hook scripts stable.

## Minimum Change

- add a focused parity test proving `gate commit-msg` must not route through the generic legacy `run_gate` wrapper
- route `gate commit-msg` through a dedicated thin adapter path in `cli_commands/gate.py`
- delegate the legacy `policy.gates.run_gate(..., COMMIT_MSG, ...)` path through the dedicated commit-msg adapter so the wrapper no longer owns that branch directly
- keep `hooks/manager.py` unchanged because generated hook scripts were already transport-only and still point at `ai-eng gate ...`

## Verification

- `uv run pytest tests/unit/test_gate_adapter_parity.py -q`
- `uv run pytest tests/unit/test_gates.py tests/integration/test_gates_integration.py tests/integration/test_cli_command_modules.py -q`
- `uv run ai-eng validate -c manifest-coherence`