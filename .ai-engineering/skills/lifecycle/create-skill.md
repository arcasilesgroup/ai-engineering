# Create Skill

## Purpose

Definitive procedure for authoring and registering a new skill in the ai-engineering framework. Ensures every registration point is updated — canonical file, template mirror, all instruction files, counters, changelog, and cross-references — eliminating partial registration risk.

## Trigger

- Command: agent invokes create-skill skill or user requests adding a new skill.
- Context: new procedural skill is needed, existing gap identified, governance content expansion.

## Procedure

### Phase 1: Design

1. **Define skill identity** — determine name, category, purpose, and trigger contexts.
   - Name: kebab-case (`my-skill`).
   - Category: `swe/`, `workflows/`, `quality/`, `lifecycle/`, `utils/`, or `validation/`.
   - Purpose: one paragraph explaining what the skill does and when to use it.
   - Trigger: command pattern and context scenarios.

2. **Check for duplicates** — verify no existing skill covers the same ground.
   - Review skills listed in `.github/copilot-instructions.md` under `## Skills`.
   - Search `.ai-engineering/skills/` for overlapping names or purposes.
   - If overlap exists, consider extending the existing skill instead.

### Phase 2: Author

3. **Create the canonical skill file** — write `.ai-engineering/skills/<category>/<name>.md`.
   - Follow the skill template structure:

     ```
     # Skill Name
     ## Purpose
     ## Trigger
     ## Procedure
       ### Phase N: <Name>
       N. **Step name** — description.
     ## Output Contract
     ## Governance Notes
     ## References
     ```

   - Procedure steps are **numbered sequentially** across all phases.
   - Use bold step names with em-dash: `**Step name** — description.`
   - References use relative paths from `.ai-engineering/` (e.g., `standards/framework/core.md`).

4. **Validate structure** — confirm the skill file contains all required sections.
   - Purpose: present and concise.
   - Trigger: command and context defined.
   - Procedure: at least one phase with numbered steps.
   - Output Contract: measurable deliverables listed.
   - Governance Notes: relevant constraints from standards.
   - References: at least one link to a related standard, skill, or agent.

### Phase 3: Mirror

5. **Create the template mirror** — copy to `src/ai_engineering/templates/.ai-engineering/skills/<category>/<name>.md`.
   - Content must be **byte-identical** to the canonical file.
   - This is required by framework-contract: "Keep non-state files identical between canonical and template mirror."
   - The installer uses `rglob("*")` to discover templates — no Python code changes needed.
   - The `pyproject.toml` includes `src/ai_engineering/templates/**/*.md` — no build config changes needed.

### Phase 4: Register

6. **Add to all 6 instruction files** — insert a reference line under the correct subsection.
   - Format: `- \`.ai-engineering/skills/<category>/<name>.md\` — one-line description.`
   - Subsection mapping:
     - `workflows/` → `### Workflows`
     - `swe/` → `### SWE Skills`
     - `lifecycle/` → `### Lifecycle Skills`
     - `quality/` → `### Quality Skills`
   - Files to update (all 6, every time):

     | # | File | Location |
     |---|------|----------|
     | 1 | `.github/copilot-instructions.md` | `## Skills` → appropriate subsection |
     | 2 | `AGENTS.md` (repo root) | `## Skills` → appropriate subsection |
     | 3 | `CLAUDE.md` (repo root) | `## Skills` → appropriate subsection |
     | 4 | `src/ai_engineering/templates/project/copilot-instructions.md` | `## Skills` → appropriate subsection |
     | 5 | `src/ai_engineering/templates/project/AGENTS.md` | `## Skills` → appropriate subsection |
     | 6 | `src/ai_engineering/templates/project/CLAUDE.md` | `## Skills` → appropriate subsection |

   - Insert alphabetically within the subsection for consistency.

### Phase 5: Update Counters

7. **Update skill count in product-contract** — edit `.ai-engineering/context/product/product-contract.md`.
   - Update the `Active Objectives` line (e.g., "19 skills" → "21 skills").
   - Update the `KPIs` table row for `Agent coverage` (e.g., "19 skills + 8 agents" → "21 skills + 8 agents").
   - The count must match the actual number of skills listed in the instruction files.

### Phase 6: Changelog

8. **Add changelog entry** — edit `CHANGELOG.md`.
   - Add under `## [Unreleased] → ### Added`.
   - Format: `- <Skill name> skill for <purpose summary>.`

### Phase 7: Cross-Reference

9. **Update related skills** — add the new skill to `## References` of skills that relate to it.
   - If the new skill extends or complements an existing skill, add a reference in both directions.

10. **Update related agents** — add the new skill to `## Referenced Skills` of agents that would use it.
    - If an agent's behavior involves the new skill's procedure, add the reference.

### Phase 8: Verify

11. **Run the verification checklist** — confirm all registration points are complete.

    | # | Check | How to verify |
    |---|-------|---------------|
    | 1 | Canonical file exists | `Test-Path .ai-engineering/skills/<category>/<name>.md` |
    | 2 | Follows template structure | Has Purpose, Trigger, Procedure, Output Contract, Governance Notes, References |
    | 3 | Template mirror exists | `Test-Path src/ai_engineering/templates/.ai-engineering/skills/<category>/<name>.md` |
    | 4 | Mirror is identical | `diff` canonical vs. mirror — 0 differences |
    | 5 | Listed in all 6 files | `grep` for the skill path in each instruction file |
    | 6 | Count matches | Count skills in instruction files = count in product-contract |
    | 7 | CHANGELOG updated | Entry under `## [Unreleased] → ### Added` |
    | 8 | Cross-references added | Related skills/agents reference the new skill |

## Output Contract

- Canonical skill file at `.ai-engineering/skills/<category>/<name>.md` following template structure.
- Identical template mirror at `src/ai_engineering/templates/.ai-engineering/skills/<category>/<name>.md`.
- Reference entry in all 6 instruction files under the correct subsection.
- Updated skill count in `product-contract.md` (objectives + KPIs).
- Changelog entry in `CHANGELOG.md`.
- Cross-references in related skills and agents.
- Verification checklist passes all 8 checks.

## Governance Notes

- No Python code changes are needed — installer, ownership, packaging, and maintenance all use glob-based discovery.
- Template mirror must be byte-identical to canonical — never diverge.
- Skill count in product-contract must match actual count listed in instruction files.
- Skills are framework-managed content (`OwnershipLevel.FRAMEWORK_MANAGED`) — they follow the governed update flow.
- Never create a skill that duplicates an existing skill's purpose — extend instead.
- Skill references use paths relative to `.ai-engineering/` (e.g., `standards/framework/core.md`, not `.ai-engineering/standards/framework/core.md`).

## References

- `standards/framework/core.md` — governance structure, ownership model, lifecycle.
- `context/product/framework-contract.md` — template packaging and replication rule.
- `skills/swe/prompt-engineer.md` — prompt engineering for skill content authoring.
- `skills/lifecycle/create-agent.md` — companion procedure for agent registration.
- `skills/lifecycle/create-spec.md` — spec creation procedure (spec-first enforcement).
- `skills/lifecycle/delete-skill.md` — inverse procedure for skill removal.
- `skills/lifecycle/content-integrity.md` — post-change validation of governance content.
- `skills/swe/changelog-documentation.md` — changelog entry formatting.
