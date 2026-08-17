---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0011"
title: "Requirement-closure work is a block like any other"
date: "2026-08-16"
spec: "010"
status: "accepted"
authority_role: "repository owner"
approval_ref: "ae523990"
approved_at: "2026-08-17T01:27:45Z"
supersedes: ""
---

# 0011. Requirement-closure work is a block like any other

## Context and problem statement

The block cadence this project adopted governs implementation blocks: a boundary, one
independent reviewer for the closed block, one bounded repair pass, one gate run. It says
nothing about the work that comes after — continuous-integration repair, and closing
requirements an audit found open — and that work has now been the majority of two sessions.

Three audits recorded the same gap in the same words: `PO-01`, `PO-06` and `PO-13` did not
govern it. Roughly twenty commits went in with `just check` green on each and no block
boundary and no independent reviewer. Independent review did happen twice, both times outside
the protocol, and both times it found real defects: a verifier re-ran twenty-eight closures
and found five overclaims, and four auditors re-ran the unproven requirements and found three
contradictions. Later, a reviewer given five requirement-closure commits found two live
defects — a coverage control that was permanently red for any repository with a package in a
subdirectory, and a SARIF reader that took an exception out through the security gate instead
of a verdict. Neither was reachable by re-reading; both needed somebody else executing.

So this is not a rule nobody has tested. It is a rule the work kept inventing ad hoc, and
each time it was invented it paid for itself immediately.

## Considered options

1. **Leave it uncovered and rely on the gate.** `just check` runs on every commit, and each
   closure lands with its own fixtures. It costs nothing and it is what happened. What it
   misses is exactly what a gate cannot see: whether the thing built is the thing the
   requirement asked for. Five of eleven closures in one session were overclaims, every one
   of them green.

2. **Apply the implementation cadence unchanged.** A boundary and a reviewer per requirement.
   This is the review-after-every-Task shape the process research already rejected for
   implementation, and requirement closure has smaller units still, so it would cost more per
   unit of work than the shape it replaced.

3. **A boundary counted in requirements rather than in tasks.** Requirement closure is
   naturally batched: several requirements close against the same subsystem in one sitting.
   Close the block when a coherent group is done or when the accumulated diff crosses roughly
   five commits, whichever comes first, then one independent read-only reviewer over the
   accumulated diff, one repair pass, one gate run.

## Decision outcome

Option 3, with one addition the other two do not have: the reviewer is asked to compare what
was built against **what the requirement asked for**, in the requirement's own words, and not
only to review the diff. That is the check that caught all five overclaims and it is a
different question from "is this code correct".

A requirement-closure block therefore closes on whichever comes first — a coherent group of
requirements finished, or about five commits — and then:

1. the writer stops and the diff is frozen;
2. one independent read-only reviewer reads each commit against its parent and the
   accumulated range, and is given the requirement texts, not only the diff;
3. every finding lands in one ledger and the writer repairs them in a single pass;
4. `just check` runs once, twice only if the first run failed and code changed;
5. the block's own commit says what the reviewer found and what was repaired.

Anything the reviewer refuses is not closed. A closure the reviewer downgrades goes back to
the audit as INCOMPLETE with the reason, in the same commit — never quietly dropped.

## Consequences

Better: the defect class this project exists to cure — a control that reads stronger than it
is — is now checked by the one mechanism that has ever caught it here, on the work where it
happens most. The audit stops being the place overclaims are discovered months later.

Worse: it is slower, and it costs a second reader on work that already feels finished. The
first block run under this rule cost one reviewer and a repair pass over five commits that
were all green. Two of those repairs were live defects, so the price was paid back on the
first use; that will not be true every time, and this decision accepts blocks where it is not.

Also worse: `specs/010/plan.md` is approved by digest and this record does not amend it. It
cannot: amending an approved plan invalidates its approval, and no agent may re-approve a plan
under the authority this project grants it. Accepted on 2026-08-17 by the repository owner,
so the cadence governs from here — and it governs beside the plan rather than inside it,
which is a seam somebody should close the next time the plan is opened for another reason.
