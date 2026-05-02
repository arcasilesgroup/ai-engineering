# Build Packet - HX-02 / T-5.1 / active-spec-ledger-coherence

## Task ID

HX-02-T-5.1-active-spec-ledger-coherence

## Objective

In manifest-coherence only, detect the contradiction where the placeholder active spec buffer is paired with a readable active task ledger containing any non-done task. Preserve the passing idle behavior for placeholder plus empty or no-live ledger, and preserve unreadable-ledger warning behavior.

## Write Scope

- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `tests/unit/test_validator.py`
- No edits outside those files.

## Failing Tests First

- Add `TestManifestCoherence::test_active_spec_placeholder_with_non_done_task_in_ledger_fails` and expect `manifest-coherence` to fail with one `active-spec-ledger-coherence = FAIL`.
- Add `TestManifestCoherence::test_active_spec_placeholder_with_malformed_task_ledger_warns` and expect the existing `active-task-ledger = WARN` path plus no downstream ledger sub-checks.
- Keep or tighten the current placeholder regression so placeholder plus empty ledger stays passing and does not emit `active-spec-ledger-coherence`.

## Minimum Production Change

- Keep the non-placeholder path and `_record_task_ledger_activity(...)` unchanged.
- Add one narrow placeholder-only helper, for example `_record_placeholder_spec_ledger_coherence(target, report)`, and call it only from the placeholder branch in `_check_manifest_coherence(...)`.
- Use `resolve_active_work_plane(target).ledger_path.exists()` together with `read_task_ledger(target)` so the placeholder branch can distinguish missing, unreadable, and readable ledgers without changing resolver code.
- If the ledger is missing, emit nothing and keep idle behavior.
- If the ledger file exists but is unreadable, emit the existing `active-task-ledger = WARN` result and stop.
- If the ledger is readable and any task status is not `DONE`, emit `active-spec-ledger-coherence = FAIL`.
- If the ledger is readable and has no non-done tasks, do not emit the failure path.
- Do not route placeholder specs through `_record_task_ledger_activity(...)`.
- Do not widen into resolver, model, template, work-item, or CLI changes.

## Verification

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence::test_active_spec_placeholder_with_non_done_task_in_ledger_fails -q`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -k "active_spec_placeholder or malformed_task_ledger" -q`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`
- `uv run ai-eng validate -c manifest-coherence`

## Rollback

- Remove the placeholder-only coherence helper and its call site.
- Delete the new placeholder contradiction and warning tests, and restore the prior placeholder assertions if they were split.
- Re-run the focused manifest-coherence pytest slice to confirm the reversion.

## Done Condition

- Placeholder active spec plus readable ledger with any non-done task fails `manifest-coherence` through `active-spec-ledger-coherence`.
- Placeholder plus empty or no-live ledger still passes as idle.
- Placeholder plus unreadable existing ledger still warns through `active-task-ledger` and skips downstream ledger sub-checks.
- Non-placeholder readable-ledger behavior is unchanged.
- Focused `TestManifestCoherence` and `ai-eng validate -c manifest-coherence` both pass.

## Execution Evidence

### Change Summary

- Added placeholder-only ledger coherence handling in `manifest_coherence.py` so placeholder `spec.md` no longer short-circuits a readable resolved ledger with live work.
- Kept placeholder plus empty ledger as idle and placeholder plus malformed ledger on the existing `active-task-ledger = WARN` path.
- Added focused `TestManifestCoherence` coverage for the contradiction case, the idle placeholder case, and the malformed-ledger compatibility case.

### Failing Test Executed First

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence::test_active_spec_placeholder_with_non_done_task_in_resolved_ledger_fails -q`
- Result before implementation: `FAIL` because no `active-spec-ledger-coherence = FAIL` result was emitted yet.

### Passing Checks Executed

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence::test_active_spec_placeholder_with_non_done_task_in_resolved_ledger_fails -q`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -k "active_spec_placeholder or malformed_task_ledger" -q` -> `4 passed`
- `uv run ruff check src/ai_engineering/validator/categories/manifest_coherence.py tests/unit/test_validator.py`
- `uv run ruff format --check src/ai_engineering/validator/categories/manifest_coherence.py tests/unit/test_validator.py`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q` -> `27 passed`
- `uv run ai-eng validate -c manifest-coherence` -> `PASS`

### Follow-up Evidence

- Testing review found that the pointer-aware regression only partially proved resolved work-plane selection.
- Tightened `test_active_spec_placeholder_with_non_done_task_in_resolved_ledger_fails` so the legacy singleton `spec.md` is a real active spec while only the pointed work plane remains placeholder-backed.
- Re-ran the focused regression (`1 passed`), full `TestManifestCoherence` (`27 passed`), and `uv run ai-eng validate -c manifest-coherence` (`PASS`).

### Result

- `active-spec-ledger-coherence = FAIL` now emits when a placeholder active spec conflicts with a readable resolved ledger containing non-done tasks.
- True idle placeholder behavior and unreadable-ledger warning behavior remained unchanged.
- The slice stayed local to `manifest_coherence.py` and `TestManifestCoherence`, with runtime/orchestrator cutover still deferred.

### Residual Concerns

- This slice closes only the validator-local half of `T-5.1`.
- Runtime, orchestrator, and CLI consumers that still treat placeholder buffers as authoritative remain open for the next cutover slice.