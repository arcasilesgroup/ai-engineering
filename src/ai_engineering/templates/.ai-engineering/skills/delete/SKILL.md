---
name: delete
description: "Delete agents or skills with full cleanup: remove files, update manifest, remove commands."
metadata:
  version: 1.0.0
  tags: [lifecycle, governance, agents, skills, deletion]
  ai-engineering:
    scope: read-write
    token_estimate: 500
---

# Delete

## Purpose

Delete agents or skills with full cleanup from the governance framework. Removes files, updates manifest, deletes slash commands, and cleans cross-references.

## Trigger

- Command: `/ai:delete agent <name>` or `/ai:delete skill <name>`
- Context: removing an agent or skill from the framework.

## Procedure

### Delete Agent

1. **Validate** -- confirm agent exists. Warn if agent owns skills.
2. **Reassign** -- if agent owns skills, reassign to another agent or prompt user.
3. **Remove** -- delete `agents/<name>.md`.
4. **Deregister** -- update `manifest.yml` agent count and names list.
5. **Command** -- remove `.claude/commands/ai/<name>.md`.
6. **Verify** -- run integrity check.

### Delete Skill

1. **Validate** -- confirm skill exists.
2. **Remove** -- delete `skills/<name>/` directory.
3. **Deregister** -- update `manifest.yml` skill count.
4. **Command** -- remove `.claude/commands/ai/<name>.md`.
5. **Unlink** -- remove skill reference from owning agent's frontmatter.
6. **Verify** -- run integrity check.
