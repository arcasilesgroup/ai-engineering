---
id: sub-002
parent: spec-088
title: "Cross-IDE Hook Compatibility"
status: planning
files:
  - .ai-engineering/scripts/hooks/_lib/hook_context.py
  - .ai-engineering/scripts/hooks/telemetry-skill.py
  - .ai-engineering/scripts/hooks/prompt-injection-guard.py
  - .ai-engineering/scripts/hooks/strategic-compact.py
  - .ai-engineering/scripts/hooks/mcp-health.py
  - .ai-engineering/scripts/hooks/instinct-observe.py
  - .ai-engineering/scripts/hooks/instinct-extract.py
  - .ai-engineering/scripts/hooks/observe.py
  - src/ai_engineering/templates/project/.gemini/settings.json
  - src/ai_engineering/templates/project/.codex/hooks.json
depends_on: []
---

# Sub-Spec 002: Cross-IDE Hook Compatibility

## Scope

Create a shared `_lib/hook_context.py` module providing `get_hook_context()` that returns engine, project_root, session_id, and normalized event_name. Update all 7 non-working hooks to use it instead of hardcoded Claude Code env vars. Add `AIENG_HOOK_ENGINE=gemini` / `AIENG_HOOK_ENGINE=codex` to hook command strings in .gemini/settings.json and .codex/hooks.json. Normalize Gemini event names (BeforeTool->PreToolUse, AfterTool->PostToolUse, BeforeAgent->UserPromptSubmit, AfterAgent->Stop). Decisions D-088-02, D-088-04, D-088-06.

## Exploration
[EMPTY -- populated by Phase 2]
