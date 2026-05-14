---
description: 'Audits MCP servers and skills on demand using LLM coherence analysis to catch capability drift and rug-pulls. Trigger for ''audit this skill'', ''is this MCP safe'', ''check coherence'', ''detect rug-pull'', ''snapshot baseline'', ''mcp audit''. Three modes: scan (declared-vs-observed), audit-update (post-update diff), baseline set (anchor known-good). Not for runtime payload inspection; use prompt-injection-guard hook instead. Not for CVE scanning; use /ai-security instead.'
mirror_family: opencode-commands
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-mcp-audit/SKILL.md
edit_policy: generated-do-not-edit
---

Use the `ai-mcp-audit` skill to handle this request. OpenCode will lazy-load the canonical skill body via the `skill` tool; arguments below are forwarded verbatim.

$ARGUMENTS
