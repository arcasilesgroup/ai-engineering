---
id: "005"
slug: "slash-command-wrappers"
status: "done"
created: "2026-02-10"
---

# Spec 005 — Slash Command Wrappers

## Problem

Skills and agents exist as governance files but are not discoverable as Claude Code slash commands. Developers must know file paths to invoke them. No IDE-native surface exposes the full skill/agent catalogue.

## Solution

Create thin `.claude/commands/` wrappers (decision S0-008) that point to canonical skill and agent files. No content duplication — each wrapper is a 3-5 line prompt that reads and executes the source file. Update lifecycle skills (create-skill, create-agent, delete-skill, delete-agent) to include slash command registration/removal steps. Register `.claude/commands/**` as framework-managed in the manifest. Update all instruction files (CLAUDE.md, AGENTS.md, copilot-instructions.md) and their template mirrors.

## Scope

### In Scope

- `.claude/commands/` wrappers for all skills (workflows, swe, lifecycle, quality) and agents.
- Template mirrors at `src/ai_engineering/templates/project/.claude/commands/`.
- Manifest ownership update (`.claude/commands/**` as `external_framework_managed`).
- Lifecycle skill updates: create-skill, create-agent, delete-skill, delete-agent (Phase 4b/3b steps).
- Content-integrity skill update: additional mirror pair for `.claude/commands/**`.
- Instruction file updates: CLAUDE.md, AGENTS.md, copilot-instructions.md (and template mirrors).
- Decision S0-008 recorded in decision-store.json.

### Out of Scope

- Wrapper content changes beyond thin pointer prompts.
- New skills or agents.
- Runtime behavior changes.

## Acceptance Criteria

1. All skills have corresponding `.claude/commands/<namespace>/<name>.md` wrappers.
2. All agents have corresponding `.claude/commands/agent/<name>.md` wrappers.
3. Every wrapper has a byte-identical mirror in `src/ai_engineering/templates/project/.claude/commands/`.
4. Manifest lists `.claude/commands/**` under `external_framework_managed`.
5. Lifecycle skills include Phase 4b/3b for slash command registration/removal.
6. Content-integrity skill covers the `.claude/commands/**` mirror pair.
7. CLAUDE.md, AGENTS.md, copilot-instructions.md document the slash command surface.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| S0-008 | Thin command wrappers in .claude/commands/ | No content duplication — skills remain source of truth |
