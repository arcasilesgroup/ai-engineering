---
name: skill-lifecycle
description: "Create or delete a skill: author canonical file with frontmatter, mirror, register in instruction files, update counters, clean cross-references."
metadata:
  version: 1.0.0
  tags: [governance, skill, registration, removal, authoring]
  ai-engineering:
    scope: read-write
    token_estimate: 1900
---

# Skill Lifecycle

## Purpose

Unified procedure for creating and deleting skills. Ensures every registration point is updated or cleaned — canonical directory, template mirror, all instruction files, slash commands, counters, changelog, and cross-references.

## Trigger

- Command: `/govern:skill-lifecycle create|delete` or agent determines skill lifecycle action is needed.
- Context: new procedural skill needed, or existing skill deprecated/merged.

## When NOT to Use

- **Extending an existing skill** — edit the SKILL.md directly, do not create a new one.
- **Agent creation/deletion** — use `agent-lifecycle` instead.

## Mode: Create

### Procedure

1. **Design** — define name (kebab-case), category (`workflows|dev|review|quality|govern|docs`), purpose, trigger contexts.
2. **Check duplicates** — search `skills/` for overlapping purposes. Extend existing if overlap found.
3. **Author canonical file** — create directory `skills/<category>/<name>/` and write `SKILL.md`:
   - YAML frontmatter: `name`, `description`, `version`, `category`, `tags` (required). Optional: `metadata.ai-engineering` block for gating.
   - Body sections: Purpose, Trigger, When NOT to Use (if high confusion risk), Procedure (numbered steps in phases), Output Contract, Governance Notes (with Iteration Limits + Post-Action Validation for read-write), References.
   - `name` must match directory name. `category` must match parent directory.
4. **Create template mirror** — copy directory to `src/ai_engineering/templates/.ai-engineering/skills/<category>/<name>/` (byte-identical).
5. **Register in instruction files** — add skill to `## Skills` table row for appropriate category in all 7 instruction files. Update count in header.
6. **Create slash command** — write `.claude/commands/<category>/<name>.md` and template mirror. Thin 3-5 line pointer.
7. **Update counters** — increment skill count in `product-contract.md` and `manifest.yml`.
8. **Changelog** — add under `## [Unreleased] → ### Added`.
9. **Cross-reference** — add to related skills' References and agents' Referenced Skills.
10. **Verify** — run integrity-check. Confirm: file exists, frontmatter valid, template matches, listed in all files, count matches.

### Output

- Canonical directory + mirror. Listed in all instruction files. Slash command. Counters updated. Changelog. Cross-references. Integrity-check 7/7.

## Mode: Delete

### Procedure

1. **Confirm existence** — verify `skills/<category>/<name>/SKILL.md` exists.
2. **Check dependents** — search all governance content for references. List affected agents, skills, and instruction files. Get user confirmation.
3. **Record decision** — if dependents exist, persist in `decision-store.json` with reason and replacement.
4. **Remove from instruction files** — remove skill from `## Skills` table row in all 7 instruction files. Update count.
5. **Remove slash command** — delete `.claude/commands/<category>/<name>.md` and template mirror. Clean empty dirs.
6. **Remove files** — delete template mirror directory first, then canonical directory.
7. **Update counters** — decrement skill count in `product-contract.md` and `manifest.yml`.
8. **Changelog** — add under `## [Unreleased] → ### Removed`.
9. **Clean cross-references** — remove from agents' Referenced Skills and other skills' References. Update replacement if applicable.
10. **Verify** — run integrity-check. Confirm: file gone, mirror gone, removed from all files, count matches, no orphaned refs.

### Output

- Directory removed. Cleaned from all instruction files. Counters updated. Changelog. No orphaned references. Integrity-check 7/7.

## Governance Notes

- No Python code changes needed — installer uses glob-based discovery.
- Template mirrors must be byte-identical (create) or both removed (delete).
- Skill count in product-contract and manifest.yml must match actual count.
- Skills are framework-managed content — follow governed update flow.
- Never create a skill duplicating an existing purpose — extend instead.
- Deletion is governed — dependents must be resolved before removal.
- `name` in frontmatter MUST match directory name. Category MUST match parent.
- After any lifecycle operation, run integrity-check to verify 7/7.

## References

- `standards/framework/core.md` — governance structure, ownership model.
- `standards/framework/skills-schema.md` — skill directory schema, frontmatter spec.
- `context/product/framework-contract.md` — template packaging and replication rule.
- `skills/agent-lifecycle/SKILL.md` — companion procedure for agents.
- `skills/integrity/SKILL.md` — post-change validation.
- `skills/changelog/SKILL.md` — changelog entry formatting.
