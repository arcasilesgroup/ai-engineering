---
id: "024"
slug: "model-tiering-doc-enforcement"
status: "in-progress"
created: "2026-02-26"
---

# Spec 024 — Model Tiering + Documentation Enforcement

## Problem

Workflow skills (`/commit`, `/pr`, `/acho`, `/cleanup`, `/pre-implementation`) are deterministic procedures that consume expensive Opus tokens for tasks requiring zero reasoning. Additionally, documentation updates (CHANGELOG, README) are never enforced — the changelog skill exists but no workflow mandates its use, leading to stale documentation.

## Solution

1. **Introduce `model_tier` metadata** — a two-tier system (`fast` vs default) in the skill/agent schema that hints runtimes to dispatch deterministic workflows on cost-efficient models (Haiku for Claude Code, GPT-5.3-Codex or Haiku for Copilot).
2. **Add documentation gate** — a mandatory step in `/commit` and `/pr` that classifies changes and enforces changelog/doc updates for user-visible changes.

## Scope

### In Scope

- `model_tier` field added to skill and agent schema in `skills-schema.md`.
- 5 workflow skills annotated with `model_tier: fast`.
- 5 Claude Code command wrappers updated with model tier dispatch hints.
- 5 Copilot prompt wrappers updated with advisory model tier notes.
- Documentation gate step added to `/commit`, `/pr`, `/acho` procedures.
- PR checklist expanded with changelog/docs items.
- Standards updated: `core.md` non-negotiables, `quality/core.md` gate table.
- Manifest updated with model_tier annotations.
- Template mirrors synced.
- Decisions recorded in `decision-store.json`.

### Out of Scope

- Runtime model routing code (content-layer metadata only).
- Automated changelog generation (AI follows existing changelog skill procedure).
- Copilot model selection enforcement (advisory only — Copilot model is user-controlled).
- Changes to agent roster (workflows stay as skills per S0-001).

## Acceptance Criteria

1. `skills-schema.md` documents `model_tier` field with two-tier definitions and runtime mappings.
2. All 5 workflow skills have `model_tier: fast` in frontmatter.
3. All 5 Claude Code wrappers include `**Model tier: fast**` dispatch hint.
4. All 5 Copilot wrappers include advisory model tier blockquote.
5. `/commit` procedure includes documentation gate step (step 5) between secret detection and commit.
6. `/pr` procedure includes documentation gate step and expanded PR checklist.
7. `/acho` references documentation gate inheritance.
8. `core.md` non-negotiables include documentation update mandate.
9. `integrity-check` passes all 7 categories after completion.
10. Template mirrors byte-identical with canonical files.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D024-001 | Two-tier `model_tier` system: `fast` + default (omitted = Opus-class). | Opus handles everything well by default. Only deterministic workflows warrant Haiku. Middle tier adds complexity without clear benefit. Evolves D021-001 which removed multi-model routing when tooling didn't support it — Claude Code Task tool now supports `model: "haiku"`. |
| D024-002 | Documentation gate added to `/commit` and `/pr` as governance-mandated step. | Changelog skill exists but is never required. User-visible changes must update CHANGELOG.md. Internal-only changes skip silently. External docs trigger user prompt for URL. |
