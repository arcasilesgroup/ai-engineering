---
id: sub-002
parent: spec-087
title: "Sync Script Migration to .codex/"
status: planning
files:
  - scripts/sync_command_mirrors.py
depends_on:
  - sub-001
---

# Sub-Spec 002: Sync Script Migration to .codex/

## Scope

Update sync_command_mirrors.py to replace .agents/ as a generation target with .codex/. Rename constants (AGENTS_SKILLS->CODEX_SKILLS, lines 47-62), add "codex" target_ide to translate_refs() (lines 436-491, keeps ai- prefix), update generation pipeline Surfaces 1/2/2b (lines 1204-1300), update generate_agents_md() to output .codex/ paths and split Gemini/Codex rows (lines 752-792), update orphan detection surfaces (lines 1534-1550).

Decisions: D-087-01 (.agents->.codex), D-087-06 (.codex/agents/ for future-proofing).

## Exploration
[EMPTY -- populated by Phase 2]
