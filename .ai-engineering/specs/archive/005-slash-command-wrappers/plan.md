---
spec: "005"
approach: "thin-wrapper-pointer-pattern"
---

# Plan — Slash Command Wrappers

## Approach

Each `.claude/commands/<path>.md` file is a 3-5 line prompt that instructs Claude Code to read and execute the canonical skill or agent file. No logic or content is duplicated. The canonical files in `.ai-engineering/skills/` and `.ai-engineering/agents/` remain the single source of truth.

## Namespace Mapping

| Skill category | Command path |
|----------------|-------------|
| `workflows/` | `.claude/commands/<name>.md` (root) |
| `swe/` | `.claude/commands/swe/<name>.md` |
| `lifecycle/` | `.claude/commands/lifecycle/<name>.md` |
| `quality/` | `.claude/commands/quality/<name>.md` |
| `agents/` | `.claude/commands/agent/<name>.md` |

## Mirror Strategy

Every command wrapper has a byte-identical copy in `src/ai_engineering/templates/project/.claude/commands/` so that `ai-eng init` distributes the wrappers to new projects.

## Governance Updates

- Manifest: `.claude/commands/**` added to `external_framework_managed`.
- Lifecycle skills: Phase 4b (create) and Phase 3b (delete) steps added.
- Content-integrity: new mirror pair registered.
- Instruction files: Slash Commands section added to CLAUDE.md, AGENTS.md, copilot-instructions.md.
