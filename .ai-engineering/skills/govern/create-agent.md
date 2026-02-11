# Create Agent

## Purpose

Definitive procedure for authoring and registering a new agent in the ai-engineering framework. Ensures every registration point is updated — canonical file, template mirror, all instruction files, counters, changelog, and cross-references — eliminating partial registration risk.

## Trigger

- Command: agent invokes create-agent skill or user requests adding a new agent.
- Context: new agent persona is needed, complex multi-step task requires dedicated behavior protocol, governance content expansion.

## Procedure

### Phase 1: Design

1. **Define agent identity** — determine name, identity, capabilities, and activation triggers.
   - Name: kebab-case (`my-agent`).
   - Identity: third-person description of WHO the agent is and their expertise (e.g., "Senior technical reviewer who...").
   - Capabilities: concrete, actionable abilities as noun phrases.
   - Activation: when/how users invoke or trigger this agent.

2. **Check for duplicates** — verify no existing agent covers the same ground.
   - Review agents listed in `.github/copilot-instructions.md` under `## Agents`.
   - Search `.ai-engineering/agents/` for overlapping names or capabilities.
   - If overlap exists, consider extending the existing agent instead.

3. **Identify referenced skills and standards** — determine which skills and standards the agent will use.
   - Map behavior steps to existing skills that provide procedures.
   - Identify standards that govern the agent's domain.

### Phase 2: Author

4. **Create the canonical agent file** — write `.ai-engineering/agents/<name>.md`.
   - Follow the agent template structure:

     ```
     # Agent Name
     ## Identity
     ## Capabilities
     ## Activation
     ## Behavior
       1. **Step name** — description.
       2. **Step name** — description.
     ## Referenced Skills
     ## Referenced Standards
     ## Output Contract
     ## Boundaries
     ```

   - Identity is written in **third person** (not "I am", but "Senior ... who ...").
   - Capabilities are listed as **noun phrases** (not sentences).
   - Behavior is a **numbered protocol** (typically 4-8 sequential steps).
   - Referenced Skills and Referenced Standards are **separate sections**.
   - Boundaries explicitly state what the agent does NOT do and escalation paths.
   - References use relative paths from `.ai-engineering/` (e.g., `skills/dev/debug.md`).

5. **Validate structure** — confirm the agent file contains all required sections.
   - Identity: present, third-person, describes expertise and approach.
   - Capabilities: bullet list of concrete abilities.
   - Activation: when/how to trigger.
   - Behavior: numbered protocol, sequential, 4-8 steps.
   - Referenced Skills: at least one skill linked.
   - Referenced Standards: at least one standard linked.
   - Output Contract: measurable deliverables.
   - Boundaries: scope limitations and escalation paths.

### Phase 3: Mirror

6. **Create the template mirror** — copy to `src/ai_engineering/templates/.ai-engineering/agents/<name>.md`.
   - Content must be **byte-identical** to the canonical file.
   - This is required by framework-contract: "Keep non-state files identical between canonical and template mirror."
   - The installer uses `rglob("*")` to discover templates — no Python code changes needed.
   - The `pyproject.toml` includes `src/ai_engineering/templates/**/*.md` — no build config changes needed.

### Phase 4: Register

7. **Add to all 6 instruction files** — insert a reference line under the `## Agents` section.
   - Format: `- \`.ai-engineering/agents/<name>.md\` — one-line description.`
   - Files to update (all 6, every time):

     | # | File | Location |
     |---|------|----------|
     | 1 | `.github/copilot-instructions.md` | `## Agents` |
     | 2 | `AGENTS.md` (repo root) | `## Agents` |
     | 3 | `CLAUDE.md` (repo root) | `## Agents` |
     | 4 | `src/ai_engineering/templates/project/copilot-instructions.md` | `## Agents` |
     | 5 | `src/ai_engineering/templates/project/AGENTS.md` | `## Agents` |
     | 6 | `src/ai_engineering/templates/project/CLAUDE.md` | `## Agents` |

   - Insert alphabetically within the agents list for consistency.

### Phase 4b: Register Slash Command

7b. **Create Claude Code command wrapper** — write `.claude/commands/agent/<name>.md` (and its mirror at `src/ai_engineering/templates/project/.claude/commands/agent/<name>.md`).
   - Content is a thin 3-5 line prompt pointing to the canonical agent file. No content duplication.
   - Mirror must be byte-identical to canonical command file.

### Phase 5: Update Counters

8. **Update agent count in product-contract** — edit `.ai-engineering/context/product/product-contract.md`.
   - Update the `Active Objectives` line (e.g., "8 agents" → "9 agents").
   - Update the `KPIs` table row for `Agent coverage` (e.g., "19 skills + 8 agents" → "19 skills + 9 agents").
   - The count must match the actual number of agents listed in the instruction files.

### Phase 6: Changelog

9. **Add changelog entry** — edit `CHANGELOG.md`.
   - Add under `## [Unreleased] → ### Added`.
   - Format: `- <Agent name> agent for <purpose summary>.`

### Phase 7: Cross-Reference

10. **Update related skills** — add the new agent to `## References` of skills that the agent uses.
    - If a skill's procedure is part of the agent's behavior, add a reference in the skill: `agents/<name>.md — agent that uses this skill.`

11. **Update the agent's own references** — ensure `## Referenced Skills` and `## Referenced Standards` are complete.
    - Every skill mentioned in the behavior protocol must appear in `## Referenced Skills`.
    - Every standard governing the agent's domain must appear in `## Referenced Standards`.

### Phase 8: Verify

12. **Run the verification checklist** — confirm all registration points are complete.

    | # | Check | How to verify |
    |---|-------|---------------|
    | 1 | Canonical file exists | `Test-Path .ai-engineering/agents/<name>.md` |
    | 2 | Follows template structure | Has Identity, Capabilities, Activation, Behavior, Referenced Skills, Referenced Standards, Output Contract, Boundaries |
    | 3 | Template mirror exists | `Test-Path src/ai_engineering/templates/.ai-engineering/agents/<name>.md` |
    | 4 | Mirror is identical | `diff` canonical vs. mirror — 0 differences |
    | 5 | Listed in all 6 files | `grep` for the agent path in each instruction file |
    | 6 | Count matches | Count agents in instruction files = count in product-contract |
    | 7 | CHANGELOG updated | Entry under `## [Unreleased] → ### Added` |
    | 8 | Cross-references added | Related skills reference the new agent |

## Output Contract

- Canonical agent file at `.ai-engineering/agents/<name>.md` following template structure.
- Identical template mirror at `src/ai_engineering/templates/.ai-engineering/agents/<name>.md`.
- Reference entry in all 6 instruction files under the `## Agents` section.
- Updated agent count in `product-contract.md` (objectives + KPIs).
- Changelog entry in `CHANGELOG.md`.
- Cross-references in related skills.
- Verification checklist passes all 8 checks.

## Governance Notes

- No Python code changes are needed — installer, ownership, packaging, and maintenance all use glob-based discovery.
- Template mirror must be byte-identical to canonical — never diverge.
- Agent count in product-contract must match actual count listed in instruction files.
- Agents are framework-managed content (`OwnershipLevel.FRAMEWORK_MANAGED`) — they follow the governed update flow.
- Never create an agent that duplicates an existing agent's capabilities — extend instead.
- Agent identity must be written in third person.
- Agent references use paths relative to `.ai-engineering/` (e.g., `skills/dev/debug.md`, not `.ai-engineering/skills/dev/debug.md`).

## References

- `standards/framework/core.md` — governance structure, ownership model, lifecycle.
- `context/product/framework-contract.md` — template packaging and replication rule.
- `skills/docs/prompt-design.md` — prompt engineering for agent persona authoring.
- `skills/govern/create-skill.md` — companion procedure for skill registration.
- `skills/govern/create-spec.md` — spec creation procedure (spec-first enforcement).
- `skills/govern/delete-agent.md` — inverse procedure for agent removal.
- `skills/govern/integrity-check.md` — post-change validation of governance content.
- `skills/docs/changelog.md` — changelog entry formatting.
