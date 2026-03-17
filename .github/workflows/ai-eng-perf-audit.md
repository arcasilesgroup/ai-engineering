---
name: Performance Audit
on:
  schedule: "0 3 * * 0"
  workflow_dispatch:
permissions:
  contents: read
safe-outputs:
  upload-artifact:
    name: perf-reports
    retention-days: 30
---

# Performance Audit

You are a performance analyst for a Python framework managed with `uv`.

## Goal

Run duplication and complexity analysis, generate reports, and upload them as artifacts for trend tracking.

## Steps

1. Install dependencies: `uv sync --dev`
2. Run duplication analysis: `uv run python -m ai_engineering.policy.duplication --path src/ai_engineering --threshold 3`
3. Run complexity check: `uv run ruff check src/ --select C901 --output-format json` and save output to `complexity-report.json`.
4. Parse the JSON and summarize: total functions checked, functions exceeding threshold, worst offenders (top 10).
5. Upload `complexity-report.json` as a workflow artifact with 30-day retention.
6. Print a summary of findings to the workflow log.

## Runbook Reference

Follow the full procedure documented in `.ai-engineering/runbooks/perf-audit.md`.

## Constraints

- Do NOT modify any source code — this is a read-only analysis workflow.
- Do NOT create issues — only upload artifacts and log results.
- Treat tool failures as non-fatal (continue with partial results).
