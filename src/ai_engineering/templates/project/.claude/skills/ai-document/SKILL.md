---
name: ai-document
version: 2.0.0
description: "Documentation authoring with modes: generate (create/update docs) and simplify (reduce verbosity preserving accuracy)."
argument-hint: "generate|simplify"
tags: [documentation, open-source, readme, guides, simplification]
---


# Docs

## Purpose

Documentation authoring and simplification. Modes: `generate` creates/updates documentation (README, CONTRIBUTING, guides, API docs, ADRs); `simplify` reduces verbosity while preserving accuracy and constraints. Consolidates docs and simplify skills.

## Trigger

- Command: `/ai:docs [generate|simplify]`
- Context: documentation creation, update, review, or simplification.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"docs"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## Modes

### generate — Create/update documentation

Transform codebase knowledge into polished documentation. Reads code, configuration, `.ai-engineering` context, and project metadata. Writes what users can DO, not what you BUILT.

Types: README, CONTRIBUTING, guides, API docs, ADRs, Wiki pages.

### simplify — Reduce verbosity

Apply signal-to-noise optimization to existing content. Remove duplication, tighten language, preserve constraints and accuracy. Produce before/after metrics (word count, readability, link count).

## Shared Rules (Canonical)

Use these rules as the single source of truth for documentation behavior shared by skill and agent.

- **DOC-R1 (Mode selection):** choose `generate` for net-new docs and `simplify` for existing content optimization.
- **DOC-R2 (Type detection):** classify doc type (tutorial/how-to/explanation/reference/ADR/changelog) before drafting.
- **DOC-R3 (Validation):** verify internal links and markdown structure before completion.
- **DOC-R4 (Style contract):** apply Divio structure + Google developer documentation style conventions.
- **DOC-B1 (Doc-only writes):** allow writes to documentation artifacts only; no source-code or test changes.

## Procedure

### Generate

1. Apply shared rules `DOC-R1..DOC-R4`.
2. Enforce shared boundary `DOC-B1`.

### Simplify

1. Apply shared rules `DOC-R1..DOC-R4` for simplification context.
2. Enforce shared boundary `DOC-B1`.
3. Report before/after metrics (word count, readability, link count).
$ARGUMENTS
