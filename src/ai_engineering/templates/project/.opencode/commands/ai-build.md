---
description: 'Canonical implementation gateway: reads approved plan.md, resolves stack from manifest, deterministic-routes each task to its adapter, dispatches the build agent in an isolated worktree, runs TDD self-validation per task, then a single final quality loop with one bounded quality-remediation pass on the full changeset before /ai-pr. Trigger for ''go'', ''start building'', ''execute the plan'', ''implement it'', ''lets do this'', ''build the plan'', ''resume'', ''continue''. Not without an approved plan; run /ai-plan first. Not for multi-concern specs needing decomposition; use /ai-autopilot instead. Not for a single function or subcomponent; use /ai-code.'
mirror_family: opencode-commands
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-build/SKILL.md
edit_policy: generated-do-not-edit
---

Use the `ai-build` skill to handle this request. OpenCode will lazy-load the canonical skill body via the `skill` tool; arguments below are forwarded verbatim.

$ARGUMENTS
