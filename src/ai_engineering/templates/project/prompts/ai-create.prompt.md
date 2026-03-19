---
name: ai-create
description: Use when creating a new skill or agent for the ai-engineering framework, with TDD-based pressure testing and CSO-optimized descriptions.
argument-hint: "skill <name>|agent <name>"
mode: agent
---



# Create

## Purpose

Create new skills and agents for the ai-engineering framework using TDD. Skills go through a pressure-test cycle (RED/GREEN/REFACTOR) to ensure they actually change agent behavior. Agents are scaffolded with mandate, self-challenge protocol, and capability declarations.

## Trigger

- Command: `/ai-create skill <name>` or `/ai-create agent <name>`
- Context: framework needs a new capability that no existing skill or agent covers.

## Modes

### skill <name> -- Create a new skill

**Phase RED -- Baseline without the skill**:

1. **Define test scenarios** -- write 3-5 prompts that the skill should handle. These are the "pressure tests."
2. **Run baseline** -- execute the prompts WITHOUT the new skill loaded. Record how the agent behaves.
3. **Identify gaps** -- document specific failures: wrong approach, missed steps, bad output format, skipped governance.

**Phase GREEN -- Write minimal skill**:

4. **Scaffold** -- create `.github/prompts/ai-{name}.prompt.md` with frontmatter:
   ```yaml
   ---
   name: ai-{name}
   description: "{CSO-optimized: Use when [triggering conditions]}"
   argument-hint: "{expected arguments}"
   ---
   ```
5. **Write skill body** -- address ONLY the gaps found in RED phase. Include:
   - Purpose (2-3 lines)
   - Trigger (command + context)
   - Procedure (numbered steps)
   - When NOT to Use (differentiation from similar skills)
6. **CSO-optimize description** -- the `description` field is the skill's search ranking. It must describe triggering conditions, not summarize what the skill does. Pattern: "Use when [specific situation the user is in]".
7. **Run pressure tests again** -- verify the skill changes behavior for all test scenarios.

**Phase REFACTOR -- Close loopholes**:

8. **Test edge cases** -- try prompts that should NOT trigger this skill. Verify they do not.
9. **Add guardrails** -- if edge-case prompts incorrectly triggered the skill, add "When NOT to Use" entries.
10. **Final validation** -- all pressure tests pass, no false triggers.

### agent <name> -- Create a new agent

1. **Define mandate** -- what is this agent's singular responsibility? An agent does ONE thing.
2. **Scaffold** -- create `.github/agents/{name}.agent.md` with:
   - Identity (role, experience level, specialization)
   - Mandate (what it owns, what it does not own)
   - Capabilities (declared permissions: read-only, read-write, which files/paths)
   - Behavior (modes, procedures)
   - Boundaries (hard limits, escalation protocol)
   - Self-challenge protocol (questions the agent asks itself before acting)
3. **Register** -- add to `manifest.yml` agents section.
4. **Create skill entry point** -- create matching `/ai-{name}` skill that activates the agent.

## Registration Checklist

After creating any skill or agent:

- [ ] File created at correct path
- [ ] Frontmatter has `name`, `description`, `argument-hint`
- [ ] Description is CSO-optimized (triggering conditions, not summary)
- [ ] Registered in `manifest.yml`
- [ ] Mirror files created for other IDE surfaces (`.agents/`, `.github/prompts/`)
- [ ] No overlap with existing skills (checked `/ai-find` or skill list)

## CSO Description Patterns

| Bad (summary) | Good (CSO trigger) |
|---------------|-------------------|
| "Generates standup notes" | "Use when preparing daily standup notes or summarizing recent PR activity" |
| "Sprint planning tool" | "Use when planning a new sprint or running a retrospective" |
| "Resolves git conflicts" | "Use when git reports merge conflicts during rebase, merge, or cherry-pick" |

## Quick Reference

```
/ai-create skill standup     # create a new standup skill with TDD
/ai-create agent reviewer    # create a new reviewer agent
```

## Integration

- **Calls**: `handlers/create-skill.md`, `handlers/create-agent.md`, `handlers/validate.md`
- **Triggers sync**: `python scripts/sync_command_mirrors.py` after creation

$ARGUMENTS

---

# Handler: create-agent

## Purpose

Scaffold a new agent with standardized frontmatter, defined mandate, referenced skills, and mirror generation.

## Procedure

### 1. Validate name
- Must not conflict with existing agents (check `.github/agents/`)

### 2. Define identity
- What is the agent's singular responsibility?
- What model? (opus for complex tasks, sonnet for simple/fast)
- What color? (check existing agents to avoid duplicates)
- What tools? (Read, Write, Edit, Bash, Glob, Grep — pick minimum needed)

### 3. Scaffold agent file
Frontmatter order (mandatory):
```yaml
---
name: ai-<name>
description: "[Mandate in one sentence]."
color: <color>
model: <opus|sonnet>
tools: [Read, Glob, Grep, ...]
---
```

Body structure:
1. `# <Name>` (no prefix)
2. `## Identity` — 3-4 sentences defining expertise and perspective
3. `## Mandate` — singular responsibility, 1-2 sentences
4. `## Behavior` — numbered sections for the agent's workflow
5. `## Referenced Skills` — list of skill paths (validate they exist!)
6. `## Boundaries` — what the agent does NOT do
7. `### Escalation Protocol` — iteration limit, never loop silently

### 4. Register
- Add to `.ai-engineering/manifest.yml` agents section
- Increment `total` count

### 5. Generate mirrors
- Run `python scripts/sync_command_mirrors.py`
# Handler: create-skill

## Purpose

Scaffold a new skill with standardized frontmatter, CSO-optimized description, optional handlers, manifest registration, and mirror generation.

## Procedure

### 1. Validate name
- Must not conflict with existing skills (check `.github/prompts/`)
- Prefix with `ai-` automatically if not provided

### 2. Interrogate (max 3 questions)
- What does the skill do? (→ Purpose)
- What triggers it? (→ CSO description: "Use when...")
- Does it have multiple modes? (→ handlers needed?)

### 3. Scaffold SKILL.md
Frontmatter order (mandatory):
```yaml
---
name: ai-<name>
description: "Use when [trigger condition]. [What it does]."
argument-hint: "[args]"
---
```

Body structure:
1. `# <Name>` (no prefix)
2. `## Purpose` — 2-3 sentences
3. `## When to Use` — bullet list of trigger conditions
4. `## Process` — numbered steps or mode dispatch
5. `## Quick Reference` — code block with invocation examples
6. `## Integration` — Called by, Calls, Transitions to
7. `## References` — related skills/files
8. `$ARGUMENTS`

### 4. Create handlers (if multi-mode)
For each mode: create `handlers/<mode>.md` with Purpose, Procedure sections.

### 5. Register
- Add to `.ai-engineering/manifest.yml` skills registry
- Increment `total` count

### 6. Generate mirrors
- Run `python scripts/sync_command_mirrors.py`

### 7. Pressure-test
Present 5 example prompts that SHOULD trigger this skill. Verify the CSO description would match.

## CSO Description Rules

- Start with "Use when" (trigger-focused, not summary-focused)
- Bad: "Generates standup notes from PR activity"
- Good: "Use when preparing daily standup notes or summarizing recent PR and commit activity for team updates"
# Handler: validate

## Purpose

Post-creation validation. Verifies a skill or agent is correctly configured across all surfaces.

## Procedure

### 1. CSO Description Quality
- Does description start with "Use when"?
- Does it describe a trigger condition, not a summary?
- Is it specific enough to distinguish from other skills?

### 2. Frontmatter Order
- Check field order matches canonical:
  - Agents: name, description, color, model, tools
  - Skills: name, description, [optional fields], argument-hint

### 3. Mirror Parity
- Verify skill/agent exists in all 3 surfaces:
  - `.github/prompts/ai-<name>.prompt.md` or `.github/agents/<name>.agent.md`
  - `.agents/skills/<name>/SKILL.md` or `.agents/agents/ai-<name>.md`
  - `.github/prompts/ai-<name>.prompt.md` or `.github/agents/<name>.agent.md`
- Verify handlers are mirrored too (if any)

### 4. Manifest Registration
- Verify skill/agent is in `.ai-engineering/manifest.yml`
- Verify `total` count matches actual count

### 5. Cross-Reference Integrity
- All Referenced Skills paths point to existing files
- No ghost skill references

### 6. Report
```
✓ CSO description: PASS
✓ Frontmatter order: PASS
✓ Mirror parity: 3/3 surfaces
✓ Manifest registered: PASS
✓ Cross-references: PASS (0 broken)
```
