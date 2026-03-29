---
id: sub-007
parent: spec-087
title: "Root Generation & Cleanup"
status: planning
files:
  - .codex/
  - .agents/
  - src/ai_engineering/templates/project/.agents/
  - AGENTS.md
  - GEMINI.md
depends_on:
  - sub-002
  - sub-004
  - sub-006
---

# Sub-Spec 007: Root Generation & Cleanup

## Scope

Run `sync_command_mirrors.py` to generate `.codex/` at root (41 skills + agents), regenerate `AGENTS.md` and `GEMINI.md` with correct paths. Delete root `.agents/` directory (124 files) and template `.agents/` directory. Run `sync_command_mirrors.py --check` to verify drift-free state. Run full test suite for final validation. Verify no `.agents/` directory exists anywhere in the project.

Risk R2 mitigation: stale `.agents/` from previous installs is removed here.

## Exploration
[EMPTY -- populated by Phase 2]
