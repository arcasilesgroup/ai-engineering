---
name: agent-lifecycle
description: "Create or delete an agent: author canonical file, mirror, register in instruction files, update counters, clean cross-references."
version: 1.0.0
tags: [governance, agent, registration, removal, persona]
metadata:
  ai-engineering:
    scope: read-write
    token_estimate: 1800
---

# Agent Lifecycle

## Purpose

Unified procedure for creating and deleting agents. Ensures every registration point is updated or cleaned — canonical file, template mirror, all instruction files, slash commands, counters, changelog, and cross-references.

## Trigger

- Command: `/govern:agent-lifecycle create|delete` or agent determines agent lifecycle action is needed.
- Context: new agent persona needed, or existing agent deprecated/merged.

## When NOT to Use

- **Extending an existing agent** — edit the agent file directly, do not create a new one.
- **Skill creation/deletion** — use `skill-lifecycle` instead.

## Mode: Create

### Procedure

1. **Design** — define name (kebab-case), identity (third-person), capabilities (noun phrases), activation triggers.
2. **Check duplicates** — search `agents/` for overlapping capabilities. Extend existing if overlap found.
3. **Identify references** — map behavior steps to existing skills and standards.
4. **Author canonical file** — write `.ai-engineering/agents/<name>.md` following template:
   - Sections: Identity, Capabilities, Activation, Behavior (4-8 numbered steps), Referenced Skills, Referenced Standards, Output Contract, Boundaries (with Escalation Protocol).
   - Identity in third person. Boundaries include max 3 retries, different approach each time.
5. **Create template mirror** — copy to `src/ai_engineering/templates/.ai-engineering/agents/<name>.md` (byte-identical).
6. **Register in instruction files** — add agent row to `## Agents` table in all 7 instruction files (CLAUDE.md, AGENTS.md, copilot-instructions.md, GEMINI.md + 3 templates). Insert alphabetically.
7. **Create slash command** — write `.claude/commands/agent/<name>.md` and its template mirror. Thin 3-5 line pointer.
8. **Update counters** — increment agent count in `product-contract.md` (Active Objectives + KPIs).
9. **Changelog** — add under `## [Unreleased] → ### Added`.
10. **Cross-reference** — add agent to related skills' References. Ensure agent's Referenced Skills/Standards are complete.
11. **Verify** — run integrity-check. Confirm: file exists, template matches, listed in all files, count matches, changelog updated.

### Output

- Canonical + mirror files. Listed in all instruction files. Slash command created. Counters updated. Changelog entry. Cross-references complete. Integrity-check 7/7.

## Mode: Delete

### Procedure

1. **Confirm existence** — verify `.ai-engineering/agents/<name>.md` exists.
2. **Check dependents** — search all governance content for references. List affected files. Get user confirmation before proceeding.
3. **Record decision** — if dependents exist, persist in `decision-store.json` with reason and replacement.
4. **Remove from instruction files** — delete agent row from `## Agents` table in all 7 instruction files.
5. **Remove slash command** — delete `.claude/commands/agent/<name>.md` and template mirror.
6. **Remove files** — delete template mirror first, then canonical file.
7. **Update counters** — decrement agent count in `product-contract.md`.
8. **Changelog** — add under `## [Unreleased] → ### Removed`.
9. **Clean cross-references** — remove from all skills' References and other agents' references. Update replacement agent if applicable.
10. **Verify** — run integrity-check. Confirm: file gone, mirror gone, removed from all files, count matches, no orphaned refs.

### Output

- Files removed. Cleaned from all instruction files. Counters updated. Changelog entry. No orphaned references. Integrity-check 7/7.

## Governance Notes

- No Python code changes needed — installer uses glob-based discovery.
- Template mirrors must be byte-identical (create) or both removed (delete).
- Counts in product-contract must match actual instruction file listings.
- Agents are framework-managed content — follow governed update flow.
- Never create an agent duplicating existing capabilities — extend instead.
- Deletion is governed — dependents must be resolved before removal.
- After any lifecycle operation, run integrity-check to verify 7/7.

## References

- `standards/framework/core.md` — governance structure, ownership model.
- `standards/framework/skills-schema.md` — agent frontmatter schema.
- `context/product/framework-contract.md` — template packaging and replication rule.
- `skills/govern/skill-lifecycle/SKILL.md` — companion procedure for skills.
- `skills/govern/integrity-check/SKILL.md` — post-change validation.
- `skills/docs/changelog/SKILL.md` — changelog entry formatting.
