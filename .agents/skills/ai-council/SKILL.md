---
name: ai-council
description: >-
  Reads one specification through five lenses that never see each other, then has them read
  each other anonymously to find what every one of them missed and to refute what does not
  hold, then a chairman writes the page a person reads. Trigger for "council this spec",
  "read this from several angles", "what is this specification missing", "pressure-test this
  spec", "stress-test this before I sign it". Not for attacking the claims a specification
  makes — use /ai-challenge, which executes its sentences; this asks what is absent. Not for
  judging a diff — use /ai-review. Not for recording what was decided — use `ai-eng decide`,
  which needs a named person. It concludes and it never grants: it may write a verdict and a
  recommendation, and it may not write an approval, a PASS, a gate result or an accepted risk.
license: Apache-2.0
compatibility: needs git
context: fork
background: false
disable-model-invocation: true
---

# Three rounds, and the last one concludes

## What it produces

Two files beside the spec. `specs/NNN-slug/council.md` is the transcript.
`specs/NNN-slug/council.html` is the page the person reads. Both sit under `specs/`, the one
root this skill may write.

## Round one — five lenses, and none of them sees another

Cost, reversibility, the undecidable path, what is taken on trust, the example nobody wrote.
Each is a question, not a personality. Each reads the spec and nothing else. Not the plan,
not the chat, not another lens's answer.

That rule is not taste. Put one answer in a reader's context and a right answer turns wrong
66.5% of the time, against 10.3% for a plain re-ask (report 003). Nobody was named as its author. So the
harm comes from the words being there, not from being told who wrote them.

Reading alone also buys ground. Human reviewers who do not confer raise 14 issues a session
against 9 (report 003). And 70% (report 003) of what they find is seen by one reader only.

Every finding carries a command a reader can run to see the gap. One with no command is cut
before its section is written, and it is listed under its own heading below so the count can
be recomputed rather than believed.

## Round two — they read each other, and they do not rank

Each lens sees the other four answers, relabelled and shuffled, and **not its own**. It
answers two questions. Which of these findings is a false alarm, and what command shows it?
And what did all of us miss?

It is never asked which answer is best. Ranking five good answers is the worst case in the
measured work. One judge falls from 0.70 to 0.34 moving from pairs to a list (report 003). And the one
head-to-head of rank-then-write puts it under the best single reader.

What the cross-read buys is aim. False alarms fall from 22% to 5.3%, and no true finding is lost (report 003).

A refutation carries a command. The command is run and its output is written down. One with
no command is dropped, the same way a finding with none is.

A refuted finding is struck through and kept, with the refuting command beside it. It is
never erased: a real gap killed by a good-looking answer must leave more than a number.
Where one lens refutes and another agrees, the finding stays.

## Round three — a chairman, and it does not learn who said what

It is given the spec, both rounds, and no lens names. It writes new text rather than picking
a winner. Put the names back and a judge's bias for its own text moves from 0.511 to between 0.82 and 0.97 on the same words (report 003). So the names stay off in the one call that writes the answer.

It writes what the lenses agree on, where they clash, the blind spots the cross-read caught,
a verdict, a recommendation and one first step.

It may not write an approval, a `PASS`, a gate result or an accepted risk. `ai-eng decide`
with a named person is where that is written. A test refuses all four in this file.

## The shape `council.md` must have, because a script reads it

Three headings, each a list of top-level bullets: `### Gaps no single lens named`,
`### Findings cut for carrying no command`, and `### Findings the cross-read refuted, with
the command that refuted them`. The middle one is the round-one cuts, written down rather
than only counted, because the second total below names two causes and a file that shows one
of them cannot hold that total honest. All three are required; an absent one is an
unreadable file, not a zero. Then `## The two counts`, with exactly these two lines:

```
- Gaps that appeared only after the cross-read: **N**
- Findings deleted, for carrying no command or for being refuted: **N**
```

`just council` counts the bullets again and fails when its count and those totals disagree.
Do not write the totals you wanted. Write what is in the file. The check counts; it does not
read your number.

## Done when

Every lens has a section. Every finding carries a command. Every refutation carries one that
was run. The two counts are written and `just council` agrees with them. The chairman's page
exists. And nothing in either file grants anything.
