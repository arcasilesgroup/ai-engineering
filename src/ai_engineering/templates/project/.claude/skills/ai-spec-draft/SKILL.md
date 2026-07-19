---
name: ai-spec-draft
description: "Produces a 14-section spec brief in `.ai-engineering/specs/drafts/<topic>-brief.md` so an operator can hand off a fully-researched problem statement to `/ai-brainstorm`. Trigger for 'draft a spec brief', 'put together a one-pager for this idea', 'research and write up the problem before brainstorming', 'capture the diagnostic for this work'. Not for executing the spec (use /ai-brainstorm → /ai-plan → /ai-build); not for ad-hoc notes (use /ai-note)."
effort: mid
argument-hint: "<topic>"
tags: [planning, brief, research, sdd]
---

# Spec Brief

Researches a problem, surveys the surface, and writes a 14-section brief to `.ai-engineering/specs/drafts/<topic>-brief.md` for handoff to `/ai-brainstorm`. The brief is the human-readable contract between idea and spec: every architectural claim cites `file:line`; machine-absolute paths become `$HOME/...`; no emoji (team convention).

## Workflow

Principles: §10.6 SDD (the brief precedes and feeds the spec), §10.5 TDD (a structural test pins the 14-section shape), §10.1 KISS (one file, one location, one handoff token).

1. **Interview intent** — ask up to 3 questions: (a) problem in one sentence, (b) audience (operator / framework dev / external user), (c) scale (single-skill / multi-wave / cross-IDE). Reasonable defaults on ambiguity.
2. **Dispatch parallel research** — run `/ai-explore` (codebase, read-only) and `/ai-research` (external, cited) in parallel, each in its own context. Wait for both.
3. **Compose 14 sections** — use the shape below. ≥ 5 `file:line` citations across the body (cross-surface briefs carry 20+). Placeholder paths (`$HOME/...`), never `/Users/...`. No emoji.
4. **Write** — output `.ai-engineering/specs/drafts/<topic>-brief.md`; kebab-case slug. Frontmatter declares `title`, `status: draft`, `audience`, `branch`, `length_estimate`, `authoring_style`, `principles_required`, `delivery_mode`, `mantra`.
5. **Emit handoff token** — print the relative path plus `/ai-brainstorm` (which reads the brief as its problem statement).
6. **Audit** — emit `framework_event kind=brief_drafted`, `component: ai-spec-draft`, `detail: {topic, path, citations_count}`.

## Brief shape (14 canonical sections)

Byte-equivalent across drafts so reviewers and downstream skills can rely on it. Empty sections allowed only when honestly N/A.

| # | Section | Holds |
|---|---------|-------|
| 1 | Vision | where we are going and why (one paragraph) |
| 2 | Scope Boundary | in scope vs explicitly NOT |
| 3 | Diagnostic Snapshot | current-state evidence with `file:line` |
| 4 | Architecture | proposed structural change; module / surface boundaries |
| 5 | Evidence Catalog | table of `file:line` citations |
| 6 | Roadmap | milestones with acceptance gates |
| 7 | Definition of Done | measurable acceptance criteria |
| 8 | Quality Stamps | §10.x anchors + contracts honoured |
| 9 | Open Decisions | choices the spec phase must resolve |
| 10 | Migration | hard rename per CONSTITUTION.md §3 — no shims |
| 11 | Risks | likelihood × impact matrix + mitigations |
| 12 | References | external sources (Anthropic skill-creator, RFCs, prior art) |
| 13 | Glossary | domain terms introduced |
| 14 | Acceptance | checklist form of Definition of Done |

Reference drafts: `.ai-engineering/specs/drafts/cli-ux-overhaul-brief.md`, `dx-excellence-refactor-brief.md`.

## Citation discipline

- Every architectural claim and every "currently / today / current state" sentence in §3 cites `file:line` — form `path/to/file.py:42`, no `../` prefixes.
- Minimum 5 citations across the body. Rewrite `/Users/...` → `$HOME/...` (`tools/skill_lint/checks/md_mirror.py` flags leaks).

## Examples

User: "draft a brief for adding a /ai-feedback skill that posts feedback to a webhook"

```
/ai-spec-draft "ai-feedback-webhook"
```

Interviews intent (collect operator feedback; operator; single-skill), dispatches `/ai-explore` + `/ai-research` in parallel, drafts the 14 sections with ≥ 5 citations, writes `.ai-engineering/specs/drafts/ai-feedback-webhook-brief.md`, prints the handoff token.

## Common mistakes

- Drafting from session context alone — unciteable claims. Always run `/ai-explore` + `/ai-research`.
- Emojis or machine paths — both fail later checks.
- Dropping sections to save lines — the 14-section shape is the contract.

## Integration

Called by: user directly. Dispatches: `/ai-explore` (codebase research, read-only) and `/ai-research` (external evidence) in parallel. Writes: `.ai-engineering/specs/drafts/<topic>-brief.md`. Audited: `framework_event kind=brief_drafted`. Pairs with: `/ai-brainstorm` (consumes the brief to produce an approved spec.md). See also: `/ai-plan` (consumes spec.md), `/ai-build` (consumes plan.md).

$ARGUMENTS
