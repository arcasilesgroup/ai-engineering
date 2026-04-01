---
name: sync-skill-and-agent-mirrors
description: Workflow command scaffold for sync-skill-and-agent-mirrors in ai-engineering.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /sync-skill-and-agent-mirrors

Use this workflow when working on **sync-skill-and-agent-mirrors** in `ai-engineering`.

## Goal

Propagate canonical skill/agent definitions to all IDE and template mirrors, ensuring parity across .claude/, .agents/, .github/, and templates/project/ directories.

## Common Files

- `.claude/skills/*/SKILL.md`
- `.claude/skills/*/handlers/*.md`
- `.claude/agents/*.md`
- `scripts/sync_command_mirrors.py`
- `.agents/skills/*/SKILL.md`
- `.agents/skills/*/handlers/*.md`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit or add skill/agent/handler files in .claude/ directory.
- Run sync_command_mirrors.py script to propagate changes.
- Update all mirrors: .agents/, .github/, templates/project/.claude/, templates/project/.agents/, templates/project/.github/
- Stage and commit all changed files across mirrors.
- Update instruction files (CLAUDE.md, AGENTS.md, copilot-instructions.md) if skill/agent count or structure changes.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.