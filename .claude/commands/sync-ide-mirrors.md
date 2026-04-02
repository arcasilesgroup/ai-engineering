---
name: sync-ide-mirrors
description: Workflow command scaffold for sync-ide-mirrors in ai-engineering.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /sync-ide-mirrors

Use this workflow when working on **sync-ide-mirrors** in `ai-engineering`.

## Goal

Synchronize canonical skill/agent files to all IDE mirror directories (Claude, Copilot, Codex, Gemini, .github, templates), ensuring parity and updating all mirrors after changes to skills or agents.

## Common Files

- `scripts/sync_command_mirrors.py`
- `.claude/skills/**`
- `.claude/agents/**`
- `.agents/skills/**`
- `.agents/agents/**`
- `.github/skills/**`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit or add canonical skill/agent/handler files in .claude/ (or canonical source dir).
- Run or update scripts/sync_command_mirrors.py to propagate changes.
- Regenerate all mirror files in .agents/, .github/, .codex/, .gemini/, templates/project/...
- Update or create corresponding handler files in all mirrors.
- Run tests/integration/test_sync_mirrors.py or similar to verify mirror parity.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.