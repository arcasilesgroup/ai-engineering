# Client-Value Lens: stakeholder-legible communication (spec-186 D-186-06)

## Purpose

The chain skills (`/ai-brainstorm`, `/ai-plan`, `/ai-build`, `/ai-autopilot`,
`/ai-pr`) produce excellent machine artifacts, but every human-facing moment is
authored for an engineer. A non-technical sponsor — product owner, client, or an
autonomous agentic company acting as one — must answer three questions without
decoding the mechanism: **what changed, why it matters, and what it risks or
unlocks.**

The lens renders every user-facing report *and every question a skill asks* as a
concise, non-technical, agile-framed value statement — answer first, detail on
request, jargon on a leash — never at the cost of a precise gate, commit, or
security warning.

It is orthogonal to the caveman (terse) and ponytail (minimal) plugins: the lens
governs *how you frame value*. Unlike those host-level plugins it ships with the
framework, so an autonomous consumer gets the value signal with nothing extra
installed.

## The value block (canonical form)

A fixed-field, BLUF-ordered form — not free prose. Answer first (Field 1),
support (Fields 2-5), evidence (Field 6): an exec reads Field 1 and stops, a PO
reads 1-5, an engineer expands Field 6. Each field is length-capped.

| # | Field | Holds | Cap |
|---|-------|-------|-----|
| 1 | **Bottom line** | What changed + the value, `so that <sponsor outcome>` | 1 line |
| 2 | **Why it matters** | Impact in plain terms (important / positive / negative) — significance, not mechanism | 1-2 sentences |
| 3 | **What's done / now possible** | Acceptance criteria as user-facing outcomes; the shippable increment | 2-3 bullets |
| 4 | **Risk / watch-outs** | Named risk, its impact if it lands, the mitigation. Say `None` explicitly if none | 1-2 lines |
| 5 | **Next / decision needed** | The next step, or the exact decision required (what, by whom, by when) | 1 line |
| 6 | **Details** (optional) | Collapsed pointer layer: spec / PR / commit / `file:line` references | link only |

## Audience ladder

Audience depth (from caveman's intensity levels). Selected via
`AIENG_VALUE_LENS_LEVEL` env, then `manifest.value_lens.default_level`, then the
built-in default `full`.

- **lite** — engineer: Field 1 + Field 6 inline; technical terms kept.
- **full** (default) — PO / stakeholder: all of Fields 1-5; jargon translated or
  defined inline on first use.
- **ultra** — exec / autonomous sponsor: Field 1 + Field 4 only; zero jargon;
  one business outcome and its single risk.

## Applies to questions, not only reports

The lens governs every point where a skill addresses the human — interrogation
questions, approach proposals, approval asks — as well as end-of-phase report
blocks. A value block is worthless if the sponsor could not understand the
question that shaped it, so questions carry plain-language framing and per-option
trade-offs (impact, effort, risk).

Cadence: every user-facing interaction point (question or report), NOT internal
working turns (tool calls, intermediate reasoning, routine acknowledgements).

## Carve-outs (load-bearing)

The lens applies to the *summary for the sponsor*, **never** to the exact output
it summarizes. These stay precise and normal — write them exactly as with no
lens active:

- source code
- commit messages
- unified-diff patch hunks
- security warnings
- acceptance-criteria *test conditions* (the machine-checkable assertions)
- gate verdicts (pass/block and the reason)
- irreversible-action confirmations

Value framing that softened a security warning or blurred a gate verdict is a
governance regression. The block *summarizes* exact output; it never replaces or
softens it.

When caveman is also active, the value block is a carve-out from caveman
compression: it renders in full (fragment-compression would destroy the sponsor
framing) while surrounding chatter may stay terse.

## Anti-verbosity guardrails

- Enforce the per-field caps; one idea per field.
- Apply the two-question filter to every line: does the reader need this, and are
  you sure they do not already know it? If either answer is no, cut the line.
- Define unavoidable jargon inline on first use; otherwise translate it.
- Detail is opt-in behind Field 6, never inlined — keep the block to one screen.
- Prefer positive framing ("report changes as outcomes") over negative
  ("do not be technical").

## Adoption contract

A chain skill adopts the lens by citing this document
(`reference/value-lens.md`) at its user-facing report step and, where it asks the
human anything, at its question step. Enforced by a blocking `skill_lint` check
(`tools/skill_lint/checks/value_block.py`) that fails if any of the five chain
skills omits the citation. See `spec-186` decisions D-186-01 through D-186-10.
