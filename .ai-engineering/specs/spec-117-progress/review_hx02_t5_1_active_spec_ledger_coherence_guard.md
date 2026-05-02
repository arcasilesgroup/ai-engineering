# HX-02 T-5.1 Active Spec Ledger Coherence - Guard Review

## Verdict

- `WARN`

## Constraints

- This is governance-safe only as the validator-local half of `T-5.1`, not as closure of the full cutover.
- Keep write scope exactly to `src/ai_engineering/validator/categories/manifest_coherence.py` and `tests/unit/test_validator.py`.
- Do not touch resolver, models, CLI, `plan.md` semantics, runtime/orchestrator gates, templates, or new validator categories.
- Do not hoist the full readable-ledger helper chain above the placeholder branch; add one narrow pre-idle coherence check instead.
- Use the existing active predicate: any task with `status != DONE` counts as active.
- Preserve true-idle placeholder behavior when the readable ledger has no non-done tasks.
- Preserve unreadable-ledger warning ownership and keep the new failure mode visible as its own check.

## Required Tests

- one failing test for placeholder `spec.md` plus a readable ledger with a non-done task
- one pointed-work-plane regression proving the failure uses the resolved active work plane
- one passing idle case for placeholder plus empty readable ledger
- one passing malformed-ledger guardrail preserving the current warning path

## Residual Scope

- Runtime consumers still using placeholder gates remain open and must be handled later in `T-5.1` or adjacent cutover slices.