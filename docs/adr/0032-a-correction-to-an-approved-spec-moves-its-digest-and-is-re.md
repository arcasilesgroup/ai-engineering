---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0032"
title: "A correction to an approved spec moves its digest and is re-signed."
date: "2026-08-28"
spec: "046"
status: "proposed"
supersedes: "0031"
---

# 0032. A correction to an approved spec moves its digest and is re-signed.

## Context and problem statement

`0031` approved specification 046 and its plan at exact bytes on 2026-08-28, and the map
(`just map`, spec 026) found three real broken references in the bytes that approval
covered: `policy/visual-pages.md` cited bare `spec.md` and `plan.md`, and the approved
specification cited `specs/NNN/plan.md` — a template hole spelled without its `-slug`, so
the analyzer could not read it as one. All three are prose pointers that were never meant
as file links, and the reference-integrity gate refuses the tree while they stand.

Two ways out existed. The map's dated accepted set (`policy/skill-map-accepted.toml`, the
ADR 0025 mechanism) could carry the three node+target pairs and the bytes would not move —
which keeps a false statement in the record, written to protect a signature. Or the
references are corrected in the documents themselves, the spec digest moves, and this
record re-approves the corrected bytes. `docs/adr/0023` is the precedent: a specification
whose approved bytes were found wrong was corrected and re-signed at its new digests,
superseding the old approval rather than annotating around it.

## Considered options

1. **Accept the three pairs in the map's dated set.** No signature moves, and the
   specification keeps a typo (`specs/NNN/plan.md`) and `policy/visual-pages.md` keeps two
   citations that resolve to nothing, now blessed by an acceptance record until
   2026-09-30. Refused: the accepted set exists for prose that is true and unresolvable by
   the analyzer, not for bytes that are wrong.

2. **Edit the approved bytes and let the digest slide.** Refused without argument: an
   unbound digest move is the exact failure every approval in this repository exists to
   catch.

3. **Correct the references and re-approve at the corrected digests.** What this record
   does. The correction is two sentences and one `-slug`; the re-approval is the honest
   artifact for a digest that moved.

## Decision outcome

Option 3. Re-approved at these exact bytes, superseding `0031`:

| file | SHA-256 |
|---|---|
| `specs/046-visual-html-records/spec.md` | `e9fb5a119f704ccd838f2985d1f873e4da0a9b7b52f783592288dcfac9bf3200` |
| `specs/046-visual-html-records/plan.md` | `5bbaa617c857ff1cfae5af21fab5d69e56b56a4ef6678d33e418f2446a0d7848` |

The plan digest is unchanged from `0031` — the canonical value, tick column masked, exactly
as that record printed it. What changed in the specification's bytes from what `0031`
approved, so a reader does not have to diff to find out:

- One citation corrected: `specs/NNN/plan.md` became `specs/NNN-slug/plan.md`, the spelling
  the map's template-hole convention (`policy/skill-map-exclusions.toml`) recognises.
- Decision `D-046-05` added: a correction to an approved spec moves its digest and is
  re-signed, never accepted around. The plan's tasks and checks are untouched.

`policy/visual-pages.md` is not part of this approval: it is a task-9 artifact of the plan,
committed under it, and its two bare citations were corrected in the same pass.

## Consequences

Better: the map is green from the documents being true rather than from an acceptance
carrying their errors; `just check`'s `map` recipe stops red-lining a spec whose only
defect was a typo; and the rule that a moved digest gets re-signed is now itself a marked
decision in the specification it came from.

Worse: `0031` is superseded twenty-four hours after it was signed, and any later text that
cites the `b7e60a1a…` digest is citing bytes this record replaces. That is the cost this
repository chooses on purpose: the alternative is a record that is quietly wrong and
formally right.
