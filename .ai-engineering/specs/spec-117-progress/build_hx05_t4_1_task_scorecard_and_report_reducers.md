# Build Packet - HX-05 / T-4.1 / task-scorecard-and-report-reducers

## Task ID

HX-05-T-4.1-task-scorecard-and-report-reducers

## Objective

Add derived task scorecards and report reducers for task resolution, retry, rework, verification tax, drift, and related views without creating a peer authority.

## Minimum Change

- add a public `TaskScorecard` reducer in `maintenance.report` that reads only the authoritative active task ledger plus canonical framework events
- derive retry, rework, verification-tax, and guard-drift counts from task-trace and control-outcome events instead of introducing new event families or sidecar state files
- thread the scorecard through `MaintenanceReport` JSON and Markdown rendering so existing maintenance report outputs become the first derived view consumer
- pin the reducer contract with focused unit coverage over synthetic ledger and event histories

## Verification

- `uv run pytest tests/unit/test_skills_maintenance.py -q`
- `uv run pytest tests/integration/test_skills_integration.py -q`