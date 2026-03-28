---
name: Performance Audit
on:
  schedule: "0 3 * * 0"
  workflow_dispatch:
permissions:
  contents: read
---

# Performance Audit GitHub Adapter

Canonical contract: `.ai-engineering/runbooks/perf-audit.md`

## Goal

Act as the GitHub host adapter for the canonical performance-audit runbook.

## Adapter Steps

1. Read `.ai-engineering/runbooks/perf-audit.md`.
2. Run the analysis steps and persist machine artifacts.
3. Report the result through provider-native comments or follow-up work when thresholds are exceeded.
4. Print a concise summary for the workflow log.

## Constraints

- read-only for source code
- artifacts are allowed
- no local spec or plan writes
