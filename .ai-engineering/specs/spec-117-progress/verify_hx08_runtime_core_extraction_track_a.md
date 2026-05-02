# Verify: HX-08 Runtime Core Extraction Track A

## Focused Proof

```bash
.venv/bin/python -m pytest tests/unit/test_runtime_repositories.py tests/unit/test_manifest_load_required_tools.py tests/unit/test_install_state_required_tools.py -q
```

Result: `52 passed`.

```bash
.venv/bin/python -m ruff check src/ai_engineering/state/repository.py src/ai_engineering/state/manifest.py src/ai_engineering/state/service.py tests/unit/test_runtime_repositories.py --select I,F,E9
```

Result: `All checks passed!`.

Editor diagnostics reported no errors for the HX-08 touched source and test files.

```bash
.venv/bin/python -m json.tool .ai-engineering/specs/task-ledger.json >/dev/null
```

Result: passed with no output.

```bash
.venv/bin/python -m ai_engineering.cli validate -c cross-reference -c file-existence
```

Result: `Validate [PASS]`, `Categories 7/7 passed`.

## Wider Test Notes

A broader nearby run also executed `tests/unit/test_state.py`, `tests/unit/state/test_install_state.py`, and `tests/unit/test_state_plane_contract.py`; all selected tests passed except the pre-existing `TestAuditEnrichment.test_read_active_spec_caches_result` cache expectation in `tests/unit/test_state.py`, which is outside the HX-08 touched path.

Another broader manifest test run surfaced existing real/template manifest authority drift in `tests/unit/config/test_manifest.py`; those failures are outside this HX-08 repository-boundary change and were already implied by the active control-plane drift context.

## Coverage

- Manifest repository typed, raw, partial, and patch modes are covered.
- Comment-preserving manifest patch behavior is covered.
- Durable-state repository paths and stable state-family loaders are covered.
- `StateService` compatibility over the repository boundary is covered.
- Install-state legacy migration behavior is covered through the repository boundary.
- Manifest projection consumers were regression-tested through required-tools, SDK prereq, and install-state required-tools slices.

## Final Deferred Review

Completed in the final end-of-implementation review pass requested by the user. Governance review reconciled typed versus partial read semantics, compatibility boundaries, and ownership boundaries with `HX-04`, `HX-05`, and `HX-09`; no implementation tasks reopened.
