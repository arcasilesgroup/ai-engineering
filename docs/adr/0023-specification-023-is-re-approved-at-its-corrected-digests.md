---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0023"
title: "Specification 023 is re-approved at its corrected digests"
date: "2026-08-22"
spec: "023"
status: "proposed"
supersedes: "0021"
---

# 0023. Specification 023 is re-approved at its corrected digests

## Context and problem statement

`0021` approved specification 023 and its plan at exact bytes on 2026-08-21, and those bytes
are no longer the right ones for two separate reasons.

**The first is a defect this work found in itself.** Three critics read the branch and an
adversarial pass tried to refute each blocking finding by executing it. Five survived, and
three of those are executable claims inside the approved specification that are false against
the tree it ships in. One — `just skilleval` printing `RAN skilleval=326` — was true when it
was signed, and task 5 of this specification's own plan made it false by moving the baseline to
332. One describes a regular expression that task 4 changed. One was never true at all: it
claimed a `grep` answered `src/ai_engineering/readiness.py:212`, `tests/pilot_register.py:95`
and `tests/stats.py:226`, and the pattern it names does not match any of the three. All three
are corrected, each now naming the tree its Then is about.

That is the defect class `docs/adr/0014` exists for — a claim about another document needs a
comparator, and a comparator is executing the sentence rather than re-reading it. This
specification cites that record and then broke its rule twice: once in the draft, where the
challenge stage caught it, and once here, where a review did.

**The second is a hole the first five tasks do not close, and the owner named it.** Forty-nine
findings were written for this specification — ten from the challenge, twenty-eight from the
lenses, eleven from the cross-read — and nothing in this repository is obliged to read one.
`challenge.md` has no reader at all; the two things that read `council.md` count its bullets and
refuse its verdict fields, and neither opens a finding. The nineteen corrections that went into
the draft arrived because a person made them by hand. That is behaviour living in a session
transcript and in no file, which is the failure this product exists to expose.

## Considered options

1. **Correct the examples and leave the loop open.** One signature instead of two, and it
   leaves a council whose findings nobody has to answer — which makes the whole of this
   specification optional in practice. Refused.

2. **Correct the examples here, and open a specification 024 for the loop.** Cleaner in that
   what was signed on 2026-08-21 is delivered without growing. Refused by the owner on
   2026-08-22, and the arithmetic is on his side: the digests move for the corrections anyway,
   so the second signature buys separation and costs a second cycle and a second pull request.

3. **Fold both into 023 and re-sign it once.** What this record does.

## Decision outcome

Option 3. Re-approved at these bytes, superseding `0021`:

| file | SHA-256 |
|---|---|
| `specs/023-council-that-reads-itself/spec.md` | `90b7c9f646c473019fd94aedfcfaa6cf0268e0f8dbaf479538cd5c96bfb52663` |
| `specs/023-council-that-reads-itself/plan.md` | `43bfa3a2296470c4fd114e05fb380075992cbd6369b3c7dc6280613045cfaa0c` |

What changed from the bytes `0021` approved, so a reader does not have to diff to find out:

- Three examples corrected, each now naming the tree its Then is about, and each verified by
  running it: `git show main:policy/pilot-register.toml` reads `measured = 326`; the regular
  expression taken from `git show main:tests/test_contracts.py` reads
  `[False, False, False, True, True]`; the `git grep` over `main` answers ten lines in five
  files and the same command over `HEAD` answers nothing and exits 1.
- Two decisions added. `D-023-09`: every finding carries an identity derived from its position
  and the author answers each one in the same file, `taken:` with the section that changed or
  `refused:` with a reason. `D-023-10`: if any answer reads `taken:`, the specification's digest
  must have moved — a comparator, because `taken:` is a claim about another document.
- Two tasks added to the plan, 6 and 7, which are the above as work.

The five tasks `0021` authorised are delivered and are not re-opened by this. What this
authorises beyond them is exactly tasks 6 and 7.

Everything `0021` recorded about authority still holds and is not restated by reference: the
owner read the brief and approved in his own words, this is not the standing autonomous grant
in `0016`, and the two decisions that were his rather than the author's — that the chairman may
conclude and that `contract.CEILING` is deleted — are unchanged.

## Consequences

The good one, and it is the only evidence in this repository that any of this was worth doing:
the stage that found the hole is the stage this specification is about. A review executed a
claim the author had re-read, and an owner reading the result asked the question the plan did
not answer. Neither the gate nor the author found either. That is not proof that a council
improves a specification — `EP-195` stays open and `0022` says so — but it is the first time a
critic in this repository produced something that changed the work rather than a file nobody
opened.

The one that gets worse. `0021` is superseded eighteen hours after it was accepted, and it is
the fifth record in three days to reopen something an earlier record closed — `0018`, `0019`,
`0021`, `0022` and this. `0019` wrote that two is not a pattern and three would be. Five is not
a pattern either; it is a rate. Nothing in this repository counts it, a human reading the pull
request is the only control on it, and this paragraph is the second place the count has had to
be written by hand. If a sixth is written before this specification ships, the thing to fix is
not the sixth record.

A smaller one, stated because a reader will otherwise assume it: re-signing does not re-run the
five delivered tasks against the new digests. Their commits carry the gate output they were
green under, and `ai-eng spec show 023 --task <n>` will from now on verify against these bytes
and not the ones those commits were written against. That is the honest cost of folding rather
than separating, and it is the reason option 2 was a real option.
