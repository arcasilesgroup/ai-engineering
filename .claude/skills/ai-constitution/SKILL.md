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

Generate and maintain `CONSTITUTION.md` — the foundational governance document that defines who the project is, what it aims to achieve, what principles are non-negotiable, and what the AI must NEVER do.

This is the first document loaded at Step 0 of every skill and agent invocation. It governs all AI behavior in the project.

## When to Use

- First-time `ai-eng install` -- seed the constitution with auto-detected data + interview
- Project scope changes -- update identity, mission, or principles
- Agents keep violating boundaries -- strengthen prohibitions
- New team member needs orientation -- review the constitution
- Formal amendment needed -- version bump with governance trail

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

## Procedure

1. **Auto-detect** -- read `manifest.yml`, `pyproject.toml`, `package.json`, `Cargo.toml`, or `*.csproj` to infer:
   - Project name and stack
   - Existing quality gate configuration
   - Framework version

2. **Read existing** -- if `CONSTITUTION.md` exists, load current values as defaults. If only `.ai-engineering/CONSTITUTION.md` exists, load it as a compatibility fallback.

3. **Interview** -- for any section that cannot be inferred, ask the user:
   - **Identity**: What does this project do? Who is it for? (1-3 sentences)
   - **Mission**: What are the 2-3 measurable goals? What is the "north star"?
   - **Principles**: What are the non-negotiable rules? (guide with examples from the framework)
   - **Prohibitions**: What must the AI NEVER do in this project?
   - **Boundaries**: What is framework-owned vs team-owned?

4. **Write** -- save to `CONSTITUTION.md` using the 7-section structure. Minimal template skeleton:

   ```markdown
   # CONSTITUTION

   ## 1. Identity

   <!-- Project name, purpose, audience -->

   ## 2. Mission

   <!-- Measurable goals, north star metric -->

   ## 3. Principles

   <!-- Non-negotiable rules for AI behavior -->

   ## 4. Prohibitions

   <!-- What the AI must NEVER do -->

   ## 5. Quality Gates

   <!-- Thresholds: coverage, complexity, security -->

   ## 6. Boundaries

   <!-- Framework-owned vs team-owned zones -->

   ## 7. Governance

   <!-- version: "1.0.0" -->
   <!-- ratified: "YYYY-MM-DD" -->
   <!-- last_amended: "YYYY-MM-DD" -->
   <!-- amendments: [] -->
   ```

5. **Verify** -- confirm all 7 sections are populated and internally coherent.

6. **Version** -- set governance metadata (version, ratified date, last amended).

## Arguments

- `generate` -- create from scratch with auto-detect + interview
- `update` -- update specific sections preserving the rest. User specifies section(s) to update in the prompt. The skill loads the existing document, presents the target section for review, and applies changes while preserving all other sections.
- `amend` -- formal amendment with semantic version bump and governance trail. Record amendment in CONSTITUTION.md governance metadata (version, date, description) and emit a framework event to `state/framework-events.ndjson`.

## Quick Reference

```
/ai-constitution generate   # create from scratch
/ai-constitution update     # update specific sections
/ai-constitution amend      # formal amendment with version bump
```

## Integration

- **Called by**: installer (governance phase), `/ai-start`
- **Reads**: `manifest.yml`, package files, existing `CONSTITUTION.md`
- **Writes**: `CONSTITUTION.md`
- **Consumed by**: ALL skills and agents via Step 0 protocol

$ARGUMENTS
