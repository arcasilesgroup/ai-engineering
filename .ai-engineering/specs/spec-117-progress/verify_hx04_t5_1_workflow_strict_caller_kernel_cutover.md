# Verify HX-04 T-5.1 Workflow Strict Caller Kernel Cutover

## Ordered Verification

1. `uv run pytest tests/integration/test_command_workflows.py -k pre_push_checks`
   - `PASS`
2. `uv run pytest tests/integration/test_command_workflows.py tests/unit/test_workflow_cmd.py tests/unit/test_gate_adapter_parity.py -q`
   - `PASS`
3. `uv run ai-eng validate -c manifest-coherence`
   - `PASS`

## Key Signals

- The last remaining strict workflow caller no longer depends on `policy.gates.run_gate`; the workflow pre-push path now enters through the kernel-backed authority.
- Workflow step rendering stayed compatible by translating the findings envelope into `StepResult` entries keyed by the kernel’s canonical CI registration.
- Nearby adapter parity stayed green, so the workflow cutover did not reopen the already-closed gate CLI and hook adapter seams.