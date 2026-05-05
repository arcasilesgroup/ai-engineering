# Review - HX-02 / T-5.1 / work-items-ledger-aware-active-spec-dir

## Scope

- `src/ai_engineering/work_items/service.py`
- `tests/unit/test_work_items_service.py`

## Review Focus

- placeholder `spec.md` must not suppress sync for a resolved spec-local work plane that still has live ledger tasks
- fully-done and unreadable ledgers must remain idle for compatibility
- keep the cutover local to the work-items service and matching unit coverage

## Findings

- No correctness findings after the final local review.
- The production change mirrors the existing Wave 1 placeholder-to-ledger rule instead of inventing a new policy.
- The tests cover the live-ledger activation case plus done-ledger and unreadable-ledger guardrails.

## Residual Risk

- Other runtime or CLI readers still rely on placeholder spec text alone; those remain open `T-5.1` follow-up slices.
