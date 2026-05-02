# Build Packet - HX-02 / T-5.1 / state-audit-ledger-aware-active-spec-id

## Task ID

HX-02-T-5.1-state-audit-ledger-aware-active-spec-id

## Objective

Cut `state.audit._read_active_spec()` over from placeholder-only `None` to resolved-ledger-aware active-spec identity. When the resolved active work plane is placeholder-backed but its readable `task-ledger.json` still has any non-`DONE` task, audit enrichment must emit the raw work-plane directory name as the active spec identifier. The helper must also reflect current ledger transitions instead of serving a stale cached answer.

## Write Scope

- `src/ai_engineering/state/audit.py`
- `tests/unit/test_state.py`

## Failing Tests First

- add a pointed-work-plane regression where placeholder `spec.md` plus a live resolved ledger returns the raw work-plane name
- add a done-ledger guardrail where the same placeholder-backed resolved work plane still returns `None`
- after correctness review, replace the stale cache contract with current-state regressions for spec file updates and live-to-done ledger transitions in the same process

## Minimum Production Change

- keep the cutover local to `_read_active_spec()` in `state.audit.py`
- treat placeholder `spec.md` as active only when `read_task_ledger(root)` is readable and contains any task with `status != DONE`
- use the raw resolved work-plane directory name as the canonical fallback identifier so audit metadata stays aligned with work-item lookup
- remove spec-id caching because active-spec truth now depends on current ledger state
- keep frontmatter and heading fast paths unchanged

## Verification

- `uv run pytest tests/unit/test_state.py::TestAuditEnrichment -q`
- `uv run ruff check src/ai_engineering/state/audit.py tests/unit/test_state.py`

## Done Condition

- placeholder-backed resolved work planes with live ledger tasks emit a non-`None` audit spec identifier
- placeholder-backed resolved work planes with fully `DONE` ledgers stay idle
- same-process spec-file and ledger transitions are reflected immediately
- focused audit enrichment coverage and local Ruff checks pass

## Execution Evidence

### Change Summary

- Added pointed-work-plane audit regressions for placeholder-plus-live-ledger and placeholder-plus-done-ledger behavior.
- Taught `_read_active_spec()` to consult the resolved ledger before treating placeholder prose as authoritative idle state.
- Kept the raw work-plane directory name as the canonical fallback identifier and removed spec-id caching after review exposed stale live-to-done transitions.

### Passing Checks Executed

- `uv run pytest tests/unit/test_state.py::TestAuditEnrichment -q` -> `12 passed`
- `uv run ruff check src/ai_engineering/state/audit.py tests/unit/test_state.py` -> `All checks passed!`
- `get_errors` on `src/ai_engineering/state/audit.py` -> no errors
- `get_errors` on `tests/unit/test_state.py` -> no errors

### Result

- Audit enrichment now keeps active spec context for placeholder-backed resolved work planes when the ledger still carries live work.
- The helper no longer serves stale spec ids after the ledger transitions to fully done.
- The cutover stayed local to `state.audit` and its audit-enrichment unit coverage.