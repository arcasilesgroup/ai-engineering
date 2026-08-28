---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0028"
title: "Specification 045 and its plan are approved at exact digests"
date: "2026-08-28"
spec: "045"
status: "accepted"
authority_role: "repository owner"
approval_ref: "ae523990"
approved_at: "2026-08-28T02:36:47Z"
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
| `specs/045-critics-inside-spec/spec.md` | `b84af3f60fe8de05c15b44366247eb185fb1001cac4f87822ed931cd5a118ea9` |
| `specs/045-critics-inside-spec/plan.md` | `27ab8a15d235630e6f45fc41102844763d20d9fe85150b9230995dd3ebbf2421` |

Both digests are the bytes after three record-coherence reflows, none of which
changed a decision, a task or its command: the marked-decision lines moved onto
single lines (the wrapping made them unparseable by `ai-eng decide`; spec moved
from `7888877b…`), every `check` was reshaped to name exactly one command because
`--tick` executes the single command a box carries (plan moved from `fae01029…`),
and task 1's title closed its bold on the line the parser cannot read (plan moved
from `dd757776…`). The tick column is masked before the digest is taken, so the
seals themselves do not move these numbers. The approval names the bytes the
promotions and the ticks actually read.

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
