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

# Weekly Health GitHub Adapter

Canonical contract: `.ai-engineering/runbooks/weekly-health.md`

## Goal

Act as the GitHub host adapter for the canonical weekly health runbook.

## Adapter Steps

1. Read `.ai-engineering/runbooks/weekly-health.md`.
2. Run the health checks and summarize them through a provider-native report issue.
3. Use safe outputs only for allowed issue creation, updates, and supersession.
4. Print a concise summary of the run.

## Constraints

- reporting only
- no source-code modification
- no local spec or plan writes
