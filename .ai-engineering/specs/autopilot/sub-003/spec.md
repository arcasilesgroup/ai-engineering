---
id: sub-003
parent: spec-087
title: "Installer Provider Remapping"
status: planning
files:
  - src/ai_engineering/installer/templates.py, src/ai_engineering/installer/autodetect.py
depends_on:
  - sub-001
---

# Sub-Spec 003: Installer Provider Remapping

## Scope

Update installer so Codex maps to .codex/ and Gemini no longer copies .agents/. templates.py: remove .agents from gemini tree maps (lines 65-68), change codex from .agents to .codex (lines 69-71). autodetect.py: add .codex/ detection alongside .agents/ backward compat (lines 213-216). Decisions: D-087-01, D-087-03.

## Exploration
[EMPTY -- populated by Phase 2]
