# Build Packet - HX-02 / T-5.1 / pr-description-ledger-aware-active-spec-id

## Task ID

HX-02-T-5.1-pr-description-ledger-aware-active-spec-id

## Objective

Cut `vcs.pr_description._read_active_spec()` over from placeholder-only `None` to resolved-ledger-aware active-spec identity. When the resolved active work plane is placeholder-backed but its readable ledger still has any non-`DONE` task, PR title/body generation must stay spec-aware. The canonical lookup identifier must remain the raw work-plane directory name so linked-issue resolution stays aligned with `work_items.service`, while user-facing title/body text normalize away a leading `spec-` prefix.

## Write Scope

- `src/ai_engineering/vcs/pr_description.py`
- `tests/unit/test_pr_description.py`

## Failing Tests First

- add a pointed-work-plane helper regression where placeholder `spec.md` plus a live ledger returns the raw work-plane name
- add a done-ledger guardrail where the same placeholder-backed resolved work plane still returns `None`
- add public-builder regressions that prove title/body normalize display text without breaking raw lookup identity
- after testing review, tighten the live-ledger contract to a mixed ledger with `DONE` plus `VERIFY`

## Minimum Production Change

- keep the cutover local to `pr_description.py`
- make `_read_active_spec()` consult the resolved ledger before treating placeholder prose as idle
- keep the raw resolved work-plane directory name as the canonical lookup identifier
- normalize only user-facing title/body rendering by stripping a leading `spec-` prefix in display paths
- preserve done-ledger idle behavior and linked-issue lookup behavior

## Verification

- `uv run pytest tests/unit/test_pr_description.py -q`
- `uv run ruff check src/ai_engineering/vcs/pr_description.py tests/unit/test_pr_description.py`

## Done Condition

- placeholder-backed resolved work planes with live ledger tasks keep PR title/body spec-aware
- issue lookup still receives the raw work-plane name
- title/body rendering normalize display text so user-facing output does not duplicate `spec-`
- placeholder plus fully `DONE` ledger stays idle at helper and public-builder level
- full `test_pr_description.py` coverage and local Ruff checks pass

## Execution Evidence

### Change Summary

- Added helper, title, body, raw-lookup, done-ledger idle, and mixed-ledger regressions to `tests/unit/test_pr_description.py`.
- Taught `_read_active_spec()` to consult the resolved ledger for placeholder-backed work planes.
- Kept the raw work-plane name as the canonical lookup id and normalized only user-facing rendering through a small display helper.

### Passing Checks Executed

- `uv run pytest tests/unit/test_pr_description.py -q` -> `48 passed`
- `uv run ruff check src/ai_engineering/vcs/pr_description.py tests/unit/test_pr_description.py` -> `All checks passed!`
- `get_errors` on `src/ai_engineering/vcs/pr_description.py` -> no errors
- `get_errors` on `tests/unit/test_pr_description.py` -> no errors

### Result

- PR description readers now derive placeholder-backed active-spec context from the resolved live ledger instead of placeholder prose alone.
- Linked-issue lookup remains aligned with the raw work-plane identifier while visible text stays normalized.
- The cutover stayed local to `pr_description.py` and its unit coverage.