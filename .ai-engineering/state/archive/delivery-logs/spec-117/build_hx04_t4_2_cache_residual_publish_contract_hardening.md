# Build Packet - HX-04 / T-4.2 / cache-residual-publish-contract-hardening

## Task ID

HX-04-T-4.2-cache-residual-publish-contract-hardening

## Objective

Tighten cache, residual-output, and publish-path behavior so canonical kernel siblings cannot drift away from their expected durable-artifact contract.

## Minimum Change

- add one shared `publish_gate_document(...)` helper under `policy.orchestrator` for canonical `.ai-engineering/state/*.json` findings siblings
- delegate `gate` findings persistence to that helper instead of keeping a second publish implementation in `cli_commands.gate`
- route canonical `watch-residuals.json` emission through the same helper while preserving the existing atomic override-path fallback for arbitrary test or tool destinations
- pin the contract with focused tests that require cache metadata to survive publication and require both `gate` and `watch_residuals` to delegate to the shared helper

## Verification

- `uv run pytest tests/unit/test_kernel_publish_contract.py tests/unit/test_watch_residuals_emit.py tests/unit/test_harness_sequencing.py tests/integration/test_gate_findings_persisted.py tests/unit/test_cli_gate_run_flags.py`
- `uv run ai-eng validate -c manifest-coherence`