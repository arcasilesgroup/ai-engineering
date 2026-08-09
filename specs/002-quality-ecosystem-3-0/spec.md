---
id: "002"
slug: quality-ecosystem-3-0
status: draft
date: 2026-08-08
ref: ""
supersedes: ""
---

# What a quality model changes here, and what it does not

## Context and problem

Two questions arrived together, and they turn out to have the same answer.

The first came with a fifteen-slide deck, *Ecosistema de Calidad 3.0*. It describes a
quality system in four parts: write acceptance criteria in a testable form before anything
is built; move testing effort off the screen and onto the interfaces underneath it; make
security an automatic part of the pipeline with an unalterable evidence trail; and treat
the model as something that accelerates a person's judgement rather than replacing it. The
question was what of that should enter this framework so that writing a spec, planning it,
building it, shipping it and reviewing it all get better.

A second question arrived with it, about whether a second repository's governed-document
work should become a skill here. That one is answered in `specs/004-solution-intent-home`,
because its decision changes no line of this framework and its work lives elsewhere. It is
cited below only where it supplies evidence, and this spec does not decide it.

### What is true today

This framework already records **what was decided**. `ai-eng decide` writes the decision
and the sentence explaining it. `ai-eng accept` writes the risk somebody chose to live
with, the date it expires and the person who signed it. `ai-eng audit verify` walks a
hash-linked record that lives outside every copy of the repository. Eight boxes at the
bottom of every spec name the eight things that must be true before anything gets a web
address, and `/ai-ship` will not mark work shipped while any of them is empty.

So most of the deck is already here under other names. The evidence trail it calls forensic
readiness is the hash chain. The pipeline stages it lists as six phases are the eight boxes
plus the rollback line every plan task already carries. The governed-model half of its
fourth part is this whole product.

What is not here is smaller than the deck and worse than it looks, because all three of
these were found by running the code rather than by reading it.

**One. A ticked box is not read by anything.** Assertion 19 searches a shipped spec for
`- [ ]` — an *unticked* box — and fails if it finds one. It never looks at a box that has
been ticked. So the framework enforces that you answered the question, and never that your
answer says anything. Three of the eight boxes in this repository's own shipped spec claim
a control and name no command to prove it:

```
- [x] CI/CD — check.yml runs the gate, the suite and the install matrix on every push
- [x] Logs — one JSON line per decision, six closed classes, hash-chained
- [x] External check — the install matrix runs a stranger's first five minutes on three OSes
```

Each of those is a sentence a person believes. The five beside them name a file or a
command in backticks. The gate cannot tell the two groups apart, and `/ai-ship` tells the
model to write the command beside every tick — an instruction with no assertion behind it,
which this repository's own first spec calls prose.

**Two. The artifact we offer an auditor can be written unsigned.** `ai-eng accept` takes
`--by` and `--justification`, and when they are left out it writes the literal strings
`TODO: a person, by name` and `TODO: why this is acceptable, in one sentence` into the
record. Assertion 16 compares the expiry date and nothing else. So an accepted risk with no
owner and no reason passes every gate we have, and the constitution's promise — dated risk
acceptances with a named owner — is a promise the code does not keep.

**Three. One assertion is green on nothing.** Assertion 6 is called *the hash chain is
intact and writable*. Its second line is `if not path.exists(): return None`. Run it against
a machine where the chain was never written and it creates the parent directory and reports
ok. Measured, with the chain path pointed at a file that has never existed:

```
chain file exists: False
check 6 verdict : None -> ok (GREEN)
dir created     : True
```

It proved that a directory can be created. It did not prove the chain is writable, and
there is nothing for it to prove intact. The constitution names this exact failure as the
product: doing nothing silently is reporting green while blind.

This is bounded, and the bound matters. All twenty-one assertions were run against an empty
repository: five failed, six correctly declined to answer, and ten reported ok. Nine of
those ten are honest — they are statements about tables inside the package, or conditions
that hold when there is genuinely nothing to check. Assertion 6 is the only one that
measured nothing and called it clean. The cure already exists here and works: an assertion
that cannot decide raises `Undecidable`, prints a question mark and is never counted as a
pass. Assertion 6 simply does not use it.

### The two things the other repository proves, which decide what we can add

Spec 004 sets out that estate in full. Two of its findings are load-bearing here, and both
are about the difference between a rule written as prose and a rule written as a gate.

Three skills there describe how to write that repository's governed document. They describe
the third version of its mould. The corpus is on the fifth. They rotted at a distance of
zero — same repository, same author, same reviewer, nothing between them and the original
except the intention to keep them in step. That is why every proposal in this spec that
would have added instruction to a skill was refused, and why the two that survive delete
prose the moment a gate replaces it.

And its weekly watcher has been blind since that mould changed: it searches each document
for a block the fifth mould moved out, finds it in none of the sixteen, measures nothing,
and reports a clean week. It was written never to fail, so its empty answer and its
all-clear answer print the same thing. That is the same failure as assertion 6 below,
found independently in two codebases in one afternoon, which is why it is worth two lines
to close here.

## Options considered

1. **Adopt the deck as written.** Add a section to every spec choosing between four
   acceptance-criteria formats, a mandatory Given/When/Then line on every work item, a
   ninth production-ready box for dynamic security scanning, a translation procedure from
   safety analysis to test scenarios, and a skill that authors Solution Intents. Roughly two
   hundred lines across the skills, the template and the assertions, against a ceiling with
   no room. Rejected on mechanism rather than price. A decision tree that turns prose into
   prose has no exit code, so rule 12 can never retire it into a script. A rule that a
   ticket must contain the words Given, When and Then goes red only when they are absent
   and green on *Given a user, When they click, Then it works* — which is the vague
   criterion the deck's own slide condemns. A gate that cannot fail is worse than no gate,
   because it reports green.

2. **Take nothing, and write down that the deck is already covered.** Cheapest, honest
   about most of the deck, and wrong about three things. The two holes in the record and the
   assertion that greens on nothing are real, verified by running the code, and every one of
   them lets this framework report a result it has not observed. That is the one failure the
   constitution names as unacceptable, so leaving it is not an option we can write down.

3. **Take only what can be made to fail closed, delete what invites vagueness, and write
   down why the rest stays prose.** Chosen.

## Decision

Take three gates and one deletion.

**The gates.** Assertion 19 stops rewarding the tick: a ticked box in the production-ready
section that names nothing in backticks, and does not say *not applicable*, fails. The same
assertion refuses a shipped spec that still carries an unfilled template marker. And
`ai-eng accept` refuses to write an acceptance with no named person and no reason — the
failure moves from the gate at the end to the keyboard at the start, which is cheaper and
earlier, and it deletes three strings rather than adding a check.

Two corrections that came from running the proposed gates against this repository before
proposing them, and both change the gate rather than the prose.

The marker rule cannot be `"TODO:" in text`. Measured against all four specs in the tree,
that form has exactly one hit and it is **this spec**, which quotes the literal strings
three times as evidence for the second hole. A gate whose only red in the whole repository
is the document arguing for it is not a gate, it is a trap. The rule is anchored instead —
a marker at the start of a line, allowing a list marker before it, written
`^\s*(?:[-*]|\d+\.)?\s*TODO:`. Measured: four hits on the template `ai-eng spec new`
writes, which is the entire target, and zero on all four specs including this one.

And all three of `accept`'s fallback strings go, not two. `--follow-up` was going to stay
optional, but it writes `TODO: what has to happen before it expires` when omitted, which
means every acceptance without a follow-up would make its spec permanently red the moment
it ships. That is the same coupling the deletion below exists to break, found a second
time. An absent follow-up becomes an empty field, which is what the prose claimed it
already was.

Assertion 6 stops greening on absence. When the chain has never been written it declines to
answer instead of passing, which is what `Undecidable` is already for.

**The deletion.** `ai-eng spec new --ref` currently fetches a work item and pastes up to
twelve hundred characters of its body into the problem statement. That is twenty-nine lines
whose entire effect is to prefill the one section the skill tells the author to write from
scratch, with truncated prose from a tracker — which is precisely the vague requirement the
deck's first part exists to prevent. The flag survives, the frontmatter reference survives,
and `/ai-ship` still closes the work item. What goes is the whole fetch, the paste and the
title seeding with it: `seed()` returns both, the heading it supplies is the same borrowed
sentence one line further up, and the plan's check deletes the function rather than
narrowing it.

Rule 10, one line each, because a spec is where these are supposed to earn their keep:
**KISS** — every gate here is a text scan inside an assertion that already exists; no new
check number, no new file class, no config key.
**YAGNI** — the four acceptance-criteria formats, the ninth production-ready box and the
safety-analysis translation are each built for a problem nobody here has had, and each is
refused for that reason before price is discussed.
**DRY** — the sentence in `/ai-ship` asking for a command beside every tick is deleted in
the same commit the gate starts asking for it, or the repository now holds the same rule
twice and one copy drifts.
**SOLID** — `accept` refuses an unsigned acceptance at its own boundary instead of leaving
`doctor` to notice later; the verb owns the invariant it is named for.
**TDD** — every task names a check that is red before it and green after, and task 4's diff
exists to be the evidence that task 5's gate works.
**Clean Code** — the assertion is retitled to what the code observes, a box ticked with no
command, rather than what a reader would like it to mean, that the work is finished.
**Clean Architecture** — nothing added crosses the line the tree is built on: the hooks
still never import the package, and both edits land in the half allowed to import freely.

The context-engineering guidance for this model generation points the same way, and it is
what killed the largest candidates rather than the smallest. Every proposal that would have
added a sentence of instruction to a skill died; the two that survived delete instruction
the moment a gate replaces it. Nothing here adds a line to `AGENTS.md`, and no skill grows.

**The arithmetic, for the operator to approve or refuse.**

Two of the five numbers below were wrong when this spec was first written, because they
were estimated rather than measured. Both are now measured by applying the change to a copy
and counting: the deletion is thirty-one lines, not twenty-nine, and the `accept` change is
zero, not minus two — three fallback strings shorten three lines without removing any, and
two flags become required in place. The net is unchanged at minus eighteen, which is the
coincidence that would have hidden both errors if the total had been the only thing checked.

| | lines |
|---|---|
| A ticked box must name a command | +6 |
| No unfilled template marker in a shipped spec | +5 |
| Assertion 6 declines instead of passing | +2 |
| `ai-eng accept` requires a person and a reason | 0 |
| Delete `spec.seed()`, its call, the paste and the import | −31 |
| **net** | **−18** |

**The durable number is the delta: minus eighteen. Every absolute below is a snapshot with
a head attached, and it is derived, never stored.** At `31fa6cf4` the count was 5,764
against a ceiling of 5,764, so this change would close at **5,746**. That absolute has
already been restated twice — it was 5,592 against 5,610 when this spec was written — and a
coverage push is expected to move the count again before this lands. Whoever implements this
recomputes it with `contract.repo_lines()` at the head they are on rather than reading it
here, for the same reason `AGENTS.md` stopped quoting the ceiling: a number written in two
places drifts, and the copy that drifts is the one nobody executes. This spec names the home
and the delta; the constant is the value.

**No raise is requested at any of those heads.** The question that remains is whether the
ceiling follows the count down or stays where it is and banks the difference. The
recommendation is to follow it down. The ceiling is not a budget, it is the mechanism that
forces a conversation before the next addition, and eighteen banked lines are eighteen lines
of silent permission. The comment on the constant already reaches the same conclusion from
the other direction, in its own words — *it closes at the count that landed* — written by
the commit that raised it to 5,764 after predicting plus fifty-one and measuring plus one
hundred and fifty-four. That gap is the best argument in the tree for why the delta is the
claim and the absolute is a measurement.

Two things this deliberately does not do. It does not add a section to the spec asking how
we will know the work was right — every version of that gate died the same way, because the
skill itself tells the model to delete a section with nothing real to say, so the gate's
subject can be removed by the file that adds it. That gap is real and it is the largest one
here: all eight boxes measure whether a thing is *operable*, and not one measures whether it
was the *right thing*. It is also where the deck's fourth part lands hardest, and the reason
the gap is worth naming rather than shelving: a system that raises output while lowering the
operator's grasp of what shipped is trading against the one faculty that has to catch the
difference, and eight boxes that all measure operability cannot see that trade happening. It
gets its own spec or it gets written down as a prompt with a reason, which is what rule 12
requires. And it does not import a single number from the
deck. The claims of fifty times faster and eighty per cent of effort come from a paper whose
case study verifies two scenarios against a demonstration login system, with ten simulated
users over five seconds and no coverage figure at all. Its own authors scope everything
except one syntactic translation to human judgement. Repeating those numbers here would be
claiming a result this code has not observed, one level up from the code.

## Decisions

```yaml
decision: The work-item fetch goes whole, and the author writes the problem from scratch
date: 2026-08-08
rationale: ai-eng spec new --ref fetches a work item and uses its title as the document heading and up to twelve hundred characters of its body as the problem statement. Both are prefill, and prefill is the cheapest way to lose the one thing a spec exists to produce, which is an author who understands the problem well enough to state it. A person handed a filled section reviews it, and reviewing is not understanding: the acceleration lands immediately and the comprehension it costs is invisible until somebody has to supervise the result and finds they cannot. That is the deck's fourth part read as a mechanism rather than as advice, and it is the same argument against the title as against the paste, so seed() goes whole rather than being narrowed, which is what the plan's check already enforces and which corrects this spec's earlier sentence saying only the paste goes. No figure travels with this claim: the effect is stated as a shape, because importing a measured percentage from the deck would be repeating a result this code has not observed, which the arithmetic section refuses one paragraph later for the fifty-times and eighty-per-cent numbers.
```
```yaml
decision: Assertion 6 declines to answer instead of passing on an absent chain
date: 2026-08-08
rationale: Assertion 6 is called 'the hash chain is intact and writable' and returns ok when the chain file does not exist, after creating its parent directory. Measured with the path pointed at a file that has never existed, the verdict is ok. It proved a directory is creatable; it proved nothing about writability and there was nothing to be intact. Undecidable already exists for exactly this, prints a question mark and is never counted as a pass. Of the twenty-one assertions run against an empty repository, this is the only one that measured nothing and called it clean, so the fix is one branch and not a family.
```
```yaml
decision: ai-eng accept refuses an unnamed or unjustified acceptance
date: 2026-08-08
rationale: Catching an unsigned acceptance at ship time is late and costs a check; refusing to write one costs three deleted strings and two required flags. The failure moves from the gate at the end to the keyboard at the start, and the artifact that cannot be written cannot be shipped. This is a breaking change to a released flag and is written as one in the changelog, with no shim.
```
```yaml
decision: A shipped spec may not contain a TODO marker
date: 2026-08-08
rationale: The template ships TODO markers in every section and ai-eng accept writes them into the record whenever a person or a reason is omitted, while assertion 16 compares only the expiry date. So an accepted risk with no owner and no justification passes every gate, and the constitution's offer to an auditor is a promise the code does not keep. The same textual condition assertion 19 already runs now also fails a shipped spec containing TODO, and it copies assertion 4's existing idiom rather than inventing one.
```
```yaml
decision: A ticked production-ready box must name a command
date: 2026-08-08
rationale: Assertion 19 searches a shipped spec for an unticked box and never reads a ticked one, so the framework enforces that the question was answered and never that the answer says anything. Three of the eight boxes in this repository's own shipped spec claim a control and name no command, and /ai-ship carries a sentence telling the model to write the command beside every tick with no assertion behind it. The gate now reads the tick, and a ticked box in the production-ready section with nothing in backticks and no 'not applicable' fails. The sentence in /ai-ship is deleted in the same commit, because rule 12 says the prompt goes when the script arrives. The stated ceiling is that a backtick proves a command was named, never that it passed, and that limit is recorded as an accepted risk rather than hidden.
```
<!-- ai-eng decide writes yaml blocks here -->

## Accepted risks

```yaml
id: R-002-01
finding: ticked-box-gate-proves-naming-not-passing
severity: low
accepted_by: the maintainer
accepted: 2026-08-08
expires: 2026-11-06
renewals: 0
justification: The gate that reads a ticked production-ready box proves that a command was named in backticks, never that the command was run or that it passed. A file path in backticks satisfies it. The stronger form would execute what the box names, which needs a command runner inside doctor, a sandbox and a timeout, and would make every spec's assertions run on every doctor invocation. The weaker gate still goes red on this repository's own shipped spec on the day it lands, and on any consumer that ticks the eight untouched template lines, which is the failure that exists today.
follow_up: Revisit when a spec ships a ticked box whose backticked span is a bare filename rather than a command; that is the first observed instance of the gap, and until then the stronger form is speculation.
```
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
