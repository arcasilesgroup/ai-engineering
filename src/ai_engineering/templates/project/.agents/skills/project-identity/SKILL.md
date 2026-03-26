---
name: project-identity
description: "Use when setting up or updating a project's identity document. Auto-detects project metadata and guides the user through a short Q&A to fill gaps."
effort: medium
argument-hint: "[generate|update]"
---



# Project Identity

## Purpose

Generate and maintain the `project-identity.md` file that gives AI agents essential context about the project: what it does, what it exposes, who consumes it, and what boundaries must not be crossed without coordination.

## When to Use

- First-time `ai-eng install` -- seed `project-identity.md` with auto-detected data
- Project scope changes -- update purpose, services, or boundaries
- New dependencies or consumers added
- Team onboarding -- verify the identity document is current

## Procedure

1. **Auto-detect** -- read `manifest.yml`, `package.json`, `pyproject.toml`, `Cargo.toml`, or `*.csproj` to infer:
   - Project name
   - Primary stack(s)
   - Dependencies
   - Version

2. **Read existing** -- if `.ai-engineering/contexts/project-identity.md` exists, load current values as defaults.

3. **Q&A for gaps** -- for any field that cannot be inferred, ask the user:
   - Purpose (1-2 sentences)
   - Services & APIs exposed or consumed
   - Downstream consumers or stakeholders
   - Boundaries (what must not change without coordination)

4. **Write** -- save to `.ai-engineering/contexts/project-identity.md` using the standard template structure (Project, Services & APIs, Dependencies & Consumers, Boundaries).

5. **Verify** -- confirm all 4 sections are populated and non-empty.

## Quick Reference

```
/ai-project-identity generate   # create from scratch with auto-detect + Q&A
/ai-project-identity update     # update existing identity document
```

## Integration

- **Called by**: installer (governance phase), `/ai-onboard`
- **Reads**: `manifest.yml`, package files, existing `project-identity.md`
- **Writes**: `.ai-engineering/contexts/project-identity.md`
- **Consumed by**: `/ai-brainstorm`, `/ai-plan`, `/ai-governance` (compliance mode)

$ARGUMENTS
