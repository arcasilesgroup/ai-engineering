# Handler: create-skill

## Purpose

Scaffold a new skill with standardized frontmatter, CSO-optimized description, optional handlers, manifest registration, and mirror generation.

## Procedure

### 1. Validate name
- Must not conflict with existing skills (check `.agents/skills/`)
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
