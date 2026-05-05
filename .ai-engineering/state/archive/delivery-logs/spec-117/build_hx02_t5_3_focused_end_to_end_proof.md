# Execution Packet - HX-02 / T-5.3 / focused-end-to-end-proof

## Task ID

HX-02-T-5.3-focused-end-to-end-proof

## Objective

Run the smallest proof bundle that still exercises the full `HX-02` contract: active work-plane resolution, task-ledger semantics, activate/reset lifecycle, CLI/runtime readers, validator coherence, and a real filesystem-backed integration path.

## Verification Bundle

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
- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c file-existence`

## Done Condition

- the full focused pytest bundle passes together
- structural validators stay green after the final work-plane artifact updates
- no additional `HX-02` slices remain queued in the plan

## Execution Evidence

### Result

- The focused proof bundle passed with `185 passed` across the selected unit and integration slices.
- `uv run ai-eng validate -c cross-reference` passed.
- `uv run ai-eng validate -c file-existence` passed.
- `HX-02` now has executable closure evidence for resolver, lifecycle, downstream readers, validator coherence, and integration behavior.