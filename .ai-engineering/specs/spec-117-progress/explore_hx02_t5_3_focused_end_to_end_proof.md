# Explore - HX-02 / T-5.3 / focused-end-to-end-proof

## Slice Goal

Assemble one focused verification bundle that proves the `HX-02` work-plane contract end to end across resolver behavior, activate/reset maintenance flows, CLI/runtime readers, validator coherence, and one real integration path.

## Local Anchor

- `tests/unit/test_work_plane.py`
- `tests/unit/maintenance/test_spec_activate.py`
- `tests/unit/maintenance/test_spec_reset.py`
- `tests/unit/test_spec_cmd.py`
- `tests/unit/test_orchestrator_wave1.py`
- `tests/unit/test_work_items_service.py`
- `tests/unit/test_state.py::TestAuditEnrichment`
- `tests/unit/test_pr_description.py`
- `tests/unit/test_validator.py::TestManifestCoherence`
- `tests/integration/test_spec_reset_integration.py`

## Falsifiable Hypothesis

If one bundle covering resolver state, activate/reset lifecycle, CLI and downstream identifier readers, manifest coherence, and reset integration passes together, then `HX-02` has enough executable proof to close the feature without relying on one-off local checks.

## Cheapest Discriminating Check

- run the focused pytest bundle above as one command
- rerun `uv run ai-eng validate -c cross-reference`
- rerun `uv run ai-eng validate -c file-existence`