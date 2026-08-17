---
id: "017"
slug: decision-brief-as-an-artifact
status: draft
date: 2026-08-17
ref: ""
supersedes: ""
---

# Decision brief as an artifact

## Who this is for, and what it is worth to them

The person who has to answer when a governed run stops, and the people they have to answer
to. In this repository that is the repository owner; in a consumer's repository it is
whoever holds the accounts the framework cannot hold — the analyser, the branch protection,
the approval. Often they are not the person who wrote the code, and sometimes they are a
client or a manager who will never open it.

What it costs them today, measured on 2026-08-17 in this repository: the framework stopped
on five things and reported them as a paragraph in a terminal, in the vocabulary of the
thing that was blocked. The owner replied that it was not actionable. Making it actionable
took gathering the real data — and doing that found that two of the five items were wrong:
one count was stale by two and included a finding that was a genuine security weakness
rather than a false positive, and one item had no evidence anywhere in the repository at
all. Five items became four, and one of them turned out to be code to fix rather than a
decision to take.

That is the value, and it is not presentation. **A blocker written in the vocabulary of what
is blocked cannot be acted on by the person who has the authority to unblock it — and it
cannot be checked either.** Forcing it into a form somebody can execute is what exposed the
errors.

## Context and problem

The framework already refuses well. Guards fail closed, `INCOMPLETE` is never a pass, and a
verb that cannot prove something says so. What it does badly is the moment after the
refusal: it prints a reason and stops.

Three things are missing from that moment, and each was measured here.

**It is not actionable.** "Nine SonarCloud findings need marking" names no URL, no click
path and no text to paste. The person has to reconstruct the work from the sentence.

**It is not checkable.** Because nothing forced the sentence to carry the link, the count
in it went stale by two and nobody could tell. A brief that must carry the evidence cannot
carry a number nobody re-measured.

**It does not distinguish "I lack access" from "me doing this would void the control".**
Three of the four real blockers exist because an agent marking its own analyser findings
benign, rewriting the specification that binds it, or re-approving the plan that limits it
would destroy the thing being relied on. That distinction is the product's whole argument
and it was invisible.

There is a fourth problem underneath, and the owner named it: in an autonomous or
multi-agent run there may be nobody to read the brief at all. That is a different question
and this specification does not answer it — see the challenge below.

## Options considered

1. **Leave it as terminal output, and rely on the operator asking.** Free, and it is what
   happens today. It failed on its first real use: the operator asked, and the answer that
   came back was wrong in two of five items because nothing forced it to be built from
   measurements. A report nobody can execute is also a report nobody can falsify.

2. **A machine-readable blockers file, and let each surface render it.** Honest and small:
   the framework emits JSON and whoever consumes it decides how to show it. It moves the
   whole problem to the consumer, who then has nothing — and the failure mode is a schema
   with no renderer, which is the "written and not wired" defect this repository has found
   four times in one session.

3. **The framework publishes a rendered brief, and the brief is a governed artefact.** It
   carries, per blocker: what it is in plain words, why the agent cannot do it, what it
   unblocks, what happens if it stays, the cost, and — the part that makes it a brief rather
   than a report — the exact link, the click path and the text to paste. Built from
   measurements taken at the moment of writing, never from the previous brief.

## Decision

Option 3, with the constraint that makes it worth building: **every item in the brief is
derived from something executed at the moment the brief is written.** A link comes from an
API or a file, a count comes from a command, a corrected sentence comes beside the output
that disproves the old one. An item that cannot be derived says so and stays in the brief as
undecided rather than being dropped or guessed.

Two things this decision explicitly does not do:

- It does not create a second source of truth. The brief renders what the record already
  holds — the register, the audit, the specs, the analyser — and holds nothing itself.
- It does not grant anything, ever. A brief is how a decision is presented; `ai-eng decide`
  and a human are how one is taken.

## Challenged once

**The strongest case against: in an autonomous run there is nobody to read it, so a brief
that stops and waits is a system that cannot finish. The owner made exactly this argument
and asked whether a council of models decides instead.**

The challenge is right about the problem and wrong about the answer, and the reason is in
`CONSTITUTION.md`: *"Models may investigate, propose and review; they never grant authority
or accept risk."* A council of models approving its own work is the same agent speaking
three times — the false consensus the evolution proposal deferred by name, and which
`policy/pilot-register.toml` already records as a prohibition. Building it as the escape
hatch for autonomy would remove the brake to go faster.

The same constitution names the answer in the next sentence: *"A human or an already
approved versioned policy supplies authority."* The autonomous path is a policy the owner
approves **in advance**, saying what an agent may do without asking — reversible,
least-scope, and never anything that widens its own authority. A council invents authority
in the moment; a pre-approved policy carries the owner's authority forward in time and it
stays theirs.

So the decision stands and it is deliberately half of the answer. The brief is the path when
a person exists. The pre-approved policy is the path when one does not, and it is a separate
specification because it is a separate risk: the brief can only mislead, while a policy can
act.

## Assumptions and unresolved risks

**Assumptions.** That the accounts a brief points at stay reachable to the person who
receives it, and that a published page is an acceptable channel for what a blocker contains
— which is true here because a blocker names what is blocked and never why it matters
commercially, but is an assumption in an organisation with stricter rules about where a
repository's state may be rendered.

**Unresolved.** Where the brief is published is undecided: a hosted artefact is what worked
here, a file in the repository costs line budget and is visible to everybody with clone
access, and a surface-native panel does not exist. Undecided, and named as undecided.

**Unresolved.** Whether the brief should ever include a blocker the framework inferred
rather than hit. Today every item is something a command returned. Widening that is how a
brief starts predicting, and a brief that predicts is a brief nobody trusts twice.

Neither of these is an accepted risk. `ai-eng accept` is the only thing that accepts one.

## Examples somebody can check

**The success path.**
Given a governed run that stopped on an analyser finding, a specification whose sentence a
command disproves, and a merge that needs an account the framework does not hold,
When the brief is produced,
Then each of the three carries the link that reaches it, and the analyser item carries the
text to paste, and the specification item carries the wrong sentence, the output that
disproves it and the corrected sentence.

**The denial path.**
Given a brief that would state a count,
When the count cannot be derived by a command at the moment of writing,
Then the brief says the count is not measured rather than carrying the last one anybody
wrote down, and the item is marked undecided.

**The undecidable path.**
Given an autonomous run with no person to receive a brief and no pre-approved policy
covering the blocker,
When the run reaches it,
Then the result is `INCOMPLETE` with the blocker recorded, and the run stops. It does not
convene a council, it does not decide by majority, and it does not proceed on the grounds
that nobody was available to object.

## Decisions

<!-- ai-eng decide writes yaml blocks here -->

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI
