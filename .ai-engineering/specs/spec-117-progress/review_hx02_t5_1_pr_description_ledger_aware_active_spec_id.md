# Review - HX-02 / T-5.1 / pr-description-ledger-aware-active-spec-id

## Scope

- `src/ai_engineering/vcs/pr_description.py`
- `tests/unit/test_pr_description.py`

## Review Focus

- placeholder `spec.md` must not force PR generation idle when the resolved ledger still has live work
- canonical lookup identity must remain aligned with `work_items.service`
- display normalization must stay user-facing only
- done-ledger idle behavior and mixed-ledger live behavior must both stay covered

## Findings

- Initial correctness review found one real mismatch: normalizing the fallback id inside `_read_active_spec()` diverged from the raw work-plane identifier still used by work-item lookup.
- Follow-up applied: restored the raw work-plane directory name as the canonical lookup id and normalized only title/body display surfaces.
- Initial testing review found missing coverage for the raw-lookup contract, public-builder done-ledger idle behavior, and the broader mixed-ledger `any non-DONE task` contract.
- Follow-up applied: added regressions for raw issue lookup, builder-level done-ledger idle, and a mixed `DONE + VERIFY` live ledger.
- Final correctness review: no findings.
- Final testing review: no findings.

## Residual Risk

- This slice closes the remaining identifier-driven PR reader in `T-5.1`; the feature still needs the deferred-cleanup envelope (`T-5.2`) and focused end-to-end proof (`T-5.3`).