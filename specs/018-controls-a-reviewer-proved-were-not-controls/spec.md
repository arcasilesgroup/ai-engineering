---
id: "018"
slug: controls-a-reviewer-proved-were-not-controls
status: draft
date: 2026-08-17
ref: ""
supersedes: ""
---

# Controls a reviewer proved were not controls

## Who this is for, and what it is worth to them

Whoever relies on this repository's own gates: the repository owner, and every consumer who
installs the wheel and inherits the same guards, the same security lane and the same
mutation cadence. They do not read the gates; they read whether the build is green.

What it costs them, measured on 2026-08-17 by one independent reviewer over twenty commits:
the whole-tree mutation gate could never pass, its alarm could never fire, the security lane
threw a traceback instead of a verdict on two ordinary inputs, a refusal named a false cause,
a machine-path control excused a whole file so it could grow without limit, and a preview
flag was inert for every caller without a keyboard. Every one of these was green. Two of
them had been announced, in a commit message, as fixed.

## Context and problem

This repository exists to cure one defect: a control that reads stronger than it is. It has
now found roughly fifty instances, and the finding rate has not fallen. What changed on
2026-08-17 is where they came from: all eight came from somebody other than the author
executing the control, and none from re-reading it.

Three of them are worse than ordinary, because the control had been announced. `0f912838`
says "the mutation lane stops being a red nobody can clear" and the gate it added reads
`completed_at` off a GitHub workflow-run object, which carries no such field — so `gh api`
answered `null`, the branch below was always taken, and every wide diff was told no
whole-tree run had ever completed. A paragraph about a one-time bootstrap sat directly
underneath, explaining the permanent red away. The alarm that was supposed to make the red
actionable named an issue label that did not exist, so the first genuine failure ran that
step, could not open the issue, and told nobody.

The suite could not see any of it. `tests/test_anti_theatre.py` wrote `completed_at` into
its own fixture and both readers agreed with the fixture that taught them, which is the
shape of the whole problem: two things agreeing is not evidence when one wrote the other.

## Options considered

1. **Fix the eight and move on.** Cheapest, and it is what a green build invites. It leaves
   the mechanism that produced them untouched, and the mechanism is the finding: eight
   defects in twenty commits, all invisible to a gate, all visible to a stranger in one pass.

2. **Add a rule that every control must be executed before it is claimed.** True and
   unenforceable. "I executed it" is exactly the claim that cannot be checked from inside
   the same head that makes it, which is why the eight survived a green run each.

3. **Fix the eight, and give each one a fixture that fails from outside the author's
   assumption.** For every finding, the repair lands with a check that would have caught it
   without the reviewer: the API's real field set written down, an exemption held to the
   names it excused, a check bound to the control it names, a guard's condition count pinned
   to its explainer's branches.

## Decision

Option 3. Every repair in this specification lands with the check that makes the next
instance of the same shape fail, and the check is written from something outside the code
under repair — the platform's actual response, the tree's actual contents, the guard's
actual source.

Two things this decision does not do. It does not add a review stage: `docs/adr/0011` already
requires an independent reviewer per block, and this is that reviewer's output, so the
process worked and the finding is about what the process found. And it does not claim the
eight are the last: it claims that after this, each of those eight shapes has a reader.

## Challenged once

**The strongest case against: eight fixtures for eight defects is fixing the last war. The
next defect will be a shape nobody has written a fixture for, and the fixtures are dead
weight in a repository already at its line ceiling.**

Half right, and the half that is right is why option 2 was refused. A fixture cannot
anticipate a shape. What these eight can do is stop the same shape recurring — and this
repository has already proved that shapes recur here: the SARIF reader threw an exception
through the security gate, and one commit later the threat-model reader did the same thing,
committed while fixing the first. The third instance is in this specification. A shape that
has recurred three times is not the last war.

The line cost is real and it is paid the way every other cost here is: in a ceiling move
whose comment says what was bought.

## Assumptions and unresolved risks

**Assumption.** That GitHub's workflow-run object keeps `updated_at` and keeps its current
meaning for a completed run. The field set is written into `tests/test_anti_theatre.py` from
a live call, so a removal turns the suite red rather than the gate silent — which is the
direction that matters, but it is still an assumption about somebody else's API.

**Unresolved.** The whole-tree receipt accepts a run that finished, passing or failing. That
was a deliberate decision and it is documented, but it means a nightly that fails every night
still satisfies the gate, and the only thing that converts that into action is a person
reading the issue. Whether that is enough is not decided here.

**Unresolved.** Nine of the nineteen absorbed capabilities have neither a home check nor a
phrase pin, and a comment in `contract.py` called the other sixteen "measured rather than
assumed". The sentence is corrected; the nine are still unmeasured.

Neither is an accepted risk. `ai-eng accept` is the only thing that accepts one.

## Examples somebody can check

**The success path.**
Given a pull request whose diff is too wide for the scoped mutation lane,
When a whole-tree run has completed within the window,
Then the gate prints how many hours ago the tree was measured and passes — verified by
running the gate's own snippet against the live API and reading `the whole tree was measured
0h ago`.

**The denial path.**
Given a threat model that is not valid UTF-8, or a directory the process cannot enter,
When the security lane reads it,
Then the lane returns a verdict — `1`, a failure — and never a traceback.

**The undecidable path.**
Given a repository whose `.ai/intent.md` differs from its last transition only in
`approval_ref`,
When a governed verb asks whether the Intent grants authority,
Then the refusal names that field and those two values, and does not say the role is one the
framework refuses to read.

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
