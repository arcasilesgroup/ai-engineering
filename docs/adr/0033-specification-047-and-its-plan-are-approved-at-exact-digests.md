---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0033"
title: "Specification 047 and its plan are approved at exact digests"
date: "2026-08-29"
spec: "047"
status: "accepted"
authority_role: "repository owner"
approval_ref: "bc08b778"
approved_at: "2026-08-29T01:10:18Z"
supersedes: ""
---

# 0033. Specification 047 and its plan are approved at exact digests

## Context and problem statement

`specs/047-autonomous-cycle-wall-budget/spec.md` decides that the cycle's wall budget is
data, not prose and not a killer: three named constants in `contract.py` (180 minutes per
giant block — the owner's decision of 2026-08-29 carried by PO-27 in the ledger —, 40
minutes and 120 calls per critic, both derived and labelled derived), a stdlib reader of
`.ai/events.jsonl` that attributes minutes between `ts` stamps to the earlier event's
`cls`, the `ai-eng report vitals` verb whose verdict disqualifies and never approves, the
five critic skills carrying their box and a `TIMEBOXED` exit, `just check-all` batching
the gate so k defects cost one pass, and the goal's anti-stall rule closing an unattended
turn with one `BLOCKED:` line instead of a hung fork. The clock disqualifies a run and
never approves one; PO-26 stays true and its grep is the proof.

The draft was walked by the first half under the shape spec 045 consolidated. The grill
ran one round of five questions, four real defects found in the author's own text and
folded in place: `stamp` named for wall arithmetic when it is the chain-seal hash and
`ts` is the time; `CRITIC_CALLS_MAX = 120` cited to a per-critic measurement the
postmortem does not carry (it measures 409 calls for the whole session), restated as
derived; a stale event-line count; and the examples' phase buckets belonging to the host
transcript that D-047-03 refuses, rewritten onto the `cls` buckets the framework owns.
The council ran once (five lenses + cross-read); its CLAIMED-NOT-REAL sweep over the
eight open tasks was refuted by the cross-read — a draft whose boxes all read `[ ]` is
not a lie — and the two counts `just council` recomputes are 0 and 4. A ninth defect was
found after both rounds, before the signature: task 2's check asked a red fixture to
exit zero, which `--tick` can never seal; the check is now `--collect-only` and the
done-when says which half is red on purpose.

## Considered options

1. **Approve the specification and its plan at their exact bytes.** The same binding every
   digest approval carries, so a digest move refuses instead of sliding.
2. **Approve the direction and leave the plan open.** Rejected: an unbound plan is an
   unmeasured promise — the exact shape the 024 fidelity audit found in specs 035-040.
3. **Let the build approve its own bytes.** Rejected: authority is a dated artifact a
   validator opens, not a sentence in a transcript.

## Decision outcome

Approved at these exact bytes:

| file | SHA-256 |
|---|---|
| `specs/047-autonomous-cycle-wall-budget/spec.md` | `1ec7e1719f8b75c0f290df92f07ab475dfddeb77cc8652eae11ac57412f91a5c` |
| `specs/047-autonomous-cycle-wall-budget/plan.md` | `e4252e37414112a0db2e653b08a2afe483560a47036cd6f5f0717ecd828a5e12` |

The plan digest is the canonical value — the tick column masked — which is the number the
envelope prints and every later `--tick` verifies against. The repository owner approved
in conversation on 2026-08-29 ("okay apruebo, vamos a por ello, máximo como mucho
tardamos 3h") and directed this plan's execution.

The plan's eight tasks are the exact authorised work: the three budgets in `contract.py`,
the red fixture that collects, the vitals reader, the report verb and its banner, the
five critics carrying their box, the batched `check-all`, the goal's anti-stall and batch
rules, and the close whose smoke runs the targeted set and lets PO-27's own evidence
command answer. Nothing past task 8 is opened by this record; each task commit runs its
named check in the same chain.

## Consequences

The wall budget becomes greppable truth: `grep -n CYCLE_WALL_BUDGET_MINUTES
src/ai_engineering/contract.py` answers from task 1 on, and PO-27 closes on its own row.
The cost this record approves knowingly: the 40/120 boxes are derived arithmetic, not
measurements, and the first three real cycles will show whether they are the right
numbers — the constants have one home, so the correction is one commit; vitals reads
only the framework's own stream, so a fork that hangs without emitting is visible as a
gap between events and never as a phase, which is the honesty the postmortem's B5 asked
for and no more; and `check-all` degrades to today's `check` if a future `just` drops
the `-` prefix, with the recipe test refusing the silent version. Whether `report
vitals` gates `ai-ship` stays a prompt until three measured cycles say it is code
(rule 12).
