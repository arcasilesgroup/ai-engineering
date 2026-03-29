---
id: sub-004
parent: spec-088
title: "Instincts Pipeline Fix"
status: planning
files:
  - .ai-engineering/scripts/hooks/instinct-observe.py
  - .ai-engineering/scripts/hooks/instinct-extract.py
  - .ai-engineering/scripts/hooks/_lib/instincts.py
depends_on:
  - sub-002
---

# Sub-Spec 004: Instincts Pipeline Fix

## Scope

Fix the instinct observation pipeline end-to-end. Root cause: `instinct-observe.py` checks for event names PreToolUse/PostToolUse (Claude only) and silently drops all other events. After sub-002 normalizes event names via `get_hook_context()`, observations will flow. Verify that `append_instinct_observation()` correctly extracts tool_name from stdin data. Verify `instinct-extract.py` reads observations and writes to instincts.yml. Test end-to-end with a manual observation injection.

## Exploration
[EMPTY -- populated by Phase 2]
