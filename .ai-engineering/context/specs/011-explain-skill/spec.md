---
id: "011"
slug: "explain-skill"
status: "in-progress"
created: "2026-02-11"
---

# Spec 011 — Explain Skill: Feynman-Style Code & Concept Explanations

## Problem

No skill exists for structured explanations. Users asking "how does this work?" get ad-hoc responses with no consistent methodology, depth control, or codebase-grounded examples. Existing SWE skills cover review, debug, refactor, and documentation, but none focus on teaching and explaining code to the user.

## Solution

Create `swe:explain` skill following the Feynman technique — 3-tier depth (Quick/Standard/Deep), 6 explanation sections (One-Liner, Analogy, Step-by-Step, Gap Check, Prove It, Context Map), codebase-first examples. If you cannot explain it simply, you do not understand it well enough.

## Scope

### In Scope

- Canonical skill file at `.ai-engineering/skills/swe/explain.md` with all 6 mandatory sections.
- Template mirror (byte-identical).
- Slash command wrapper + mirror (byte-identical).
- 8 instruction file registrations.
- Counter update (32 → 33 skills).
- Changelog entry.
- Cross-references: 3 skills (debug, code-review, architecture-analysis) + 2 agents (debugger, architect).

### Out of Scope

- New knowledge files.
- Agent creation.
- Changes to other skills' procedures.

## Acceptance Criteria

1. Canonical skill file exists at `.ai-engineering/skills/swe/explain.md` with all 6 mandatory sections.
2. Template mirror is byte-identical.
3. Slash command wrapper + mirror exist and are byte-identical.
4. All 8 instruction files list the skill under `### SWE Skills`.
5. Product-contract shows 33 skills (Active Objectives + KPIs).
6. CHANGELOG has entry under `[Unreleased] → Added`.
7. 3 skills and 2 agents cross-reference the new skill.
8. Content-integrity check passes.
