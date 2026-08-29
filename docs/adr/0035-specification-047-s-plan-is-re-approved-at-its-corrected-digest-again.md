---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0035"
title: "Specification 047's plan is re-approved at its corrected digest again"
date: "2026-08-29"
spec: "047"
status: "accepted"
authority_role: "repository owner"
approval_ref: "bc08b778"
approved_at: "2026-08-29T01:35:47Z"
supersedes: "0034"
---

# 0035. Specification 047's plan is re-approved at its corrected digest again

## Context and problem statement

`0034` re-approved specification 047's plan at the digest its field-name correction
moved it to. Task 4's `--tick` then refused for the third and last mechanical defect in
the approved bytes: its check was written as a shell substitution —
`--session $(tail -n1 .ai/events.jsonl | …)` — and `_tick` runs argv with no shell by
design, so the command exits 2 before the verb is even reached; and the file it reads,
`.ai/events.jsonl`, is gitignored, so CI has none and the check could not go green
there. The correction is the same shape the tree always uses for a check that must run
unattended: one pytest command over a tmp root (the hermetic test
`test_the_verb_reads_the_in_clone_record`), and the done-when loses the word "live".
The spec is unchanged; the plan digest moves again, and this record re-approves.

## Considered options

1. **Correct the check and re-approve at the new digest.** The 0032/0034 shape; the
   record names the bytes execution verifies against.
2. **Tick by hand with a shell.** Rejected: a hand-written seal is the false-green the
   machinery exists to refuse, and rule 3 forbids the bypass.
3. **Keep the substitution and run it through a shell in --tick.** Rejected: the no-shell
   execution is the control that bounds what a markdown file can make the verb run.

## Decision outcome

The specification stays approved at `0033`'s digest. The plan is re-approved at these
exact bytes (canonical — the tick column masked):

| file | SHA-256 |
|---|---|
| `specs/047-autonomous-cycle-wall-budget/plan.md` | `55d045b04f347c8c9f20dad88d5a491379a0267e1b0d426309d226655c30f266` |

`0034`'s plan row (`ded69729…`) is superseded by this record.

## Consequences

Three corrections in one afternoon, each with its record, is the cost of signing bytes
nobody executed yet — and the cheaper alternative was the silent edit, which is the
defect this repository was rebuilt to end. From here the plan's remaining checks are
all single commands the tick machinery can run.
