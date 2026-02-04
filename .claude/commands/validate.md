---
description: Validate the AI Engineering Framework installation and structure
---

## Context

Validates that the AI Engineering Framework is correctly installed and configured in the current project. Checks for required files, correct structure, and valid content.

## Inputs

$ARGUMENTS - Optional: "fix" to auto-fix issues, or "verbose" for detailed output

## Steps

### 1. Check Required Files

Verify these files exist:
- `CLAUDE.md` - Master entry point
- `.claude/settings.json` - Permissions config
- At least one file in `.claude/commands/`
- At least one file in `standards/`
- `context/project.md` - Project context

### 2. Check File Content

For each required file:
- Verify it's not empty.
- Check YAML frontmatter is valid (for commands and agents).
- Check for unresolved `{{PLACEHOLDER}}` values in context files (warn, don't fail).

### 3. Check Standards

Verify referenced standards files exist:
- `standards/global.md`
- At least one stack-specific standard matching the project's tech stack.

### 4. Check Commands

For each file in `.claude/commands/`:
- Verify YAML frontmatter has `description` field.
- Verify the file has `## Steps` section.
- Verify the file has `## Verification` section.

### 5. Check Agents

For each file in `.claude/agents/`:
- Verify YAML frontmatter has `description` and `tools` fields.
- Verify the file has `## Objective` and `## Process` sections.

### 6. Check CI/CD (if applicable)

- If `.github/workflows/` exists: verify workflow files are valid YAML.
- If `pipelines/` exists: verify pipeline files are valid YAML.

### 7. Report

```markdown
## Framework Validation Report

**Status:** VALID | INVALID

### Files
- [x/] CLAUDE.md
- [x/] .claude/settings.json
- [x/] Commands: X found
- [x/] Agents: X found
- [x/] Standards: X found

### Warnings
- [Unresolved placeholders, missing optional files]

### Errors
- [Missing required files, invalid content]

### Recommendations
- [Suggestions for improvement]
```

## Verification

- All required files checked
- Content validation performed
- Report is accurate and actionable
