---
name: ai-constitution
description: >-
  Use when installing ai-engineering on a new project, when AI agents need
  foundational rules about what this project is, what it aims to achieve,
  and what must NEVER be violated. Trigger for 'set up the constitution',
  'define project principles', 'what are the rules for this project',
  'agents keep breaking boundaries', 'update the constitution',
  'new team member needs orientation'. Generates CONSTITUTION.md —
  the non-negotiable governance document consumed by ALL skills and agents
  at Step 0.
effort: medium
argument-hint: "[generate|update|amend]"
---


# Constitution

## Purpose

Generate and maintain `.ai-engineering/CONSTITUTION.md` — the foundational governance document that defines who the project is, what it aims to achieve, what principles are non-negotiable, and what the AI must NEVER do.

This is the first document loaded at Step 0 of every skill and agent invocation. It governs all AI behavior in the project.

## When to Use

- First-time `ai-eng install` -- seed the constitution with auto-detected data + interview
- Project scope changes -- update identity, mission, or principles
- Agents keep violating boundaries -- strengthen prohibitions
- New team member needs orientation -- review the constitution
- Formal amendment needed -- version bump with governance trail

## Procedure

1. **Auto-detect** -- read `manifest.yml`, `pyproject.toml`, `package.json`, `Cargo.toml`, or `*.csproj` to infer:
   - Project name and stack
   - Existing quality gate configuration
   - Framework version

2. **Read existing** -- if `.ai-engineering/CONSTITUTION.md` exists, load current values as defaults.

3. **Interview** -- for any section that cannot be inferred, ask the user:
   - **Identity**: What does this project do? Who is it for? (1-3 sentences)
   - **Mission**: What are the 2-3 measurable goals? What is the "north star"?
   - **Principles**: What are the non-negotiable rules? (guide with examples from the framework)
   - **Prohibitions**: What must the AI NEVER do in this project?
   - **Boundaries**: What is framework-owned vs team-owned?

4. **Write** -- save to `.ai-engineering/CONSTITUTION.md` using the 7-section structure:
   - Identity, Mission, Principles, Prohibitions, Quality Gates, Boundaries, Governance

5. **Verify** -- confirm all 7 sections are populated and internally coherent.

6. **Version** -- set governance metadata (version, ratified date, last amended).

## Arguments

- `generate` -- create from scratch with auto-detect + interview
- `update` -- update specific sections preserving the rest
- `amend` -- formal amendment with semantic version bump and governance trail

## Quick Reference

```
/ai-constitution generate   # create from scratch
/ai-constitution update     # update specific sections
/ai-constitution amend      # formal amendment with version bump
```

## Integration

- **Called by**: installer (governance phase), `/ai-start`
- **Reads**: `manifest.yml`, package files, existing `CONSTITUTION.md`
- **Writes**: `.ai-engineering/CONSTITUTION.md`
- **Consumed by**: ALL skills and agents via Step 0 protocol

$ARGUMENTS
