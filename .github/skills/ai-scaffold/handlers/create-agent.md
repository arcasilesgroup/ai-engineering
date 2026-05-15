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
