---
name: ai-onboard
description: "Use this skill for structured codebase onboarding: progressive discovery of architecture, key files, patterns, conventions, and team standards. Best for new team members or developers encountering an unfamiliar codebase."
---


# Onboard

## Purpose

Structured codebase onboarding: progressive discovery of architecture, key files, patterns, conventions, and team standards. Produces understanding, not documentation -- the developer walks away knowing where things are, why they are there, and where to start working.

## Trigger

- Command: guide agent invokes onboard or user says "onboard me", "where do I start", "how is this organized".

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"onboard"}'` at skill start. Fail-open -- skip if ai-eng unavailable.

## Procedure

### Phase 1: High-Level Structure

1. **Read root directory** -- list top-level files and directories.
2. **Classify structure** -- monorepo, single package, framework-governed, or hybrid.
3. **Present overview** -- ASCII tree with 1-line descriptions. Highlight the 3-5 most important directories.

**Socratic checkpoint**: "Based on this structure, what kind of project do you think this is?"

### Phase 2: Technology Stack and Standards

1. **Read config files** -- `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, or equivalent.
2. **Identify stack** -- language, framework, package manager, test runner, linter, formatter.
3. **Read quality standards** -- summarize key thresholds from `standards/` if present.
4. **Read CI/CD config** -- `.github/workflows/`, `Makefile`, or equivalent.
5. **Present stack summary** -- concise table of technologies and their roles.

### Phase 3: Architecture Patterns

1. **Identify layers** -- presentation, business logic, data access, infrastructure.
2. **Map entry points** -- main files, CLI entry, API routes, event handlers.
3. **Trace a request** -- follow one typical request/command from entry to output.
4. **Present architecture** -- ASCII diagram showing layers, modules, and data flow.

**Socratic checkpoint**: "If you needed to add a new feature, where would you start based on this architecture?"

### Phase 4: Key Files

Identify files a developer encounters first: entry points, configuration, models/types, API surface, tests. Present as ordered list with file path and 1-line description ("read this first, then this").

### Phase 5: Naming Conventions and Coding Patterns

Analyze naming conventions (files, functions, classes), code organization (imports, module structure), and common idioms (error handling, logging, test patterns). Present with `file:line` examples from the actual codebase.

### Phase 6: Team Standards

1. **Check for standards** -- `standards/`, `standards/team/`, `.ai-engineering/standards/`.
2. **Check for contributing guide** -- `CONTRIBUTING.md`, `docs/contributing.md`.
3. **Check for ADRs** -- `docs/adr/`, `decisions/`, `state/decision-store.json`.
4. **Present standards summary** -- commit conventions, PR process, review process, quality gates. If no formal standards, note patterns observed in the codebase.

**Socratic checkpoint**: "What area of the codebase are you most interested in working on?"

### Phase 7: Learning Path

Present a 3-tier progressive learning path: **Start here** (2-3 foundational files) -> **Build understanding** (3-5 core logic files) -> **Go deeper** (advanced topics). End with one small hands-on task to validate understanding. Format as numbered file list with path and reason for each entry.

## Headless Mode

When invoked by another agent: skip Socratic checkpoints, run full 7-phase procedure, output complete onboarding without pausing. If scope is ambiguous, onboard the entire repository.

## When NOT to Use

- **Deep-dive on a single concept** -- use `guide teach` or `explain`.
- **Decision archaeology** -- use `guide why`.
- **Generating documentation** -- use `docs` or `write`. Onboard teaches; it does not produce artifacts.

## Output Contract

- Progressive discovery across 7 phases with actual file path references.
- ASCII diagrams for architecture (same rules as explain skill).
- Socratic checkpoints between phases (skipped in headless mode).
- Learning path tailored to developer's stated goals.
- Strictly read-only. No code changes, no documentation artifacts.

## Governance Notes

Inherits language rules from `.claude/skills/ai-explain/SKILL.md`: precise terminology, no filler words, active voice.

**Onboarding-specific**: never assume project knowledge (assume technology knowledge), progressive disclosure across phases, adapt pace to developer's existing knowledge. The learning path is a suggestion, not a mandate.

| Error situation | Recovery |
|-----------------|----------|
| No config files | Infer stack from file extensions; note inference |
| No standards dir | Analyze codebase for implicit conventions |
| Monorepo | Ask which service to onboard first |
| Developer knows parts | Skip known phases; ask what is unfamiliar |

## References

- `.claude/agents/ai-guide.md` -- guide agent that invokes onboard.
- `.claude/skills/ai-explain/SKILL.md` -- 3-tier depth model, language rules.
- `.claude/agents/ai-guide.md` -- guide agent behavioral contract.
$ARGUMENTS
