# Verify HX-04 T-4.3 Targeted Verification Bundle

## Ordered Verification

1. `uv run pytest tests/unit/test_kernel_contract.py tests/unit/test_orchestrator_emit_findings.py tests/unit/test_gate_adapter_parity.py tests/unit/test_verify_service.py tests/unit/test_harness_sequencing.py tests/unit/test_kernel_publish_contract.py tests/unit/test_watch_residuals_emit.py tests/unit/test_framework_observability.py tests/unit/test_cli_sync.py tests/unit/test_cli_gate_run_flags.py tests/integration/test_gate_findings_persisted.py tests/integration/test_cli_command_modules.py tests/integration/test_orchestrator_cache_integration.py -q`
   - `PASS`

## Key Signals

- Kernel contract, findings envelope emit, adapter parity, downstream reporters, shared-artifact sequencing, shared publish behavior, residual-output compatibility, and cache integration all held together in one focused proof bundle.
- The verification bundle stayed inside `HX-04` ownership: it proved local convergence without pulling in `HX-05` state-vocabulary work or `HX-11` eval classification work.
- `HX-04` now has the parity proof required to start strict local-caller cutover in `T-5.1`.