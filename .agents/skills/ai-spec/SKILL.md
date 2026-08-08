---
name: ai-spec
description: >-
  Writes the record of a decision before any code exists: the problem, at least two real
  options, the one chosen and why the others were not, the decisions and accepted risks as
  blocks inside it, and the eight production-ready boxes unticked. Writes CONSTITUTION.md if
  this project has never had one, and seeds itself from a work item when you pass one.
  Trigger for "let's add", "how should we handle", "what's the best approach", "I'm thinking
  about", "what should we build for", "write the spec". Not for turning a spec into tasks —
  use /ai-plan. Not for writing code — use /ai-plan then say go. Not for judging what was
  built — use /ai-review.
license: Apache-2.0
compatibility: needs git; needs the ai-eng CLI on PATH
disable-model-invocation: true
---

# Write the spec

## What it produces

`specs/NNN-slug/spec.md`, committed, in the user's repository and in their diff. Nothing
here writes code.

## Steps

1. Read `CONSTITUTION.md`. If it does not exist, or still has `TODO:` markers, interview
   the person for it now — mission, who it is for, vocabulary, never, compliance gates,
   escalation, phase — and write it. A spec against an identity nobody wrote is a guess.
2. `ai-eng spec new <slug>` (add `--ref owner/repo#45` to seed the problem from a work
   item). This reserves the number and writes the scaffold.
3. Fill in **Context and problem** so that somebody who does not code can follow it. Say
   what is true today and what about it hurts. No solution yet.
4. Write **at least two real options**. A second option you invented to lose is not an
   option. Each gets what it costs and what it gives up.
5. Choose one in **Decision**, and kill the others in writing. That paragraph is what
   somebody arriving in a year is actually looking for.
6. Record each decision with `ai-eng decide "<title>" --why "<one sentence>"`. Then ask the
   single question that decides promotion: does this decision constrain specs that do not
   exist yet? If yes, `ai-eng decide --adr "<title>"` moves it to `docs/adr/` and leaves a
   pointer. If no, it stays where it has its context.
7. Record every risk you are choosing to live with as an acceptance:
   `ai-eng accept --finding <id> --expires <date> --by <person> --justification "<why>"`.
   It expires, and both `pre-push` and `ai-eng doctor` read that date.
8. Leave the **eight production-ready boxes** unticked. They are ticked by commands later,
   not by opinion, and `/ai-ship` refuses to mark this shipped while any is empty.
9. If you are reworking something already shipped, do not rewrite the old spec — that
   destroys the evidence of what was decided then. Write a new one with
   `supersedes: NNN` in the header, read the old spec and its plan first, and say what
   changes and why. Set the old one to `status: superseded`.

## Done when

- The spec answers, in plain words: what is wrong, what could be done, what will be done.
- Every decision has a rationale line. Every accepted risk has a date and a named person.
- The person has read it and said yes. That yes is the gate `/ai-plan` depends on.

## What this is not

It is not a design document that nobody executes. If a section has nothing real to say,
delete the section rather than filling it with prose.
