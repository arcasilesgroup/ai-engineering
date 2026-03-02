---
name: simplify
description: "Reduce verbosity and duplication in governance/docs content while preserving intent and constraints. Use when docs become repetitive, hard to scan, or after governance simplification passes."
metadata:
  version: 1.0.0
  tags: [docs, simplify, clarity, compression]
  ai-engineering:
    scope: read-write
    token_estimate: 680
---

# Docs Simplify

## Purpose

Reduce verbosity and duplication in documentation without losing required meaning.

## Trigger

- Docs become repetitive or hard to scan.
- Governance simplification passes.

## When NOT to Use

- **Writing new documentation** (README, guides, CONTRIBUTING) — use `docs` instead. Simplify improves existing content; docs creates new content.
- **Explaining concepts** (teaching, Feynman-style breakdown) — use `explain` instead.
- **Changelog entries** — use `changelog` instead.

## Procedure

1. Identify duplicated and low-signal passages.
2. Preserve non-negotiable clauses and semantic intent.
3. Rewrite for concise, consistent wording.
4. Re-validate cross-references and counters.

## Output Contract

- Simplified document set with rationale and preserved constraints.

## Governance Notes

- Simplification cannot weaken policy or remove required controls.

## References

- `agents/write.md`
- `skills/docs/SKILL.md`
