---
name: Daily Triage
on:
  schedule: "0 9 * * 1-5"
  workflow_dispatch:
permissions:
  contents: read
safe-outputs:
  add-labels:
    allowed: [stale, needs-triage, priority-high, priority-medium, priority-low]
  close-issue:
    required-labels: [stale]
---

# Daily Triage GitHub Adapter

Canonical contract: `.ai-engineering/runbooks/daily-triage.md`

## Goal

Act as the GitHub host adapter for the canonical daily triage runbook.

## Adapter Steps

1. Read `.ai-engineering/runbooks/daily-triage.md`.
2. Execute the provider-native triage actions against GitHub Issues.
3. Use safe outputs only for labels, comments, and eligible closures.
4. Print a concise summary of what changed.

## Constraints

- do not implement local code
- do not write local spec or plan files
- do not mutate feature-level planning records
