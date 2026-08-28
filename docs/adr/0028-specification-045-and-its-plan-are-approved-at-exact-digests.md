---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0028"
title: "Specification 045 and its plan are approved at exact digests"
date: "2026-08-28"
spec: "045"
status: "proposed"
supersedes: ""
---

# 0028. Specification 045 and its plan are approved at exact digests

## Context and problem statement

`specs/045-critics-inside-spec/spec.md` decides that the governed cycle's critics live
inside the specification they attack. `ai-challenge` becomes a grill — at most ten
command-backed `### Q` entries per round, folded into `## Grill` by the author — and
`ai-council` runs once — five named lenses and the anonymous cross-read in one pass,
the verdict written into `## Council`. The four sidecar files (`challenge.md`,
`council.md`, `council.html`, `approval.md`) die for new specs; the approval record
returns to `docs/adr/`, the home this decision resumes after the gap since ADR 0026;
`just council` becomes a critic step that reads both counter shapes, refuses an empty
or prompt-carrying declared section and a malformed `ran:` line, and scopes the
no-authority rule to section bodies so written history is never rewritten.

This record is the first digest approval written as a `docs/adr/` MADR since ADR 0026:
specs 029–044 carried their approval in `specs/*/approval.md` dossiers, which
`madr.validate` parses and skips, so the approval series is restored here rather than
continued beside it. The fifteen historical dossiers stay where they are.

The draft was walked by the first half of the cycle under the shape it proposes. The
grill ran two rounds: round one was the owner's intake (five questions, in session);
round two was one forked challenger against the specification and the tree, seven
findings `WRONG` — among them the fail-closed chain the first draft claimed, the
direction of `madr.validate`'s behaviour, and the false claim that the approval
already lived in `docs/adr/`. The council ran once (five lenses + cross-read,
`RAN council=3/12` inside `## Council`) and added three gaps no single lens named, all
folded into the decisions in place. The plan is ordered by the council's first step:
the refusal fixtures and the scoped no-authority land before the template ships the
headings, so the first spec the new tool makes cannot pass a gate its own printed
rules do not enforce.

## Considered options

1. **Approve the specification and its plan at their exact bytes.** The same binding
   the earlier approval records carry, so a digest move refuses instead of sliding.
2. **Approve the direction and leave the plan open.** Rejected: an unbound plan is an
   unmeasured promise, and this record exists to make the promise checkable.
3. **Let the goal run approve its own bytes.** Rejected: the standing grant of an
   `/ai-goal` invocation authorises the work; it does not substitute for the record
   the gate reads. Authority is a dated artifact a validator opens, not a sentence in
   a transcript.

## Decision outcome

Approved at these exact bytes:

| file | SHA-256 |
|---|---|
| `specs/045-critics-inside-spec/spec.md` | `7888877b80c0fb86e765766cd85f3c7dc70d2e0cd30efd83881006d41687ba71` |
| `specs/045-critics-inside-spec/plan.md` | `fae0102931d474856da1eeb48942932262d59bc6bca2b4c58bf69b9864c423ef` |

The plan's nine tasks are the exact authorised work: the dual-glob critic reader with
its four refusal fixtures and one clean control, the scoped no-authority pass, the
template with `## Grill`/`## Council` and three numbered option prompts, the two
critic skills rewritten to the new contract with their pinned sentences kept, the
stale skill-map holes removed, the tools row and changelog naming every behaviour
change, one whole `just check`, and the promotion of D-045-03 and D-045-04 as MADRs.
Tasks 1-7 are one coupled family that reverts as a block; nothing past task 9 is
opened by this record, and each task commit runs its named check in the same chain.

## Consequences

A future reader who asks "did the critics actually run?" gets a checked answer from
one file: the `ran:` lines, the counts the step recomputes, and the sections whose
prompts refuse a declared round that never filled them. The cost the grill found
honest and this record approves anyway: the minutes are self-reported (visible, not
audited), the lens pass will read earlier critic rounds inside the document
(reopened if the 66.5% channel ever shows), and 114 references to the dying sidecars
migrate in one family. The approval home being empty since ADR 0026 was the run's
worst finding — this record is its repair, and the day the series stops again, the
next cycle's second half has no gate to run against.
