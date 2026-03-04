---
name: docs
description: "Documentation authoring with modes: generate (create/update docs) and simplify (reduce verbosity preserving accuracy)."
metadata:
  version: 2.0.0
  tags: [documentation, open-source, readme, guides, simplification]
  ai-engineering:
    scope: read-write
    token_estimate: 1050
---

# Docs

## Purpose

Documentation authoring and simplification. Modes: `generate` creates/updates documentation (README, CONTRIBUTING, guides, API docs, ADRs); `simplify` reduces verbosity while preserving accuracy and constraints. Consolidates docs and simplify skills.

## Trigger

- Command: `/ai:docs [generate|simplify]`
- Context: documentation creation, update, review, or simplification.

## Modes

### generate — Create/update documentation
Transform codebase knowledge into polished documentation. Reads code, configuration, `.ai-engineering` context, and project metadata. Writes what users can DO, not what you BUILT.

Types: README, CONTRIBUTING, guides, API docs, ADRs, Wiki pages.

### simplify — Reduce verbosity
Apply signal-to-noise optimization to existing content. Remove duplication, tighten language, preserve constraints and accuracy. Produce before/after metrics (word count, readability, link count).

## Procedure

### Generate
1. Read product-contract, active spec, relevant source files.
2. Detect documentation type (tutorial, how-to, explanation, reference, ADR).
3. Scan user-facing features and API surfaces from code.
4. Apply Google developer documentation style guide.
5. Draft content following Divio documentation system.
6. Validate cross-references and markdown syntax.

### Simplify
1. Read target content and its purpose/audience.
2. Identify: redundancy, filler, over-explanation, duplicate links.
3. Simplify while preserving: accuracy, constraints, cross-references.
4. Report: before/after word count, readability score, link count.
