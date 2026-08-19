---
id: "019"
slug: the-four-days-two-specs-cost
status: draft
date: 2026-08-19
ref: ""
supersedes: ""
---

# The four days two specs cost

## Who this is for, and what it is worth to them

The repository owner, who is the accountable role this repository's Intent names, and who
spent four days getting two specifications implemented. And the stranger who installs the
wheel expecting the same flow to work in a repository that has never seen it.

What it costs the owner today, measured rather than felt. Executing one task of the
approved plan requires reading 53,831 bytes of specification and 74,216 bytes of plan,
because no plan in this repository has a task structure a script can enumerate. The skill
the agent loads while implementing orders the full gate after every task and orders an
edit to the plan's checkboxes; the plan it is executing says the gate does not run per
task, and says any edit to the plan's bytes invalidates the approval the work proceeds
under. So the flow either burns the gate on every commit or stops to be re-approved, and
in practice it did both. The gate itself runs the same 2,104 tests twice and imports them
a third time, at 158.89 seconds a serial run.

What it costs the stranger. On a repository with no Intent, `ai-eng spec new` refuses and
tells them to write the Intent first, saying that the spec skill walks them through it.
The spec skill does not mention the Intent anywhere, and the function that writes one is
reachable from no verb. The first command a new user runs sends them to a document nothing
they can run will produce.

What changes when this is done. A task is handed to its executor as a small envelope
derived from the approved bytes rather than as the bytes themselves; the approved bytes
stop being edited by the act of executing them; a broken git call and a receipt from other
code both read INCOMPLETE instead of PASS; the behavioural examples a specification is
already required to write become a thing a command reads; the gate keeps every check it
has and finishes in roughly a third of the wall time; and the number of writers a build
uses becomes arithmetic over what the coordination records already hold, clamped to one
until the authority that wrote the one-writer sentence changes it; and one page under
`docs/` says what state the whole thing is in, generated from the records rather than
typed, and unable to go stale without the gate saying so.

## Context and problem

This repository is not slow because the model is slow. It is slow because seven things in
it disagree with each other, and each disagreement was verified by reading the code rather
than the documentation.

**Executing the plan un-approves it.** The plan of specification 010 states at its fifth
line that any edit to the plan's digest invalidates the approval and requires a new one.
The build skill states at its twentieth and thirty-seventh lines that the plan's
checkboxes must be updated to what actually happened. Following the skill breaks the
approval the skill is executing under. The plan skill, which is the only thing that
produces a plan, never mentions a checkbox; ten of the twelve plans have none.

**No plan can be reduced to a task.** Across the twelve plans the task structure is three
different shapes and sometimes absent: checkboxes in two, block headings in one, a bold
`**check**` field in eight, and four with no executable check at all. No test in the
repository opens a plan. Meanwhile every numbered step of the spec skill is pinned byte
for byte by a closed contract. The half that decides what an agent reads is unchecked, and
the half that decides how an agent is instructed is frozen.

**A broken git call reports a pass.** The helper that runs git inside the checkpoint
module discards the exit code and returns standard output only. With empty output the
staged file list is empty, the claimed-paths receipt reports PASS over zero files, the
privacy receipt reports SKIPPED, and the aggregate treats SKIPPED as neither a failure nor
an incompletion. Running the checkpoint against a base reference that does not exist is
enough to reach it.

**A receipt from other code counts as evidence for this one.** The executed-checks receipt
is chosen by age and outcome. It reads four fields and none of them binds the receipt to
the code it is supposed to be about, although the receipts on disk already carry the
command, the tool version, an input digest and an artefact digest, and although a sibling
module already models all four. The one receipt in the tree that is bound to the content
of every tracked file is the one the reader discards, because it has no finished-at field
and the exception handler swallows the resulting error.

**Two stages of the lifecycle are declared and absent.** The capability manifest declares
fifteen capabilities and the skills directory holds twelve. One of the three missing names
is the verify phase. A behavioural example is required by the spec skill, emitted by the
template into every new specification, and read by nothing: the only test that checks it
reads the template in memory, and sixteen of the eighteen specifications have no section
under that heading. What the repository calls acceptance is risk acceptance, not
acceptance criteria, and none of the ten review lenses is an acceptance lens.

**The gate pays for the same work twice.** The check target depends on eleven recipes. One
runs the whole suite; another runs the same suite under coverage, deselecting exactly one
test of 2,105; a third collects the suite again only to print how many tests there are; a
fourth runs one more targeted file. A single serial run of that suite is 158.89 seconds
and the same run under process parallelism is 61.72 seconds, with the identical pass,
skip and failure counts and a byte-identical coverage total. One unit test whose stated
claim is about a file reader calls the real security lane and spawns whichever pinned
engines are installed, and that cost is paid twice per gate. How much it costs depends on
what those engines have cached: one measurement of the file read twenty seconds, two later
ones read about two, and the difference is a warm dependency database, so the honest claim
is that the cost is unbounded from here rather than that it is any particular number. The
mutation runner runs the 158-second suite before the 13-second adversarial suite although
a mutant is killed when either fails, so the order is free and the expensive half is the
one that always runs.

**The width of a build is a sentence nothing enforces.** The Intent says one writer owns
repository changes until a separately approved coordination plan proves otherwise, and the
only reader of that sentence is a schema that checks the field exists rather than what it
says. The coordination machinery underneath is real and wired end to end, but the module
that answers ordering questions returns a single total order and throws away the set of
claims that could have started together, and its import edges never fire on this
repository's own import spelling, so anything derived from them today would call two
dependent modules independent. Two writers in one working tree overwrite each other's
claim file with no lock and no check, which is the one genuinely unsafe shape.

## Options considered

1. **Build the missing subsystem.** An orchestrator that owns the cadence: it reads the
   approved specification and plan once, derives tasks, schedules waves, dispatches
   writers, collects checkpoints, closes blocks and calls the gate. It gives one place
   where the whole flow is expressed and one place to change it. It costs a new module
   larger than any that exists, it duplicates the claim, DAG and checkpoint machinery that
   is already wired and already re-checked from the remote by continuous integration, and
   it puts the cadence in code before the cadence has been shown to hold in prose. It
   rules out incremental delivery: nothing improves until the whole thing lands, which is
   the same broad front that produced the four days.

2. **Nine bounded repairs to what already exists, ordered so the earliest unblocks the
   rest.** Each repair touches one module or one skill, has one command that fails today
   and passes after, and can be reverted on its own. Two of the eleven are pure removals of
   duplicated work. It gives velocity back inside the first three repairs and leaves the
   architecture where it is. It costs a longer list to hold in one's head, and it accepts
   that no single file will explain the cadence. It rules out the orchestrator until the
   repairs have shown which parts of the cadence a script can actually decide.

3. **Buy the speed from the gate.** Lower the coverage floor, drop the second suite run,
   drop the mutation cadence, and stop running the security lane locally. It is the
   cheapest thing to do and it works immediately. It costs the property the repository is
   named for. It rules out every claim this framework makes about false green results, and
   the repository's own record already says that lowering a floor to go green is the
   defect it exists to name.

## Decision

Option 2. The eleven repairs, in two blocks separated by an authority boundary.

**Block A needs no authority the repository does not already hold.** In order:

1. **Stop the plan being edited by its own execution.** Move the record of what was done
   out of the approved bytes: the build skill no longer edits a checkbox and no longer
   runs the full gate per task, it runs the task's focal check and the module's cheap
   suite and labels the hand-off unreviewed. Check: a contract test asserting the word
   checkbox does not appear in the build skill, which it does twice today.

2. **Make a broken git call read INCOMPLETE.** The git helper raises on a non-zero exit
   and the two callers turn that into an incompletion rather than a pass or a skip. Check:
   verifying a checkpoint against a base reference that does not exist must not return
   PASS, and today it does.

3. **Bind the executed-checks receipt to the code it covers.** Stop discarding the one
   receipt that carries a content digest of every tracked file, and prefer it. Check: a
   fresh passing receipt written before a staged file changed must read INCOMPLETE.

4. **Give the gate its time back without removing a check.** Run both full-suite recipes
   under process parallelism at the detected core count; stub the three security engines
   in the one unit test that spawns them and whose claim is about a file reader; run the
   cheap adversarial suite before the expensive one inside the mutation runner. Check: the
   pass, skip and failure counts and the coverage total are unchanged across three runs,
   and the wall time of the suite recipe is under ninety seconds where it was 158.

5. **Make the behavioural examples real and read.** The template's example prompt asks for
   at least one Then that names a command and the output it prints; a parser in the
   specification module counts what a section actually contains and the show subcommand
   prints what it observed without deciding anything; one contract test requires the
   section on new specifications with the older ones frozen by two explicit closed lists,
   because the structure baseline and the executable baseline are not the same set.

6. **Retire the declared-and-absent verify capability by building it.** One skill with two
   routes: verify runs the gate and the security lane and ticks each production-ready box
   beside the command that ticked it; validate walks the specification's examples and
   marks each of them passed, failed or incomplete against a real command, defaulting to
   incomplete for any example with no command pasted beside it. This reverses a decision
   the record already holds: D-012-04 made absorption into the review lens the verify
   capability's exit condition, and two rows of the requirements register say a passing
   test forbids the skill from existing. What changed is that repair 5 gives the validate
   route something to read — a section a command can parse — which is the consumer the
   absorption decision was taken in the absence of. Both register rows and the ledger note
   move in the same commit as the skill; a skill that lands while the register still says
   it must not exist is two records disagreeing, which is the defect this repository names.

7. **Give on-demand dynamic scanning the home the record already chose, and say out loud
   that it is empty.** The security research and specification 014 both put it inside the
   security skill and both refuse a separate skill by name. Nothing caps the number of
   skill directories — what the capability manifest caps is the identifier list, at fifteen
   with a closed enumeration, and the verify identifier is already one of the fifteen, so
   repair 6 needs no schema change and a dynamic-scanning identifier would. The repair here
   is one printed line at the end of the security report declining the dynamic surface
   rather than passing silently over it, plus the routing sentence in the skill and its
   corpus. Check: a new test asserting the declined line is printed and the report still
   exits zero.

8. **Make the coordination edges see this repository's own imports, and expose the set the
   ordering already computes.** The module derivation must match the package spelling this
   tree uses, and a function must return the claims with no incoming edge. Until the first
   half lands, anything reading those edges is failing open.

9. **Make one working tree, one writer a refusal instead of a sentence.** Taking a claim
   when the tree already holds a different one is refused with a named code and a cure
   that says to release it or take the task in its own worktree. A claim file that cannot
   be read is the same refusal, because a scope the guard cannot see is not a scope.

10. **Make a plan's tasks something a script can enumerate, which is what the envelope was
   always waiting on.** Context named it as the second problem and the first nine repairs
   do not touch it: no executor can be handed a small envelope while the task structure is
   three different shapes across twelve plans and four of them carry no executable check at
   all. One contract test requires each task of an authored plan to name a file, a check
   that is a command in backticks, a rollback and a done-when, with the four plans that
   carry none frozen by name; and the show subcommand grows one option that prints the
   envelope for a named task — its identifier, the digest of the specification and of the
   plan it came from, the file, the check, the rollback and the done-when. It prints an
   observation and grants nothing, and it adds no subcommand, so the verb's closed list of
   five does not move.

11. **The Solution Intent a person reads lives in `docs/`, is generated, and cannot go
   stale quietly.** Today the only Solution Intent is a JSON file under `.ai/` that no
   human reads and that says in hand-typed prose what the machine could compute — and the
   one fact it asserts, that every production-ready box is incomplete, is a sentence rather
   than a reading. The repair is one page at `docs/solution-intent.html`, generated from
   records the repository already keeps: specification frontmatter, plan tasks, decision
   records, the Intent itself, the hook classes, the verb table, the line and ratio
   ceilings, and the eight boxes as the readiness module verifies them. It carries the
   digest of everything it was built from, and one gate step recomputes that digest and
   fails when the page stopped being about this tree. It decides nothing and it writes
   nothing back: a status on that page is what a file says, and the proof is still a
   receipt from a check that ran.

**Block B needs the authority Block A cannot supply.** The build width — how many writers
a surface may run — is computed by a new read-only subcommand as the smallest of the
declared surface width, the size of the independent set, and one; and it is clamped to one
for as long as the Intent still carries the one-writer sentence, which is the check
specification 013 asks for by name. The command computes a width and never spends it. The
build skill may only stop clamping when the accountable role approves a coordination plan
at an exact digest and the Intent's constraint changes in the same commit.

Option 1 loses because the machinery it would build is already wired and already
re-checked from the remote, and because it delivers nothing until all of it lands. Option
3 loses because it trades the only property this repository sells.

Three judgements stay judgements, with their reasons written here as rule 12 requires.
Whether a surface can run more than one writer does not resolve the same way twice — it
differs by surface and by session — so the surface reports a number and the arithmetic
that clamps it is the script. Whether an authorised target exists for a dynamic scan is
consent, not computation, so the preflight stays in the skill. Whether a behavioural
example is the right example is a reading, so the gate checks that it names a command and
its output and never that the example is correct.

## Challenged once

The strongest case that this is wrong: eleven repairs touching the checkpoint module, the
coordination module, the claim module, the scan module, the specification module, the
build file, three skills and two test files is not a specification, it is a roadmap, and
a roadmap presented as one decision is exactly the broad front that produced the four days
it claims to fix. A reviewer would be asked to approve eleven unrelated things at once,
and the first one to go wrong would take the other ten with it.

The case lands, and the decision is revised rather than kept. The eleven are split at the
authority boundary that already exists, which is also a dependency boundary: repairs 1
through 11 change no constraint the Intent carries, and the plan built from them groups
them into blocks that are reviewed one at a time rather than as one approval. Each is
revertible alone. Three orderings are not free and the plan states them: the second half
of repair 8 must not ship before its first half, because a set derived from edges that
never fire is worse than no set; repair 5's parser must land before the gate that calls it
and before repair 6's validate route reads it; and repair 4 comes first, because every
later block close pays the gate it makes cheap. Block B changes what the Intent
says one writer means, and it may not be reviewed in the same block as anything else.

What would falsify the revision: if the block review of Block A returns a second new
family of blocking findings after one repair wave, the split was wrong and the work
returns here rather than continuing. That is the same stopping rule the plan protocol
already carries, applied to this specification's own delivery.

## Assumptions and unresolved risks

Assumptions, which are taken as true here and not proven by this document. That the two
skills whose wording changes are not pinned by a closed contract string the way the spec
skill is, so their wording may be revised without a mirrored edit. That the coverage
total, the pass count and the skip count observed under process parallelism on an
eight-core machine hold on the continuous integration runner, which was not measured. That
the receipt carrying a content digest of every tracked file is written often enough to be
present when a checkpoint asks for one, which is true in the current cadence and was not
proven for a fresh clone.

Unresolved risks, which are open and are not accepted by anybody here. The line ceiling
had zero margin at the time of writing and the measurement is only trustworthy while a
single writer holds the tree; a second session held it during this work, so the arithmetic
that reseals the ceiling must be run by whoever holds the tree alone. The approval record
that pins specifications 016, 017 and 018 at exact digests is read by no test, and two of
its four digests have already drifted; a baseline that freezes older specifications leans
on that record, so the drift is a decision the accountable role has to take and not one a
gate can take for it. Process parallelism at more than the core count produced two
unexplained extra failures in one run of two, so the detected core count is the only
setting this specification proposes. The mutation baseline exists only as prose and the
statistics file is not tracked, so no command can currently answer whether the mutation
score fell; until a baseline is committed, every claim in this document about not losing
quality under a speed change rests on the pass, skip and coverage numbers alone.

## Examples somebody can check

**The success path.** Given a working tree whose specification and plan are approved and
whose build skill no longer edits the plan, When a writer completes one task and runs the
module's cheap suite rather than the whole gate, Then the plan's bytes hash to what was
approved before the task started and the checkpoint is labelled unreviewed — verified by
running `git diff --stat -- specs/010-governed-agentic-engineering-foundation/plan.md`
and reading `0 files changed`.

**The denial path.** Given a checkpoint asked to verify a range whose base reference does
not exist, When the git call underneath exits non-zero and returns nothing, Then the
claimed-paths receipt reports INCOMPLETE and names the failed git command, and the
aggregate verdict is not PASS — today the same input returns PASS over zero files.

**The undecidable path.** Given a specification whose examples section exists and carries
three Given lines, three When lines and three Then lines, none of which names a command,
When the contract test that reads authored specifications runs, Then the specification
fails the executable clause and passes the structure clause, and the failure names which
of the two it was — because a section that reads as complete and contains nothing runnable
is the case this gate exists to separate from an empty one.

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
