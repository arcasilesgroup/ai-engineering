---
name: Governance Drift Detection
on:
  schedule: "0 4 * * 1"
  workflow_dispatch:
permissions:
  contents: read
  issues: write
safe-outputs:
  create-issue:
    title-prefix: "[governance-drift] "
    labels: [automation, governance]
    close-older-issues: true
---

# Governance Drift Detection

You are a governance compliance checker for an AI engineering framework managed with `uv`.

## Goal

Detect drift between governance decisions and their implementation, verify mirror synchronization, and report findings.

## Steps

1. Install dependencies: `uv sync --dev`
2. Run content integrity validation: `uv run ai-eng validate`
3. Run governance diff: `uv run ai-eng governance diff`
4. Check risk acceptances: `uv run ai-eng gate risk-check`
5. Run mirror sync verification: `uv run ai-eng validate --json` and parse the JSON output.
6. Verify counter accuracy: check that counts in AGENTS.md, CLAUDE.md, and copilot-instructions.md match actual files on disk.
7. If any drift, expired decisions, or sync issues are found, create a GitHub issue with:
   - Title: `chore(governance): drift report <today's date>`
   - Body: categorized findings (integrity failures, mirror desync, expired decisions, counter mismatches)
   - Include specific fix instructions for each finding
8. If no drift found, log success and exit.

## Runbook Reference

Follow the full procedure documented in `.ai-engineering/runbooks/governance-drift-repair.md`.

## Constraints

- Do NOT apply fixes automatically — this is a detection and reporting workflow only.
- Do NOT modify governance files, standards, or decision store.
- Report ALL findings even if some checks fail — partial results are valuable.
