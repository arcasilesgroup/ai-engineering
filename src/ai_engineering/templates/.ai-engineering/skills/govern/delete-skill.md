# Delete Skill

## Purpose

Definitive procedure for safely removing a skill from the ai-engineering framework. Ensures every registration point is cleaned — canonical file, template mirror, all instruction files, counters, changelog, and cross-references — eliminating orphaned references and stale content.

## Trigger

- Command: agent invokes delete-skill skill or user requests removing a skill.
- Context: skill is deprecated, merged into another skill, or no longer needed.

## Procedure

### Phase 1: Validate

1. **Confirm the skill exists** — verify the canonical file is present.
   - Path: `.ai-engineering/skills/<category>/<name>.md`.
   - If not found, abort — nothing to delete.

2. **Check for dependents** — scan for references to this skill across all governance content.
   - Search all files in `.ai-engineering/` for the skill path.
   - Search all 6 instruction files for the skill entry.
   - Search all agents' `## Referenced Skills` for the skill.
   - Search all other skills' `## References` for the skill.
   - **If dependents exist**: list them. The user must decide whether to update or remove those references as part of this operation. Do not proceed without explicit confirmation.

3. **Record the deletion decision** — if the skill has dependents, persist the decision in `decision-store.json`.
   - Include: skill name, reason for deletion, list of affected dependents, replacement (if any).

### Phase 2: Remove from Instruction Files

4. **Remove from all 6 instruction files** — delete the reference line from the correct subsection.
   - Files to update (all 6, every time):

     | # | File | Location |
     |---|------|----------|
     | 1 | `.github/copilot-instructions.md` | `## Skills` → appropriate subsection |
     | 2 | `AGENTS.md` (repo root) | `## Skills` → appropriate subsection |
     | 3 | `CLAUDE.md` (repo root) | `## Skills` → appropriate subsection |
     | 4 | `src/ai_engineering/templates/project/copilot-instructions.md` | `## Skills` → appropriate subsection |
     | 5 | `src/ai_engineering/templates/project/AGENTS.md` | `## Skills` → appropriate subsection |
     | 6 | `src/ai_engineering/templates/project/CLAUDE.md` | `## Skills` → appropriate subsection |

   - Verify the line is removed from ALL 6 files.

### Phase 3: Remove Files

5. **Remove the template mirror** — delete `src/ai_engineering/templates/.ai-engineering/skills/<category>/<name>.md`.

6. **Remove the canonical file** — delete `.ai-engineering/skills/<category>/<name>.md`.

7. **Clean empty directories** — if the category directory is now empty, remove it (both canonical and mirror).

### Phase 3b: Remove Slash Command

7b. **Remove Claude Code command wrapper** — delete `.claude/commands/<namespace>/<name>.md` and its mirror at `src/ai_engineering/templates/project/.claude/commands/<namespace>/<name>.md`.
   - Clean empty directories in both locations if the namespace directory is now empty.

### Phase 4: Update Counters

8. **Update skill count in product-contract** — edit `.ai-engineering/context/product/product-contract.md`.
   - Decrement the `Active Objectives` skill count.
   - Decrement the `KPIs` table row for `Agent coverage`.
   - The count must match the actual number of skills listed in the instruction files.

### Phase 5: Changelog

9. **Add changelog entry** — edit `CHANGELOG.md`.
   - Add under `## [Unreleased] → ### Removed`.
   - Format: `- <Skill name> skill (<reason>).`

### Phase 6: Clean Cross-References

10. **Remove from agent Referenced Skills** — for each agent that referenced this skill, remove the line.
    - Update both canonical and mirror copies of affected agents.

11. **Remove from skill References** — for each skill that referenced this skill, remove the line.
    - Update both canonical and mirror copies of affected skills.

12. **Update replacement skill** — if a replacement skill exists, add a note in its References about what it replaces.

### Phase 7: Verify

13. **Run the verification checklist** — confirm all deregistration points are complete.

    | # | Check | How to verify |
    |---|-------|---------------|
    | 1 | Canonical file removed | `!(Test-Path .ai-engineering/skills/<category>/<name>.md)` |
    | 2 | Template mirror removed | `!(Test-Path src/ai_engineering/templates/.ai-engineering/skills/<category>/<name>.md)` |
    | 3 | Removed from all 6 files | `grep` for the skill path in each instruction file — 0 matches |
    | 4 | Count matches | Count skills in instruction files = count in product-contract |
    | 5 | CHANGELOG updated | Entry under `## [Unreleased] → ### Removed` |
    | 6 | No orphaned cross-refs | `grep` across `.ai-engineering/` for the skill path — 0 matches |
    | 7 | Agent refs cleaned | No agent references the deleted skill |
    | 8 | Mirrors consistent | All modified files have byte-identical mirrors |

## Output Contract

- Canonical skill file removed.
- Template mirror removed.
- Reference removed from all 6 instruction files.
- Updated skill count in `product-contract.md`.
- Changelog entry in `CHANGELOG.md`.
- All cross-references cleaned (agents and skills).
- Verification checklist passes all 8 checks.

## Governance Notes

- Deletion is a governed operation — dependents must be resolved before removal.
- Template mirror must be removed alongside canonical — never leave orphaned mirrors.
- Skill count in product-contract must match actual count listed in instruction files after deletion.
- If a skill is being replaced, reference the replacement in changelog and affected cross-references.
- Empty category directories should be cleaned up.
- No Python code changes are needed — installer and maintenance use glob-based discovery.

## References

- `skills/govern/create-skill.md` — inverse procedure (creation).
- `skills/govern/integrity-check.md` — post-deletion validation.
- `standards/framework/core.md` — governance structure, ownership model.
- `context/product/framework-contract.md` — template packaging and replication rule.
