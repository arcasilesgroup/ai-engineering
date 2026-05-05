# Build Packet - HX-01 / T-5.3 / focused-end-to-end-proof

## Task ID

HX-01-T-5.3-focused-end-to-end-proof

## Objective

Run the smallest proof bundle that still closes the normalized control-plane feature end to end against the real repository, including the validator-fixture regressions surfaced by the current proof run.

## Proof Bundle

- `uv run pytest tests/e2e/test_install_clean.py tests/unit/config/test_manifest.py tests/unit/test_state.py tests/unit/test_updater.py tests/unit/test_doctor_phases_state.py tests/unit/test_validator.py tests/unit/test_framework_context_loads.py tests/unit/test_lib_observability.py tests/unit/test_template_parity.py -q`
- `uv run ai-eng validate -c file-existence`
- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c manifest-coherence`

## Done Condition

- The focused HX-01 proof bundle passes against the normalized control-plane contract.
- The validator fixture surface matches the same governed root-entry and control-plane path contract as the runtime code.
- `HX-01` has no remaining executable build or verify queue beyond the explicitly deferred governance review work.