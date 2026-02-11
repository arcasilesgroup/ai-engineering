---
spec: "005"
status: "CLOSED"
closed: "2026-02-11"
pr: "#32"
---

# Done — Slash Command Wrappers

## Summary

Created 37 thin command wrappers in `.claude/commands/` pointing to canonical skill/agent files. Template mirrors created in `src/ai_engineering/templates/project/.claude/commands/`. Decision S0-008 recorded.

## Deliverables

- `.claude/commands/` — 37 slash command wrappers (workflow, SWE, lifecycle, quality, agent).
- `src/ai_engineering/templates/project/.claude/commands/` — byte-identical mirrors.
- `manifest.yml` — `.claude/commands/**` registered in `external_framework_managed`.
- Decision S0-008 — thin wrapper pattern recorded.

## Merged

PR #32 merged to main at commit `c12f89f`.
