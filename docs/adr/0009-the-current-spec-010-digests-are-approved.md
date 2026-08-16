---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0009"
title: "The current spec 010 digests are approved"
date: "2026-08-16"
spec: "010"
status: "proposed"
supersedes: ""
---

# 0009. The current spec 010 digests are approved

## Context and problem statement

The cadence in `.ai/reports/process-optimization-research/index.html` has a five-step
activation sequence. Three steps were done: Task 17 preserved, the plan rewritten to define
blocks, `UNREVIEWED` checkpoints and minimum per-commit controls, and the hashes recomputed.
Step four is a human approving those exact hashes, and step five says the cadence starts
only after it.

Nothing had. The plan recorded a specification approved at `6afc0721…` and a plan digest
invalidated with no successor, and the specification's bytes had since changed — `status`
went back to `draft` under the audit of 2026-08-15, because the final candidate never proved
its exact-HEAD receipts. So the work was running under a cadence whose activation had never
completed, and the record said so without anybody being able to act on it.

An approval also cannot be written inside the file it approves. The digest of `plan.md` is a
fact about its bytes, and a paragraph in `plan.md` naming that digest changes it by existing.
The number in the file would never be the number anybody agreed to.

## Considered options

1. **Record the approval inside the plan.** One file, one place to look. It cannot be
   correct: the plan's digest changes when the approval is added, so the approved value is
   stale the moment it is written, and the next reader cannot tell whether the mismatch is
   an unapproved edit or the approval itself.
2. **Record it here, as a decision that names the bytes.** The plan points at this file and
   this file names both digests. The plan's digest settles before this record is written,
   so the value here is the value on disk, and `tests/test_record.py` reads both.

## Decision outcome

Option 2. The repository owner approved both digests on 2026-08-16, in this session, in
answer to a question that named exactly what was being approved and offered approving only
the specification or neither. The reply was "Apruebo ambos digests".

| file | SHA-256 |
|---|---|
| `specs/010-governed-agentic-engineering-foundation/spec.md` | `364d83c56c7d9e7b4e2aeb975c9ada5c7b0db6822d79eb939e9010b9417e75db` |
| `specs/010-governed-agentic-engineering-foundation/plan.md` | `7bc96b09ed43eb52f0f74601c2504ffed86cd9ffb808aaf219be75871a76a88d` |

`tests/test_record.py::test_the_approval_digests_in_the_plan_are_read_by_something` reads
this table against the files. An edit to either without a new approval turns the build red
naming the file, which is what makes this record a gate rather than a sentence.

Approving these bytes approves the plan and the specification as they stand. It does not
grant the controlling-terminal handoff, which the plan requires as a separate named
statement, and no such statement was made. It does not tick a production-ready box, and it
does not move `specs/010` out of `draft`: the plan reserves that transition until a
candidate proves its own exact-HEAD CI receipts, and none exists.

## Consequences

The cadence's activation sequence is complete, so the block cadence is authorised rather
than merely practised. The one-primary-home rule gains the exception the owner chose in the
same answer: a commit may move the counts and line ceilings another check forces it to move,
and nothing else — recorded in the plan beside the rule it amends.

The specification stays `draft`. Approval is a fact about a person and a moment; it is not a
state of the work, and this record carries the authority, the date and the bytes that a
status word cannot.
