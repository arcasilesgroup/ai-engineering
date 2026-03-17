---
name: Weekly Health Report
on:
  schedule: "0 9 * * 1"
  workflow_dispatch:
permissions:
  contents: read
safe-outputs:
  create-issue:
    title-prefix: "[weekly-health] "
    labels: [automation, health-report]
    close-older-issues: true
---

# Weekly Health Report

You are a framework health monitor for an AI engineering platform managed with `uv`.

## Goal

Run comprehensive health checks and create a weekly status report issue.

## Steps

1. Install dependencies: `uv sync --dev`
2. Run framework health check: `uv run ai-eng doctor --json` and capture the output.
3. Run content integrity validation: `uv run ai-eng validate --json` and capture the output.
4. Parse both JSON outputs. Categorize results as PASS or FAIL per category.
5. Collect DORA-style metrics from git history:
   - Deployment frequency: count of merges to main in the last 7 days
   - Lead time: average time from branch creation to merge for completed PRs
6. Create a GitHub issue with:
   - Title: `chore(health): weekly health report <today's date>`
   - Body: health status table (category | status | details), DORA metrics, and any failures with recommendations
7. Close any older health report issues with the same prefix.

## Runbook Reference

Follow the full procedure documented in `.ai-engineering/runbooks/weekly-health.md`.

## Constraints

- Do NOT modify any files — this is a read-only reporting workflow.
- Do NOT fail the workflow if individual checks fail — report partial results.
- Always create the issue even if everything passes (for trend tracking).
