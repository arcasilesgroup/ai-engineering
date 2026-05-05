# Review - HX-02 / T-5.1 / state-audit-ledger-aware-active-spec-id

## Scope

- `src/ai_engineering/state/audit.py`
- `tests/unit/test_state.py`

## Review Focus

- placeholder `spec.md` must not suppress audit spec context when the resolved ledger still has live work
- the fallback identifier must stay aligned with work-item lookup identity
- ledger-driven truth must not be cached past a live-to-done transition

## Findings

- Initial correctness review of the identifier-reader cutover found one cross-module mismatch: stripping the `spec-` prefix in audit metadata diverged from the raw work-plane identifier still used by work-item lookup.
- Follow-up applied: restored the raw work-plane directory name as the canonical fallback identifier and kept normalization out of audit.
- A later correctness review found that spec-id caching had become stale once placeholder fallback depended on current ledger state.
- Follow-up applied: removed spec-id caching and added a live-to-done ledger transition regression in `tests/unit/test_state.py`.
- Final correctness review: no findings.
- Final testing review for the audit slice: no findings.

## Residual Risk

- This slice only closes the audit reader in `T-5.1`; broader `HX-02` closure still depends on documenting deferred cleanup in `T-5.2` and running the focused end-to-end proof in `T-5.3`.