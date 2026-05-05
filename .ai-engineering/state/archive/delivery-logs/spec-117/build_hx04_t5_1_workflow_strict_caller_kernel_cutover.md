# Build Packet - HX-04 / T-5.1 / workflow-strict-caller-kernel-cutover

## Task ID

HX-04-T-5.1-workflow-strict-caller-kernel-cutover

## Objective

Flip the remaining strict local workflow caller to the kernel-backed authority now that the parity and compatibility bundle is green.

## Minimum Change

- remove the last legacy `run_gate(GateHook.PRE_PUSH, ...)` usage from `commands.workflows`
- add one dedicated workflow pre-push kernel adapter that invokes the orchestrator in `ci` mode with the canonical cache path and CI attribution
- translate the kernel findings envelope back into workflow `StepResult` entries using the same medium-or-worse failure threshold the gate CLI already applies
- update workflow integration coverage to assert the workflow no longer falls back to the legacy gate engine and instead follows the canonical kernel CI registration names

## Verification

- `uv run pytest tests/integration/test_command_workflows.py -k pre_push_checks`
- `uv run pytest tests/integration/test_command_workflows.py tests/unit/test_workflow_cmd.py tests/unit/test_gate_adapter_parity.py -q`
- `uv run ai-eng validate -c manifest-coherence`