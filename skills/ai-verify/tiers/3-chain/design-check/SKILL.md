---
name: design-check
description: Verify the implementation actually matches design.md — builds a requirement-by-requirement traceability table showing what is implemented, partial, missing, or contradicted, plus undocumented behavior the code added on its own. Use when asked to check code against the design/spec, confirm a feature was built as designed, find drift between design.md and the app, or answer "did we build what we said we would".
---

# Design conformance check

Verify the code against the design document. The deliverable is a **traceability
table**: every requirement in the spec mapped to the code that implements it, or
marked as missing. No requirement may be silently dropped.

Read `.claude/review/CONVENTIONS.md` first — stack detection, severity, the
false-positive gate, and the report format. The installed-version rule there
applies: never call an implementation wrong based on remembered framework
behavior.

## 1. Locate the spec

In order: a path given in the skill arguments → `design.md` at the repo root →
`docs/design.md`, `DESIGN.md`, `design/*.md`, `specs/*.md`, `docs/specs/*.md`,
`docs/rfcs/*.md`, an `adr/` directory, or a PRD directory the project documents
in its `README`/`CONTRIBUTING`. If the project has its own spec convention,
follow it over this list.

**If no design document exists, stop.** Do not invent requirements, and do not
substitute `README.md`, `CLAUDE.md`, or `AGENTS.md` — those describe setup and
agent rules, not intended behavior. Report:

> No design document found (looked at: `<paths>`). A conformance check needs a
> spec to check against. Point me at the file, or I can draft a `design.md` from
> the current implementation for you to correct — but note that a spec reverse-
> engineered from code cannot find design drift, since it would encode whatever
> the code already does.

Then stop and wait. Do not proceed to a general code review — that is `code-audit`.

## 2. Extract requirements

Read the spec end to end, then decompose it into **atomic, checkable
requirements**. Assign each a stable ID (`R1`, `R2`, …) and keep the spec's own
section names.

A good requirement is one you could write a test for. Split compound sentences:
"the list paginates at 20 items and persists sort order across reloads" is two
requirements, and they can have different verdicts.

Capture all three kinds, and label which each is:
- **Behavioral** — what the app does (routes, states, flows, validation, errors)
- **Structural** — architecture, file layout, data shapes, module boundaries
- **Visual/UX** — layout, copy, spacing, responsive breakpoints, states

Also record explicit **non-goals** and **constraints** ("must not call the API on
keystroke", "no client-side secrets"). These are the requirements most often
violated, because nothing in the code points at them.

If a requirement is too vague to verify ("the UI should feel fast"), record it as
`AMBIGUOUS` with the reason rather than guessing at a threshold. Ambiguity in the
spec is a real finding about the spec.

## 3. Trace each requirement to code

For every requirement, find the implementing code and read it. Grep locates
candidates; only reading decides the verdict.

| Verdict | Meaning |
|---|---|
| `IMPLEMENTED` | Code does what the requirement says. Cite `file:line`. |
| `PARTIAL` | Main path works, some clause of the requirement is unmet. Say precisely which clause. |
| `MISSING` | No implementing code found anywhere. |
| `CONTRADICTS` | Code does something the spec explicitly rules out, or the opposite of what it says. |
| `UNVERIFIABLE` | Cannot be decided by reading code — needs the app running, a visual check, or data you do not have. |

Rules that keep this honest:

- **`IMPLEMENTED` requires a `file:line` citation you have read.** A requirement
  you could not locate is `MISSING`, never "probably fine".
- **The existence of a file is not implementation.** A component named
  `<PaymentForm>` does not satisfy "the payment form validates card expiry" — find
  the validation.
- **`UNVERIFIABLE` is a legitimate verdict and must not be used to dodge work.**
  Use it for genuinely runtime/visual properties, after you have read the code.
  Every `UNVERIFIABLE` needs a one-line note on how someone could check it.
- Prefer `CONTRADICTS` over `PARTIAL` when the code makes an opposite decision —
  those are the findings that matter most, because someone chose differently and
  the spec was never updated.

## 4. Check the reverse direction

Conformance runs both ways. Scan first-party source for behavior the spec does
not sanction:

- **Undocumented features** — routes, states, or flows with no requirement behind
  them. Not automatically wrong, but they are unreviewed surface area.
- **Non-goal violations** — the code does something the spec said not to.
- **Contradicted constraints** — architecture, data shape, or dependency choices
  that diverge from what the design specified.

Report these as `UNDOCUMENTED` rows. When the code is clearly the better decision
and the spec is stale, say so — the fix may be to update `design.md`, and
recommending that is part of the job.

## 5. Report

Use the output contract in `CONVENTIONS.md`, with the traceability table inserted
before `## Findings`:

```markdown
## Traceability

| ID | Requirement | Kind | Verdict | Evidence |
|----|-------------|------|---------|----------|
| R1 | Sort order persists across reloads | Behavioral | IMPLEMENTED | `src/views/list.ts:88` |
| R2 | List paginates at 20 items | Behavioral | PARTIAL | `src/views/list.ts:41` — paginates at 50 |
| R3 | No client-side secrets | Constraint | CONTRADICTS | `src/lib/api.ts:12` |
| R4 | Empty state illustration | Visual | UNVERIFIABLE | needs running app |
| U1 | Debug panel at `/debug` | Undocumented | — | `src/routes/debug.ts` |

**Conformance: 11/14 requirements met** (1 partial, 1 missing, 1 contradicted,
2 unverifiable, 1 undocumented addition)
```

Then write a finding for every non-`IMPLEMENTED` row, severity by user-facing
impact — a contradicted constraint outranks a missing nice-to-have, regardless of
how the spec ordered them. Verdict per `CONVENTIONS.md`: any `MISSING` or
`CONTRADICTS` on a core requirement makes the overall verdict `FAIL`.

Close with a short **Spec health** note: requirements that were ambiguous, stale,
or that the implementation has clearly outgrown. Drift is often the document's
fault, and that is worth telling the user plainly.

## Relationship to `a11y-audit`

These two overlap on visual/UX requirements but answer different questions, and
they measure against different sources of truth: this skill checks the code
against **your document**, `a11y-audit` checks it against **WCAG**, an external
standard.

The consequence is that they can reach opposite verdicts on the same line — a
spec that mandates a light gray on white is *conformant* here and *failing*
there. That is a real and useful result, so do not resolve it yourself:

- Judging accessibility is not your job. Do not mark a requirement `CONTRADICTS`
  because you think the design is inaccessible, and do not pass an implementation
  because it matched a spec you suspect is wrong.
- When a requirement you are verifying appears to mandate something inaccessible,
  record the conformance verdict normally, then add one line under **Spec
  health**: `R7 conforms but the design itself may fail WCAG — a11y-audit owns
  this`. Do not investigate further.

`full-review` surfaces that pair as a conflict, which is the point: it means the
design needs changing, not the code.
