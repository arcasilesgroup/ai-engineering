---
name: ai-triage
description: >-
  Reads one GitHub or Azure DevOps backlog, explains what to work on first, and writes a
  complete report without changing remote items. GitHub triage is available; Azure routes
  stop before remote reads until Azure support is implemented. Use for backlog triage, not
  debugging one failure, filing an issue, reviewing a diff, or deciding what to build.
license: Apache-2.0
---

# ai-triage — read the backlog, rank it, touch nothing

Use one provider-specific procedure for one backlog at a time. Do not combine repositories,
organizations, projects, teams, or boards in one report.

## Routing

- For a GitHub target, follow the complete [GitHub procedure](references/github.md). It
  preserves the existing issue and pull-request inventory, ranking, evidence, and report.
- If the target is Azure DevOps, stop before making any remote read. Azure support is not
  available yet; do not invoke Azure CLI, inspect account defaults, or guess a scope. This
  fail-closed boundary remains until the later Azure checkpoints are implemented.
- If the provider or target is unclear, ask before reading anything.

## Read-only boundary

Never create, edit, label, assign, comment on, close, merge, review, or delete remote items.
The report is the only output artifact. Keep all inventoried items visible, including any
that could not be assessed; never present a partial inventory as complete.

## Lifecycle

Lane: light
Writes: `.ai-engineering/triage.html` for GitHub
Read by: the human deciding what to work on next; ai-brainstorm when an item becomes work
Dies: replaced by the next triage of the same repository
Next: ai-brainstorm when the human picks an item to build; none when the report only closes items

Source: ai-engineering (own), Apache-2.0.
