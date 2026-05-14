---
description: 'Operates the project board (GitHub Projects v2 or Azure DevOps): discovers configuration after install (fields, state mappings, process templates) and syncs work-item state at lifecycle transitions. Trigger for ''set up the board'', ''configure our ADO board'', ''discover board fields'', ''move this issue to in-review'', ''update the board'', ''mark as in progress'', ''sync the work item state''. Two subcommands: `discover` (post-install configuration write) and `sync` (lifecycle state transitions). Auto-invoked via `sync` by /ai-brainstorm, /ai-build, and /ai-pr; fail-open. Not for backlog execution; use /ai-autopilot --backlog instead.'
mirror_family: opencode-commands
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-board/SKILL.md
edit_policy: generated-do-not-edit
---

Use the `ai-board` skill to handle this request. OpenCode will lazy-load the canonical skill body via the `skill` tool; arguments below are forwarded verbatim.

$ARGUMENTS
