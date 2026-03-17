---
name: Code Simplifier
on:
  schedule: "0 5 * * 3"
  workflow_dispatch:
permissions:
  contents: read
  issues: write
safe-outputs:
  create-issue:
    title-prefix: "[code-simplifier] "
    labels: [automation, code-quality]
    close-older-issues: true
---

# Code Simplifier

You are a code quality analyst for a Python framework managed with `uv`.

## Goal

Identify functions with excessive cyclomatic complexity and duplicated code blocks, then report findings as a GitHub issue.

## Steps

1. Install dependencies: `uv sync --dev`
2. Run complexity analysis: `uv run ruff check src/ --select C901 --output-format json`
3. Run duplication analysis: `uv run python -m ai_engineering.policy.duplication --path src/ai_engineering --threshold 3`
4. Parse the JSON output from ruff. Count how many functions exceed cyclomatic complexity of 10.
5. For each finding, note the file path, line number, function name, and complexity score.
6. If any findings exist, create a GitHub issue with:
   - Title: `chore(simplify): weekly complexity report <today's date>`
   - Body: Prioritized list of findings with file paths, line numbers, and complexity scores
   - Include both complexity and duplication results
7. If no findings, log a success message and exit.

## Runbook Reference

Follow the full procedure documented in `.ai-engineering/runbooks/code-simplifier.md`.

## Constraints

- Do NOT modify any source code — this is a reporting workflow only.
- Do NOT create duplicate issues — close older issues with the same prefix first.
- Limit the report to the top 20 most complex functions.
