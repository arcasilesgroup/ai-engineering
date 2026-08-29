---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0034"
title: "Specification 047's plan is re-approved at its corrected digest"
date: "2026-08-29"
spec: "047"
status: "accepted"
authority_role: "repository owner"
approval_ref: "bc08b778"
approved_at: "2026-08-29T01:20:50Z"
supersedes: "0033"
---

# 0034. Specification 047's plan is re-approved at its corrected digest

## Context and problem statement

`0033` approved specification 047 and its plan at exact bytes on 2026-08-29. Task 5's
`--tick` then refused: the envelope requires `file`/`check`/`rollback`/`done when` per
task, and the plan's tasks 4 and 7 named two files under `**files**:`, a plural key the
parser does not know — so the verb that executes an approved plan could not tick its own
tasks. The house format is singular `**file**` with the list inside; 045 and 046 carry it
that way 23 times. The correction is mechanical (`**files**:` → `**file**:`, eight tasks
untouched otherwise) and it moves the canonical plan digest. The precedent is `0032` and
before it `0023`: correct the bytes, move the digest, re-approve — never annotate around
a signature.

## Considered options

1. **Re-approve the corrected plan bytes at the new digest.** The 0032 shape: the record
   names the bytes execution actually runs against.
2. **Accept the pair in the drift reader's known set without a new record.** Rejected:
   the known set names a moved row so the old record reads honestly; it is not a
   substitute for the approval the executor verifies against.
3. **Leave the plan and tick by hand.** Rejected: a hand-written seal is exactly the
   false-green this machinery exists to refuse.

## Decision outcome

The specification is unchanged and stays approved at its `0033` digest. The plan is
re-approved at these exact bytes (canonical — the tick column masked):

| file | SHA-256 |
|---|---|
| `specs/047-autonomous-cycle-wall-budget/plan.md` | `ded6972988dbabfe1af90d5b18d14bbaa5ce1b9e69edc6d3117671c441beae9d` |

`0033`'s plan row (`e4252e37…`) is superseded by this record; its spec row
(`1ec7e171…`) still names the bytes on disk.

## Consequences

`--tick` reads the same bytes this record signed, and every later seal verifies against
them. The cost: one more digest in the chain, which is what an honest signature history
looks like — the alternative was a plan whose approval and whose parser disagree.
