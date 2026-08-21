---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0022"
title: "Specifications 016 and 018 are re-approved at exact digests"
date: "2026-08-21"
spec: "023"
status: "accepted"
authority_role: "repository owner"
approval_ref: "spec-023-2026-08-21"
approved_at: "2026-08-21T12:00:00Z"
supersedes: ""
---

# 0022. Specifications 016 and 018 are re-approved at exact digests

## Context and problem statement

`docs/adr/0013` approved four files on 2026-08-17. Two of them no longer hash to what it
says. An approval is a signature on bytes, and when the bytes move the signature stays put
and stops covering anything — a signature on a blank page.

Nothing noticed for four days. The reader that existed read one record, `0009`, so a drift
in `0013` was invisible: a control that covers one instance of a class reads exactly like
one that covers the class. Record `0015` found both by hand while measuring something else
and wrote one of them down as a finding it could not act on.

Neither could be repaired by an agent. Repairing them means either re-signing somebody
else's approval or rewriting the files it approved, and the first is the one act that would
make the whole chain decorative.

## Considered options

1. **Restore the signed bytes.** The signature would cover the files again with nothing new
   to sign. It also undoes both changes, and both changes are repairs — this would put a
   wrong filename back into `016` and re-assert "not done" about work that was done.
2. **Leave the drift waived in the test.** It keeps the gate green and it is the shape of
   green nobody earned, which is the failure this product exists to name.
3. **Re-approve at the bytes that are there.** The owner reads what changed and signs it.

## Decision outcome

Option 3. What moved, exactly:

`specs/016-the-thesis-nobody-owns/spec.md` changed by one line. A reference to
`docs/audit-2026-08-15.md` was corrected to `docs/audit-2026-08-16.md`, which is the file
that exists. Restoring the signed bytes would restore a reference to a file that does not.

`specs/018-controls-a-reviewer-proved-were-not-controls/plan.md` changed in task T-11, which
went from unticked to ticked with the result that closed it: the scheduled run finished
uncancelled and published 21,960 mutants at 72% against a floor of 89. The tick itself is
not what moved the digest — `spec.approval_bytes` masks the tick column for a plan precisely
so that ticking never voids a signature — the prose recording the run is.

The owner approved these bytes on 2026-08-21, by approving `specs/023`, which names both
files and both digests in its own decision D-023-01:

| file | SHA-256 |
|---|---|
| `specs/016-the-thesis-nobody-owns/spec.md` | `c91dbc80d5026aa6f4802d683dab12a2f18c2677fab932a30c8f05b5e01df0bb` |
| `specs/018-controls-a-reviewer-proved-were-not-controls/plan.md` | `104d506522edaaafd6795030661f6717e9b18c2bfb22ebb6ff42e8ee4c753323` |

`docs/adr/0013` is not edited. Its rows are what was true on 2026-08-17 and rewriting them
would destroy the only evidence that the drift happened. A later approval supersedes an
earlier one; it does not erase it.

One thing recorded here that the prose of `018` no longer supports: T-11 describes
`just mutate`, a floor of 89 and run 32043131651, and all three were deleted on 2026-08-20
by `specs/021`. The note is now a true account of what happened inside machinery that is
gone. That is history rather than drift, and it is a further reason restoring the earlier
bytes would have been worse — the earlier bytes describe the same vanished apparatus and
additionally claim the work was not done.

## Consequences

The waived pair in `tests/test_record.py` goes away, and with it the last place where the
gate was green because somebody had written down that it was allowed to be.

The reader has to change with this, and the change is the general form of the same bug: rows
must be keyed by file with the newest record winning, or `0013`'s superseded rows keep this
red forever and the tree gains a second waiver to hide the first.

What stays unsolved is the count. A reader answering "is this approved" now consults five
records and nothing enumerates them. `0015` named that and it is still true; this adds one
more record to the pile it complained about. The mechanical reader is what makes the pile
safe, not tidy.
