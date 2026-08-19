---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0014"
title: "A claim one document makes about another gets a comparator"
date: "2026-08-19"
spec: "010"
status: "proposed"
supersedes: ""
---

# 0014. A claim one document makes about another gets a comparator

## Context and problem statement

On 2026-08-19 the same defect was found nine times in one day, in nine different files, and
in every case the thing that was wrong was not the control the row described. It was a
sentence in one governed document making a claim about another, with nothing comparing them.

Each was true when it was written. Each stopped being true without anybody noticing, because
prose does not fail.

1. `policy/pilot-register.toml` published "red when an observed denial is older than seven
   days" and no receipt's declared window was ever compared to it. A receipt was free to give
   itself thirty-one days and stay green at thirty.
2. `PO-06`'s evidence asked GitHub for the runs on `fix/mutation-lane-green-on-main`, a branch
   the work had left and which has never had a run, and concluded from the empty answer that
   no CI had run on this branch.
3. `docs/audit-2026-08-16.md` explained the missing independent gate record by saying the
   workflow does not trigger on a push to this branch. It had run sixty-four times, starting
   the day that sentence was written.
4. The digest's rule-12 section printed only crossings, so an empty window and an absent check
   produced identical silence.
5. `EP-060` recorded "six controlled and two argued" about a table that had grown to thirteen
   recipes.
6. `EP-078` recorded "one capability of fifteen has a caller" in a note, where nothing counted.
7. `EP-302`'s ungated row said its refusal would reopen when "the record carries a red run
   somebody else can read". `tests/red_then_green.py` had been writing one for two days.
8. `EP-168`'s ungated reason said no code detects an interactive channel. Six modules did.
9. `EP-179` and `EP-324` were listed as ungatable while the ledger proved them, and `EP-324`'s
   reason described a gap that a reader closed the same afternoon.

`AGENTS.md` rule 12 says a judgement resolving the same way three times becomes a script. This
one resolved the same way nine times.

## Considered options

- **Leave it as a habit.** The habit produced nine instances in one repository in three days,
  and every one was found by executing something rather than by reading.
- **A linter over prose.** Separating a claim from an argument is a reading, and a tool that
  guessed would either pass everything or fail every paragraph containing a fact.
- **Ban numbers from prose.** Worse than the disease. The numbers are what make these
  documents worth reading; the defect is not that they exist but that nothing recomputed them.
- **A comparator per claim**, which is what the nine repairs already did, one at a time. Taken.

## Decision outcome

**A claim one governed document makes about another gets a comparator, or it does not get
made.** A comparator is a command that reads both sides and exits non-zero when they disagree.

Where a comparator cannot exist, the claim is written as a question rather than a statement,
and the document says which reading nobody has checked.

This is not a new gate. It is the rule that the nine repairs above already followed, written
down so the tenth is cheap: `tests/pilot_register.py` compares the register's quotes and order
against the report, its `why` count against the computed count, its bound against every
receipt, and its ungated rows against the ledger's verdicts; `tests/test_record.py` compares
the approval record's digests against the files; `tests/unreviewed.py` compares the audit's
hand-off ranges against git.

## Consequences

A number in a governed document now costs a comparator. That is the intended price: the nine
findings above cost more to discover than any of the comparators cost to write, and eight of
the nine were discovered by accident.

It does not apply to reasoning, only to claims. "This is refused because a router with one
phrase misroutes on paraphrase" is an argument and needs no comparator. "No code detects an
interactive channel" is a claim about the tree and needs one.

The rule cannot be enforced mechanically, and saying so is part of it: no command can read a
paragraph and tell an argument from a claim. What the existing comparators do is refuse the
specific shapes that have already caught this repository — a `reopen_when` naming a file that
exists, an ungated row the ledger proves, a `why` quoting a number the run computed
differently. Each was added after the shape had bitten once. This record exists so the next
one is added after it bites once rather than after it bites three times.
