---
name: ai-council
description: >-
  Reads one specification through five lenses that never see each other, then has them
  read each other anonymously to refute what does not hold and to name what every one
  of them missed, in one pass whose verdict the author writes into the specification.
  Trigger for "council this spec", "read this from several angles", "what is this
  specification missing", "pressure-test this spec", "stress-test this before I sign
  it". Not for attacking the claims a specification makes — use /ai-challenge, which
  executes its sentences; this asks what is absent. Not for judging a diff — use
  /ai-review. Not for recording what was decided — use `ai-eng decide`, which needs a
  named person. It concludes and it never grants: it may write a verdict and a
  recommendation, and it may not write an approval, a PASS, a gate result or an
  accepted risk.
license: Apache-2.0
compatibility: needs git
context: fork
background: false
disable-model-invocation: true
---

# One pass: five lenses, one cross-read, a verdict inside the spec

## What it produces

The specification's `## Council` section: three machine-read headings, the two counts,
a verdict, a recommendation and one first step. No transcript file and no page beside
it — the section is the record and the record is the artifact.

## The lenses, and none of them sees another

Cost, reversibility, the undecidable path, what is taken on trust, the example nobody
wrote. Each is a question, not a personality. Each reads the spec and nothing else.
Not the plan, not the chat, not another lens's answer.

That rule is not taste. Put one answer in a reader's context and a right answer turns
wrong 66.5% of the time, against 10.3% for a plain re-ask (report 003). Nobody was
named as its author. So the harm comes from the words being there, not from being
told who wrote them.

Reading alone also buys ground. Human reviewers who do not confer raise 14 issues a
session against 9 (report 003). And 70% (report 003) of what they find is seen by one
reader only.

Every finding carries a command a reader can run to see the gap. One with no command
is cut before its section is written, and it is listed under its own heading below so
the count can be recomputed rather than believed.

## The cross-read, inside the same pass

Each lens then sees the other four answers, relabelled and shuffled, and **not its
own**. It answers two questions. Which of these findings is a false alarm, and what
command shows it? And what did all of us miss?

It is never asked which answer is best. Ranking five good answers is the worst case in
the measured work: one judge falls from 0.70 to 0.34 moving from pairs to a list (report 003).
What the cross-read buys is aim: false alarms fall from 22% to 5.3% (report 003), and no
true finding is lost.

A refutation carries a command. The command is run and its output is written down.
One with no command is dropped, the same way a finding with none is.

A refuted finding is struck through and kept, with the refuting command beside it. It
is never erased: a real gap killed by a good-looking answer must leave more than a
number. Where one lens refutes and another agrees, the finding stays under the gaps
and is not also listed under the refuted heading — one heading owns one finding, or
the two counts double-count what the counter exists to keep honest.

## The verdict, and who writes it

The author writes it, because the author is the one who must answer the findings:
what the lenses agree on, where they clash, the blind spots the cross-read caught, a
verdict, a recommendation and one first step. The section opens with its declaration
— `ran: round <n>, <date> — <n> min` — and names its five lenses; the no-authority
rule refuses a tally of them, so they are named, never counted.

It may not write an approval, a `PASS`, a gate result or an accepted risk.
`ai-eng decide` with a named person is where that is written. A test refuses all
four in the section.

## The shape `## Council` must have, because a script reads it

Three headings, each a list of top-level bullets, or one literal `none` line when the
heading found nothing: `### Gaps no single lens named`, `### Findings cut for
carrying no command`, and `### Findings the cross-read refuted, with the command that
refuted them`. The middle one is the round-one cuts, written down rather than only
counted. All three are required; an absent one is an unreadable section, not a zero.
Then `### The two counts`, with exactly these two lines:

```
- Gaps that appeared only after the cross-read: **N**
- Findings deleted, for carrying no command or for being refuted: **N**
```

## The loop is bounded

At most two rounds against the same spec digest — the canonical bytes `ai-eng spec
show` prints. A revision changes the digest and reopens the count; the second round
against an unchanged digest is the last. At the ceiling, write the outstanding
findings worst first and hand the page to the person. The two-identical-greens rule is
the orchestrator's instrument, not yours: the skill layer's bound is this one, and an
automated cycle ends only on two digest-equal green runs when such a cycle exists.

## What this is not

- "The spec is short, so one careful read is enough" — measured on report 003, most real findings are seen by exactly one reader, which is why the five lenses and the cross-read exist.

## Done when

Every lens is named in the `## Council` declaration. Every finding carries a command.
Every refutation carries one that was run. The two counts are written and
`just council` agrees with them. And nothing in the section grants anything.
