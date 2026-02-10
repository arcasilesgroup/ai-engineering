# Delete Agent

## Purpose

Definitive procedure for safely removing an agent from the ai-engineering framework. Ensures every registration point is cleaned — canonical file, template mirror, all instruction files, counters, changelog, and cross-references — eliminating orphaned references and stale content.

## Trigger

- Command: agent invokes delete-agent skill or user requests removing an agent.
- Context: agent is deprecated, merged into another agent, or no longer needed.

## Procedure

### Phase 1: Validate

1. **Confirm the agent exists** — verify the canonical file is present.
   - Path: `.ai-engineering/agents/<name>.md`.
   - If not found, abort — nothing to delete.

2. **Check for dependents** — scan for references to this agent across all governance content.
   - Search all files in `.ai-engineering/` for the agent path.
   - Search all 6 instruction files for the agent entry.
   - Search all skills' `## References` for the agent.
   - Search other agents for references to this agent.
   - **If dependents exist**: list them. The user must decide whether to update or remove those references as part of this operation. Do not proceed without explicit confirmation.

3. **Record the deletion decision** — if the agent has dependents, persist the decision in `decision-store.json`.
   - Include: agent name, reason for deletion, list of affected dependents, replacement (if any).

### Phase 2: Remove from Instruction Files

4. **Remove from all 6 instruction files** — delete the reference line from the `## Agents` section.
   - Files to update (all 6, every time):

     | # | File | Location |
     |---|------|----------|
     | 1 | `.github/copilot-instructions.md` | `## Agents` |
     | 2 | `AGENTS.md` (repo root) | `## Agents` |
     | 3 | `CLAUDE.md` (repo root) | `## Agents` |
     | 4 | `src/ai_engineering/templates/project/copilot-instructions.md` | `## Agents` |
     | 5 | `src/ai_engineering/templates/project/AGENTS.md` | `## Agents` |
     | 6 | `src/ai_engineering/templates/project/CLAUDE.md` | `## Agents` |

   - Verify the line is removed from ALL 6 files.

### Phase 3: Remove Files

5. **Remove the template mirror** — delete `src/ai_engineering/templates/.ai-engineering/agents/<name>.md`.

6. **Remove the canonical file** — delete `.ai-engineering/agents/<name>.md`.

### Phase 3b: Remove Slash Command

6b. **Remove Claude Code command wrapper** — delete `.claude/commands/agent/<name>.md` and its mirror at `src/ai_engineering/templates/project/.claude/commands/agent/<name>.md`.

### Phase 4: Update Counters

7. **Update agent count in product-contract** — edit `.ai-engineering/context/product/product-contract.md`.
   - Decrement the `Active Objectives` agent count.
   - Decrement the `KPIs` table row for `Agent coverage`.
   - The count must match the actual number of agents listed in the instruction files.

### Phase 5: Changelog

8. **Add changelog entry** — edit `CHANGELOG.md`.
   - Add under `## [Unreleased] → ### Removed`.
   - Format: `- <Agent name> agent (<reason>).`

### Phase 6: Clean Cross-References

9. **Remove from skill References** — for each skill that referenced this agent, remove the line.
    - Update both canonical and mirror copies of affected skills.

10. **Remove from other agent references** — for each agent that referenced this agent, remove the line.
    - Update both canonical and mirror copies of affected agents.

11. **Update replacement agent** — if a replacement agent exists, add a note in its References about what it replaces.

### Phase 7: Verify

12. **Run the verification checklist** — confirm all deregistration points are complete.

    | # | Check | How to verify |
    |---|-------|---------------|
    | 1 | Canonical file removed | `!(Test-Path .ai-engineering/agents/<name>.md)` |
    | 2 | Template mirror removed | `!(Test-Path src/ai_engineering/templates/.ai-engineering/agents/<name>.md)` |
    | 3 | Removed from all 6 files | `grep` for the agent path in each instruction file — 0 matches |
    | 4 | Count matches | Count agents in instruction files = count in product-contract |
    | 5 | CHANGELOG updated | Entry under `## [Unreleased] → ### Removed` |
    | 6 | No orphaned cross-refs | `grep` across `.ai-engineering/` for the agent path — 0 matches |
    | 7 | Skill refs cleaned | No skill references the deleted agent |
    | 8 | Mirrors consistent | All modified files have byte-identical mirrors |

## Output Contract

- Canonical agent file removed.
- Template mirror removed.
- Reference removed from all 6 instruction files.
- Updated agent count in `product-contract.md`.
- Changelog entry in `CHANGELOG.md`.
- All cross-references cleaned (skills and agents).
- Verification checklist passes all 8 checks.

## Governance Notes

- Deletion is a governed operation — dependents must be resolved before removal.
- Template mirror must be removed alongside canonical — never leave orphaned mirrors.
- Agent count in product-contract must match actual count listed in instruction files after deletion.
- If an agent is being replaced, reference the replacement in changelog and affected cross-references.
- No Python code changes are needed — installer and maintenance use glob-based discovery.

## References

- `skills/lifecycle/create-agent.md` — inverse procedure (creation).
- `skills/lifecycle/content-integrity.md` — post-deletion validation.
- `standards/framework/core.md` — governance structure, ownership model.
- `context/product/framework-contract.md` — template packaging and replication rule.
