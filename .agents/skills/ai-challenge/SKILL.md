---
name: ai-challenge
description: >-
  Attacks a written specification from outside it: executes the sentences it claims are true,
  and reports where the tree disagrees. Trigger for "challenge this spec", "attack this
  decision", "is this spec true", "grill this before I approve it". Not for judging a diff —
  use /ai-review, which reads a change against a spec and cannot also be its accuser. Not for
  finding a cause in code — use /ai-debug. It never approves, revises or rewrites: it produces
  findings that carry a command, and a person decides what they mean.
license: Apache-2.0
compatibility: needs git
context: fork
background: false
disable-model-invocation: true
---

# Execute the sentence, do not re-read it

## What it produces

`specs/NNN-slug/challenge.md`, a list of findings. Every finding names a sentence in the
specification, the command that tested it, and what the command actually printed. A finding
with no command is deleted before the file is written: an opinion about a document is what
the document's own author already had.

## Why it is not the section inside the spec

`ai-spec` requires the author to challenge their own recommendation once, and that section is
worth keeping — but the questioner and the answerer are the same reader, and a reader can
only reason about what they already wrote. Measured on this repository: four of twenty specs
carry that section, and not one of the four contains a command or a file reference. Three
claims in one of them were false, and executing them is what found it.

## Steps

1. Read only the specification and the tree. Not the plan, not the pull request, not the
   conversation that produced it — a challenger who reads the author's reasoning inherits it.
2. List every sentence that asserts something checkable: a count, a path, a behaviour, a
   claim about another document. Those are the targets; the rest is intent and not yours.
3. Execute each one. A count gets counted, a path gets opened, a behaviour gets run. Paste
   what came back, including when it agrees.
4. Write the findings, worst first. `WRONG` when the tree says otherwise, `UNPROVEN` when
   nothing in the tree can decide it, and say which — those are different problems for the
   author.
5. Say what you could not test and why. A challenge that reports only what it managed to
   check reads as a clean bill of health.

## What this is not

It is not an approval and not a rejection. It never edits the specification: an accuser who
rewrites the charge is not one. And it is not a second opinion — a finding either carries a
command somebody else can run, or it does not exist.

## Done when

Every checkable sentence has a verdict beside the command that produced it, the untested ones
are named, and the file is committed in the same branch as the specification it attacks.
