---
name: migrate-claude-md
description: Migrate a legacy CLAUDE.md to the sectioned format for safe framework updates
---

## Context

This skill migrates a legacy CLAUDE.md (without section markers) to the new sectioned format that allows safe framework updates while preserving team customizations.

The sectioned format uses HTML comment markers:
- `<!-- BEGIN:AI-FRAMEWORK:vX.X.X -->` ... `<!-- END:AI-FRAMEWORK -->` — Framework content (auto-updated)
- `<!-- BEGIN:TEAM -->` ... `<!-- END:TEAM -->` — Team content (never overwritten)

## Inputs

$ARGUMENTS - Optional: path to CLAUDE.md (defaults to ./CLAUDE.md)

## Steps

### 1. Check Current State

Read the target CLAUDE.md file and check:
- Does it exist?
- Does it already have section markers?

If markers already exist:
```
CLAUDE.md already has section markers. No migration needed.
```
Exit successfully.

### 2. Analyze Content

Compare the target CLAUDE.md with `CLAUDE.framework.md`:
- Identify which sections are standard framework content
- Identify which sections have been customized by the team
- Look for team additions (custom rules, danger zones, project-specific content)

Key indicators of team customization:
- Custom entries in Critical Rules (NEVER/ALWAYS)
- Custom danger zones
- Project-specific standards references
- Modified workflow steps
- Custom skills or agents references
- Project Overview content (not placeholder)

### 3. Create Backup

```bash
cp CLAUDE.md CLAUDE.md.backup-$(date +%Y%m%d-%H%M%S)
```

### 4. Extract Team Content

Create the TEAM section with any customizations found:
- Project Overview (from existing file)
- Any custom Critical Rules that aren't in the framework
- Any custom Danger Zones
- Any other team-specific additions

### 5. Generate Migrated File

Combine:
1. Framework section from `CLAUDE.framework.md`
2. Team section with extracted customizations

Write to CLAUDE.md.

### 6. Show Diff

Show the user what changed:
```bash
diff CLAUDE.md.backup-* CLAUDE.md
```

### 7. Report

```
## Migration Complete

**Backup:** CLAUDE.md.backup-YYYYMMDD-HHMMSS

### Framework Section
- Identity, Architecture, Technology Stack
- Critical Rules (standard)
- Verification Protocol
- Reconnaissance, Two Options, Danger Zones
- Layered Memory, Reliability Template
- Standards, Learnings, Quality Gates
- Workflow, Skills, Agents, Parallel Work

### Team Section
- Project Overview: [preserved/placeholder]
- Custom Rules: [X found / none]
- Custom Danger Zones: [X found / none]
- Other Customizations: [list or none]

### Next Steps
1. Review the migrated CLAUDE.md
2. Add any team-specific content to the TEAM section
3. Future updates will preserve your TEAM section automatically
```

## Verification

- Backup file exists
- New CLAUDE.md has both markers: `BEGIN:AI-FRAMEWORK` and `BEGIN:TEAM`
- Team content is preserved in the TEAM section
- File is valid markdown
