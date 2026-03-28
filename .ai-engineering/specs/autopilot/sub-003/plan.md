---
total: 3
completed: 3
---

# Plan: sub-003 Shared Context Promotion and Ownership Migration

## Plan

- [x] T-3.1 Promote reusable team guidance into framework-managed root contexts.
  Done when: CLI and MCP guidance live once under framework-managed `contexts/*.md`, are mirrored in the governance template, and are no longer duplicated under `contexts/team/`.

- [x] T-3.2 Lock install, update, and validation behavior around the new canonical homes.
  Done when: the promoted files are framework-managed, updatable, and integrity-checked, while `contexts/team/**` remains protected and team seeds stay limited to the existing local artifacts.

- [x] T-3.3 Align context loading and telemetry with the promoted assets.
  Done when: Step 0 and template instructions have one explicit policy for these shared contexts across Codex, Gemini, Claude Code, and Copilot, and the declared context-load tests match that policy.

## Exports

- `.ai-engineering/contexts/cli-ux.md`
- `.ai-engineering/contexts/mcp-integrations.md`

## Self-Report
- Promoted reusable CLI and MCP guidance into framework-managed root contexts and mirrored them into the governance template.
- Kept `contexts/team/` focused on local conventions and lessons while preserving the existing two-file team seed contract.
- Updated install/update tests to prove the promoted files are framework-managed and selectable through the shared context-loading contract.
