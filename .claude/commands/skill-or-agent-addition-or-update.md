---
name: skill-or-agent-addition-or-update
description: Workflow command scaffold for skill-or-agent-addition-or-update in ai-engineering.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /skill-or-agent-addition-or-update

Use this workflow when working on **skill-or-agent-addition-or-update** in `ai-engineering`.

## Goal

Adding or updating a skill or agent across all IDE mirrors (Claude, Copilot, Codex, Gemini) and templates, ensuring multi-surface consistency.

## Common Files

- `.claude/skills/*/SKILL.md`
- `.claude/agents/*.md`
- `.agents/skills/*/SKILL.md`
- `.agents/agents/*.md`
- `.github/skills/*/SKILL.md`
- `.github/agents/*.md`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit or create canonical skill/agent file in .claude/skills/ or .claude/agents/
- Run scripts/sync_command_mirrors.py or ai-eng sync to propagate changes to .agents/, .github/, and src/ai_engineering/templates/project/ mirrors
- Update manifest.yml and instruction files (CLAUDE.md, AGENTS.md, copilot-instructions.md) to reflect new/changed skills/agents
- Update or create handler files as needed (e.g., handlers/validate.md, handlers/review.md) in all mirrors
- Update or create relevant tests (test_agent_schema_validation.py, test_handler_routing_completeness.py, etc.)

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.