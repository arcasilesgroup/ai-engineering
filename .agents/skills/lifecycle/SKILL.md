---
name: lifecycle
version: 1.0.0
description: 'Use this skill to create or delete agents and skills with full registration:
  scaffold, manifest update, command creation, cross-reference updates, and integrity
  verification. Merges the former create and delete skills into a unified lifecycle
  manager.'
argument-hint: create|transition|close
tags: [lifecycle, governance, agents, skills, creation, deletion]
---

# Lifecycle

## Purpose

Unified lifecycle management for agents and skills. Handles creation (scaffolding, registration, command creation) and deletion (cleanup, deregistration, cross-reference removal) in a single skill. Every lifecycle operation maintains governance integrity through manifest updates and integrity checks.

The reason these operations live together is that creation and deletion are inverse operations on the same entities — understanding one requires understanding the other. A lifecycle perspective prevents orphans (created without full registration) and ghosts (deleted without full cleanup).

## Trigger

- Command: `/ai:lifecycle create agent|skill <name>` or `/ai:lifecycle delete agent|skill <name>`
- Context: extending or reducing the framework's agent/skill catalog.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"lifecycle"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## When NOT to Use

- **Renaming** an agent or skill — rename is a delete + create with content migration. Use refactor skill instead.
- **Modifying** an existing skill body — just edit the SKILL.md directly.
- **Creating specs** — use the spec skill for spec lifecycle.

## Create Agent

1. **Validate** — check name doesn't conflict with existing agents. Verify kebab-case naming. Verify the name is a single English verb (convention).
2. **Scaffold** — create `agents/<name>.md` with required frontmatter: name, version, scope, capabilities, inputs, outputs, tags, references. Add Identity, Modes, Behavior, Boundaries, Escalation sections.
3. **Register** — update `manifest.yml`: increment agent count, add to names list.
4. **Command adapters** — create:
   - `.claude/skills/ai-<name>/SKILL.md` (Claude Code slash command)
   - `.github/prompts/ai-<name>.prompt.md` (Copilot prompt)
   - `.github/agents/<name>.agent.md` (Copilot agent)
5. **Mirror** — create corresponding files in `src/ai_engineering/templates/`.
6. **Cross-reference** — update AGENTS.md agent table. Update product-contract.md §2.2 if needed.
7. **Verify** — run `ai-eng validate` to confirm registration. Fix any integrity findings.

## Create Skill

1. **Validate** — check name doesn't conflict with existing skills. Verify kebab-case naming.
2. **Scaffold** — create `skills/<name>/SKILL.md` with frontmatter: name, description (trigger-optimized, ≤1024 chars), metadata. Follow Anthropic pattern: Purpose, Trigger, When NOT to Use, Procedure, Examples, Output Contract.
3. **Register** — update `manifest.yml` skill count.
4. **Link** — add skill reference to owning agent's `references.skills` frontmatter array.
5. **Command adapters** — create:
   - `.claude/skills/ai-<name>/SKILL.md`
   - `.github/prompts/ai-<name>.prompt.md`
6. **Mirror** — create corresponding files in `src/ai_engineering/templates/`.
7. **Cross-reference** — update AGENTS.md skill table if needed.
8. **Verify** — run `ai-eng validate`. Fix any integrity findings.

## Delete Agent

1. **Validate** — confirm agent exists. Warn if agent owns skills (they must be reassigned first).
2. **Reassign** — if agent owns skills, prompt user to reassign to another agent. Update each skill's agent reference.
3. **Remove** — delete `agents/<name>.md`.
4. **Deregister** — update `manifest.yml`: decrement agent count, remove from names list.
5. **Command adapters** — remove:
   - `.claude/skills/ai-<name>/SKILL.md`
   - `.github/prompts/ai-<name>.prompt.md`
   - `.github/agents/<name>.agent.md`
6. **Mirror** — remove from `src/ai_engineering/templates/`.
7. **Cross-reference** — update AGENTS.md, product-contract.md.
8. **Verify** — run `ai-eng validate`. Fix any findings.

## Delete Skill

1. **Validate** — confirm skill exists.
2. **Unlink** — remove skill reference from owning agent's `references.skills`.
3. **Remove** — delete `skills/<name>/` directory entirely.
4. **Deregister** — update `manifest.yml` skill count.
5. **Command adapters** — remove adapter files.
6. **Mirror** — remove from `src/ai_engineering/templates/`.
7. **Verify** — run `ai-eng validate`. Fix any findings.

## Governance Notes

- Every lifecycle operation is atomic: either all steps complete, or none (rollback on failure).
- The integrity check in the final step catches orphaned references, ghost entries, and mirror drift.
- Lifecycle operations on governance content (agents, skills) require an active spec for traceability.
- All changes are committed with format: `spec-NNN: lifecycle — create|delete agent|skill <name>`.

## References

- `standards/framework/core.md` — governance structure, ownership boundaries.
- `standards/framework/skills-schema.md` — skill/agent file format.
