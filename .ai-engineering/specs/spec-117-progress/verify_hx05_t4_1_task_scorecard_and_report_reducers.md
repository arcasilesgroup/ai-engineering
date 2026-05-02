# Verify HX-05 T-4.1 Task Scorecard And Report Reducers

## Ordered Verification

1. `uv run pytest tests/unit/test_skills_maintenance.py -q`
   - `PASS` (`17 passed`)
2. `uv run pytest tests/integration/test_skills_integration.py -q`
   - `PASS` (`14 passed`)

## Key Signals

- `maintenance.report.build_task_scorecard(...)` now derives resolution, retry, rework, verification-tax, and drift counts from the active task ledger plus canonical framework events.
- The reducer counts repeated `in-progress` task-trace phases as retries, detects reopen-after-done traces as rework, and counts same-phase artifact-ref expansion as verification-tax churn.
- Guard drift remains a derived report input by counting canonical `control_outcome` events rather than introducing a second drift log.
- `generate_report()` exposes the scorecard only through maintenance report JSON and Markdown outputs, keeping the new metrics downstream of authoritative state.