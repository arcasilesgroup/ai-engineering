---
id: sub-001
parent: spec-087
title: "Codex & Gemini Template Surface"
status: planning
files:
  - src/ai_engineering/templates/project/.codex/hooks.json
  - src/ai_engineering/templates/project/.codex/config.toml
  - src/ai_engineering/templates/project/.gemini/settings.json
depends_on: []
---

# Sub-Spec 001: Codex & Gemini Template Surface

## Scope

Create the new .codex/ template directory with hooks.json (5 Codex events in nested matcher/hooks format, CWD-relative paths, timeouts in seconds) and config.toml (enables codex_hooks feature flag). Rewrite .gemini/settings.json from the current incorrect flat format to the official Gemini CLI nested format with hooksConfig.enabled: true and timeouts in milliseconds. Reference: .claude/settings.json for the correct nested hook structure, adapted per IDE native schema.

Decisions: D-087-02 (Gemini nested format), D-087-04 (Codex hooks.json), D-087-08 (config.toml), D-087-09 (ms vs s), D-087-10 (CWD-relative).

## Exploration
[EMPTY -- populated by Phase 2]
