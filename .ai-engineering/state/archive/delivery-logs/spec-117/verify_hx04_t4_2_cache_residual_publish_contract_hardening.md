# Verify HX-04 T-4.2 Cache Residual Publish Contract Hardening

## Ordered Verification

1. `uv run pytest tests/unit/test_kernel_publish_contract.py`
   - `PASS`
2. `uv run pytest tests/unit/test_watch_residuals_emit.py tests/unit/test_harness_sequencing.py tests/integration/test_gate_findings_persisted.py tests/unit/test_cli_gate_run_flags.py`
   - `PASS`
3. `uv run ai-eng validate -c manifest-coherence`
   - `PASS`

## Key Signals

- Canonical findings and residual siblings now share one publish helper instead of keeping parallel atomic-write implementations that could drift in cache-field or schema handling.
- `gate` remains the explicit adapter publish owner, but it now delegates to the shared helper rather than keeping a second durable-artifact implementation.
- `watch_residuals` keeps compatibility for arbitrary override destinations while routing the real canonical residual sibling through the same publish contract as `gate-findings.json`.