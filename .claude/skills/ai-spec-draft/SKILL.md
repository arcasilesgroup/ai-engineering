---
name: ai-spec-draft
description: "Produces a 14-section spec brief in `.ai-engineering/specs/drafts/<topic>-brief.md` so an operator can hand off a fully-researched problem statement to `/ai-brainstorm`. Trigger for 'draft a spec brief', 'put together a one-pager for this idea', 'research and write up the problem before brainstorming', 'capture the diagnostic for this work'. Not for executing the spec (use /ai-brainstorm → /ai-plan → /ai-build); not for ad-hoc notes (use /ai-note)."
effort: mid
model_tier: sonnet
argument-hint: "<topic>"
tags: [planning, brief, research, sdd]
---


# Spec Brief

Researches the problem, surveys the existing surface, and lands a 14-section brief at `.ai-engineering/specs/drafts/<topic>-brief.md` for handoff to `/ai-brainstorm`. The brief is the human-readable contract between the idea phase and the spec phase: every claim cites `file:line` evidence; no machine paths leak into the rendered output; emojis are banned by team convention.

```
/ai-spec-draft "skills-and-agents-excellence-v2"
/ai-spec-draft "installer-windows-support"
```

## Quick Start

1. Invoke the skill with a kebab-case topic slug. Topic words drive the filename and the brief title.
2. The skill dispatches `/ai-explore` and `/ai-research` in parallel to gather codebase evidence and external references. Each runs in its own fresh context.
3. The skill drafts the 14 canonical sections using the captured evidence. Every architectural claim cites at least one `file:line` location.
4. Output lands at `.ai-engineering/specs/drafts/<topic>-brief.md`. The operator reviews, edits, and hands off to `/ai-brainstorm` for spec promotion.

## Workflow

Principles applied: §10.6 SDD (every brief precedes a spec — the spec phase consumes the brief as the canonical problem statement); §10.5 TDD (structural test enforces the 14-section shape so brief drift is impossible without a visible test failure); §10.1 KISS (one file, one location, one handoff token — no parallel surfaces).

1. **Interview owner intent.** Ask up to three clarifying questions: (a) the problem statement in one sentence, (b) the audience (operator / framework dev / external user), (c) the rough scale (single-skill change / multi-wave refactor / cross-IDE rearch). Defaults are reasonable for ambiguous prompts.
2. **Dispatch parallel research.** Invoke `/ai-explore` (codebase evidence — read-only research) and `/ai-research` (external evidence — multi-tier citation) in parallel. Each runs in its own context window. Wait for both to complete before drafting.
3. **Compose the 14 sections.** Use the canonical template documented in Brief Shape. Cite at least 5 `file:line` evidence locations across the body. Use placeholder paths (`$HOME/...`) instead of machine-absolute `/Users/...` paths. No emoji per team convention.
4. **Write the brief.** Output path: `.ai-engineering/specs/drafts/<topic>-brief.md`. YAML frontmatter declares `title`, `status: draft`, `audience`, `branch`, `length_estimate`, `authoring_style`, `principles_required`, `delivery_mode`, `mantra`. Filename slug must be kebab-case.
5. **Emit handoff token.** Print the relative file path plus the command `/ai-brainstorm --consume <topic>-brief.md` so the operator can advance to the spec phase with a single invocation.
6. **Audit.** Emit `framework_event kind=brief_drafted`, `component: ai-spec-draft`, `detail: {topic, path, citations_count}`. The event chains into the standard audit pipeline.

## Brief Shape (14 canonical sections)

The brief contract is byte-equivalent across drafts so reviewers and downstream skills can rely on the structure.

1. **Vision** — one paragraph: where we are going and why.
2. **Scope Boundary** — what is in scope and what is explicitly NOT.
3. **Diagnostic Snapshot** — current-state evidence with `file:line` citations.
4. **Architecture** — the proposed structural change with module / surface boundaries.
5. **Evidence Catalog** — table of `file:line` citations supporting the diagnostic.
6. **Roadmap** — milestones with acceptance gates.
7. **Definition of Done** — measurable acceptance criteria.
8. **Quality Stamps** — principles applied (§10.x anchors) plus contracts honoured.
9. **Open Decisions** — pending choices that the spec phase must resolve.
10. **Migration** — backwards-compat strategy (hard rename per CONSTITUTION.md §3 — no shims).
11. **Risks** — likelihood × impact matrix with mitigations.
12. **References** — external sources (Anthropic skill-creator, RFCs, prior art).
13. **Glossary** — domain terms introduced by the brief.
14. **Acceptance** — checklist version of Definition of Done.

Existing drafts that follow this shape: `.ai-engineering/specs/drafts/skills-agents-excellence-v2-brief.md`, `cli-ux-overhaul-brief.md`, `dx-excellence-refactor-brief.md`.

## Citation Discipline

Every architectural claim, every "currently" / "today" / "the current state" sentence in §3 Diagnostic Snapshot must cite a `file:line` location. The minimum is at least 5 file:line citations across the body; briefs targeting cross-surface refactors usually carry 20+. Citations use the form `path/to/file.py:42` (no relative `../` prefixes). Machine-absolute paths (`/Users/...`) are rewritten to `$HOME/...` per team convention.

## Examples

### Example 1 — small skill addition

User: "draft a brief for adding a /ai-feedback skill that posts user feedback to a configured webhook"

```
/ai-spec-draft "ai-feedback-webhook"
```

Skill interviews intent (problem: collect operator feedback; audience: operator; scale: single-skill), dispatches `/ai-explore` (research existing notification skills) + `/ai-research` (Anthropic webhook patterns), drafts the 14-section brief with ≥5 citations, writes `.ai-engineering/specs/drafts/ai-feedback-webhook-brief.md`, prints the handoff token.

### Example 2 — multi-wave refactor

User: "we need a brief for moving the installer from uv-tool to a fully native bootstrap"

```
/ai-spec-draft "installer-native-bootstrap"
```

Same flow with broader research scope. The brief lands with 30+ citations spanning `src/ai_engineering/installer/`, related GitHub Actions workflows, and external Python packaging references.

## Quick Reference

| Goal | Command |
|------|---------|
| Draft a brief | `/ai-spec-draft "<topic>"` |
| Hand off to spec | `/ai-brainstorm --consume <topic>-brief.md` |
| Survey existing drafts | `ls .ai-engineering/specs/drafts/` |

## Common Mistakes

- Skipping the research dispatch — drafting from session context alone produces unciteable claims. Always run `/ai-explore` + `/ai-research`.
- Embedding emojis or machine paths — both fail later checks (team convention; `tools/skill_lint/checks/md_mirror.py` flags `/Users/` leaks).
- Dropping sections to save lines — the 14-section shape is the contract. Empty sections are allowed when honestly N/A.
- Confusing this skill with `/ai-brainstorm` — that one approves the spec and writes `spec.md` + decision rows. This skill produces the *brief* that feeds `/ai-brainstorm`.

## Integration

Called by: user directly. Dispatches: `/ai-explore` (codebase research, read-only) and `/ai-research` (external evidence) in parallel. Writes: `.ai-engineering/specs/drafts/<topic>-brief.md`. Audited: `framework_event kind=brief_drafted`. Pairs with: `/ai-brainstorm` (consumes the brief to produce an approved spec.md). See also: `/ai-plan` (consumes spec.md to produce patch-ready plan.md), `/ai-build` (consumes plan.md to execute).

$ARGUMENTS
