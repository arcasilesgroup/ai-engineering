---
name: validate
description: Validate the AI Engineering Framework installation, structure, and platform configuration
---

## Context

Validates that the AI Engineering Framework is correctly installed and configured in the current project. Checks for required files, correct structure, valid content, and platform configuration.

## Inputs

$ARGUMENTS - Optional: "fix" to auto-fix issues, or "verbose" for detailed output

## Steps

### 1. Check Required Files

Verify these files exist:
- `CLAUDE.md` - Master entry point
- `.claude/settings.json` - Permissions config
- At least one file in `.claude/skills/`
- At least one file in `standards/`
- `context/project.md` - Project context

### 2. Check File Content

For each required file:
- Verify it's not empty.
- Check YAML frontmatter is valid (for skills and agents).
- Check for unresolved `{{PLACEHOLDER}}` values in context files (warn, don't fail).

### 3. Check Standards

Verify referenced standards files exist:
- `standards/global.md`
- At least one stack-specific standard matching the project's tech stack.

### 4. Check Skills

For each file in `.claude/skills/*/SKILL.md`:
- Verify YAML frontmatter has `name` and `description` fields.
- Verify the file has `## Steps` section.
- Verify the file has `## Verification` section.

### 5. Check Agents

For each file in `.claude/agents/`:
- Verify YAML frontmatter has `description` and `tools` fields.
- Verify the file has `## Objective` and `## Process` sections.

### 6. Check Hooks

For each file in `.claude/hooks/`:
- Verify it is executable (`chmod +x`).
- Verify it starts with a valid shebang (`#!/usr/bin/env bash`).
- Verify hooks are registered in `.claude/settings.json`.

### 7. Check Platform Configuration

Detect and verify platform setup:
- Read git remote URL: `git remote get-url origin`
- If `github.com`: verify `gh` CLI is available (`gh --version`) and authenticated (`gh auth status`)
- If `dev.azure.com` or `visualstudio.com`: verify `az` CLI is available (`az --version`) and authenticated (`az account show`)
- Report platform-specific features available

### 8. Check Version

- Check for `.ai-version` file
- Compare with framework `VERSION` if available
- **Check for remote updates** (fallback chain: `gh api` → `git ls-remote` → `curl VERSION`)
- Check `DEPRECATIONS.json` for deprecated version warnings
- Warn if outdated or deprecated

### 9. Check CI/CD (if applicable)

- If `.github/workflows/` exists: verify workflow files are valid YAML.
- If `pipelines/` exists: verify pipeline files are valid YAML.

### 10. Report

    ## Framework Validation Report

    **Status:** VALID | INVALID
    **Version:** X.X.X

    ### Files
    - [x] CLAUDE.md
    - [x] .claude/settings.json
    - [x] Skills: X found
    - [x] Agents: X found
    - [x] Hooks: X found (X executable)
    - [x] Standards: X found

    ### Platform
    - [x] Platform: GitHub | Azure DevOps | Not detected
    - [x] CLI: gh | az | Not found
    - [x] Auth: Authenticated | Not authenticated

    ### Warnings
    - [Unresolved placeholders, missing optional files, outdated version, deprecated version]

    ### Errors
    - [Missing required files, invalid content]

    ### Recommendations
    - [Suggestions for improvement]

## Verification

- All required files checked
- Content validation performed
- Platform detection verified
- Report is accurate and actionable
