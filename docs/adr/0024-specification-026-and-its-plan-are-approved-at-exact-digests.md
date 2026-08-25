---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0024"
title: "Specification 026 and its plan are approved at exact digests"
date: "2026-08-25"
spec: "026"
status: "accepted"
authority_role: "repository owner"
approval_ref: "ae523990"
---

# 0024. Specification 026 and its plan are approved at exact digests

## Context and problem statement

`specs/026-sm-skillmap-as-instrument/spec.md` decides to adopt `sm` (skill-map.ai) as the
reference-integrity instrument of the governed tree: a `just map` recipe backed by
`sm scan && sm check --json`, the `NNN-slug` template hole carried as an exclusion list
rather than a suppression, and the real broken references recorded (accepted or fixed) so
the gate's green is honest. Its plan turns that into five sequential, atomic tasks.

The draft was walked by the first half of the cycle. The challenge executed its claims and
found the numbers move (40/13/53 drafted vs 47/15/62 live) and that the 0-gate promise was
unreachable while the real references stood unaccepted; the council (5 lenses + cross-read,
`RAN council=14/5`) confirmed and added the version-pin gap and the `.venv` phantom-tree gap.
The plan is ordered to make those real before the recipe promises an honest 0: pin `sm` and
define `map` first, exclude `.venv` second, accept the real defects third, carry the
template exclusion fourth, and wire the whole into `just check` fifth.

## Decision outcome

Approved at these exact bytes:

| file | SHA-256 |
|---|---|
| `specs/026-sm-skillmap-as-instrument/spec.md` | `0ce52d25d266db4a2738f6c64e34ea3a06f62ea50a08b49c27f10dd8f45e8684` |
| `specs/026-sm-skillmap-as-instrument/plan.md` | `6b4a0cfc963d6de9975331ae3ed8f051108e88b3fd382a14f18c468ac591d202` |

The recommendation stands: `sm` is the reference-integrity instrument. The plan's five tasks
are authorized as the exact work this record approves; nothing past task 5 is opened, and
each task commit runs the gate in the same chain as the commit.

Everything `0016` recorded about authority still holds and is not restated by reference. This
is the owner's approval of the spec and its plan, not a standing autonomous grant and not an
acceptance of the 47 real broken references — those are a separate dated record task 3
materialises, and task 4's gate green depends on them being accepted or fixed, not silently
hidden.

## Consequences

The instrument's first honest finding is that the tree held real broken references (47 live
at plan time). This approval does not repair them: it authorises a sequencing where they are
accepted with a dated record inside the block, so a reader who asks "did the tree get clean?"
can see the acceptance, and a reader who finds a reference that is neither fixed nor accepted
sees a red gate. The risk that a record of acceptance is read as a clean bill is the risk of
this block, and the plan's task 5 is written to refuse that reading: a reference that is
neither fixed nor accepted reddens `just check`.