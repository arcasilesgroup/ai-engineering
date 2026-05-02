# HX-02 T-5.1 Active Spec Ledger Coherence - Review Handoff

## Scope

- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `tests/unit/test_validator.py`

## Review Agents

- `code-reviewer-correctness`
- `code-reviewer-testing`

## Findings

- `code-reviewer-correctness`: No findings.
- `code-reviewer-testing`: Flagged that the pointer-aware regression only partially proved resolved active work-plane selection because both the legacy and pointed `spec.md` files were placeholders.
- Follow-up applied: tightened `test_active_spec_placeholder_with_non_done_task_in_resolved_ledger_fails` so the legacy singleton `spec.md` is a real active spec while only the pointed work plane stays placeholder-backed, then reran the focused regression, full `TestManifestCoherence`, and `ai-eng validate -c manifest-coherence` successfully.

## Status

- `DONE`

## Residual Scope

- Runtime/orchestrator placeholder gates remain outside this completed validator slice and still need their own `T-5.1` cutover work.