---
name: create
description: "Create new agents or skills with full registration: scaffold, manifest update, command creation."
metadata:
  version: 1.0.0
  tags: [lifecycle, governance, agents, skills, creation]
  ai-engineering:
    scope: read-write
    token_estimate: 600
---

# Create

## Purpose

Create new agents or skills with full registration in the governance framework. Handles scaffolding, manifest updates, slash command creation, and cross-reference updates.

## Trigger

- Command: `/ai:create agent <name>` or `/ai:create skill <name>`
- Context: need to extend the framework with a new agent or skill.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"create"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## Procedure

### Create Agent

1. **Validate** -- check name doesn't conflict with existing agents.
2. **Scaffold** -- create `agents/<name>.md` with frontmatter template.
3. **Register** -- update `manifest.yml` agent count and names list.
4. **Command** -- create `.claude/commands/ai/<name>.md` slash command.
5. **Verify** -- run integrity check to confirm registration.

### Create Skill

1. **Validate** -- check name doesn't conflict with existing skills.
2. **Scaffold** -- create `skills/<name>/SKILL.md` with frontmatter template.
3. **Register** -- update `manifest.yml` skill count.
4. **Command** -- create `.claude/commands/ai/<name>.md` slash command.
5. **Link** -- add skill reference to owning agent's frontmatter.
6. **Verify** -- run integrity check to confirm registration.
