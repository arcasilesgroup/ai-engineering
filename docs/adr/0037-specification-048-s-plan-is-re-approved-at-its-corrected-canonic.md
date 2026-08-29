---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0037"
title: "Specification 048's plan is re-approved at its corrected canonical digest"
date: "2026-08-29"
spec: "048"
status: "accepted"
authority_role: "repository owner"
approval_ref: "54bdfa50"
approved_at: "2026-08-29T11:31:40Z"
supersedes: "0036"
---

# 0037. Specification 048's plan is re-approved at its corrected canonical digest

## Context and problem statement

ADR 0036 signed `specs/048-handshake-intake-mechanisms/plan.md` at `0faae1…` — the
raw SHA-256 of the file's bytes. That is not the number `--tick` verifies: a plan's
approval digest is canonical, taken over the file with the tick column masked, because
ticking a box moves bytes without changing what the plan says (`spec.py`'s
`approval_bytes`). The first tick attempt exposed the mismatch and the plan's own
defect at the same time: task 1's check named two commands and task 2's started with a
word outside `RUNNABLE`, and `_one_command` refuses to choose or to run what it cannot
run — a correct refusal, executed by the machine before this sentence needed writing.

The plan now at `1d2391…` is the same four tasks with each check narrowed to the one
command `--tick` executes, the removed assertions folded into the prose beside it (the
pytest selection already covers the fog ratchet and the digest pins; task 2's check is
the same one-shot guard rooted at `uv run python`). No task's file, rollback or
done-when moved; no scope moved. The specification's bytes are unchanged and its
digest stands as signed in 0036.

## Considered options

1. **Re-approve the plan at its corrected canonical digest.** Same task list, right
   number on the seal; the spec row is untouched.
2. **Rewrite 0036 in place.** Rejected: an approved record's bytes are signed, and
   032 already settled that a correction moves the digest and gets its own record.
3. **Leave the wrong number and tick without the digest.** Rejected: `--tick` executes
   a command out of a markdown file; the named digest is the only thing tying that
   execution to the thing a person approved.

## Decision outcome

Approved at these exact bytes:

| file | SHA-256 |
|---|---|
| `specs/048-handshake-intake-mechanisms/spec.md` | `9211b8f96b1c245a7a2b35d2f328b10673f5c973b95aefb0984f393334001b8c` |
| `specs/048-handshake-intake-mechanisms/plan.md` (canonical) | `1d239107445c95b0c7dd8a257a28a535817aaa5c1fe3b0c6d4dc794e03c8b3d2` |

The repository owner's `/ai-goal` invocation of 2026-08-29 remains the standing
approval behind this correction; 0036's account of the critics' rounds, the four-task
scope and the two promoted decisions is unchanged except for the plan's number. Each
task commit runs its named check in the same chain; nothing past task 4 is opened.

## Consequences

Execution of the four tasks opens against these bytes; each `--tick` re-verifies the
canonical digest before running its check, so a plan edit past this point stops at the
tick rather than at the reviewer. The corrected checks make the failure-before-fix
shape executable (task 2's guard reds today and greens with its commit), which is the
property the record was missing when it pinned the raw sha: a number nobody can tick
with is a signature nothing can present.
