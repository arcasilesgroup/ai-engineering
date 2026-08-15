---
id: "004"
slug: solution-intent-home
status: superseded
date: 2026-08-08
ref: ""
supersedes: ""
---

# Where the Solution Intent work belongs, and what it would take to sell it

## Context and problem

`solution-intents` is a second repository. It holds sixteen governed documents for one
organisation, one per project, each saying what a system is for, who it hurts when it is
missing, how you would know it works, what was decided and at what cost, what is still
waiting on a person, and what nobody verified. Around them sit eighty-eight decision
records, sixteen changelogs, sixteen sidecar files carrying machine-readable state, and a
two-layer schema that seals the header of every document. Six scripts and a hundred and
seven tests hold the whole thing to its shape on every push. A site built from those
documents is already live behind a login: it is not a plan, it is in production, and a
second session was redesigning it while this spec was being written.

The question was whether that work should become a skill here — with its scripts, its
determinism and its guards — and if not, where it belongs. Behind it sat a larger one: the
intention to eventually offer the whole thing to everybody.

### What that repository already proves

Three facts settle most of this, and none of them is an opinion.

**It carries two hundred and eleven files of this framework, and none of them runs.**
Version 0.12.3 is installed there: nine command-line tools, fifty-six hooks, fifty-four
per-language override files, nineteen reference documents, fifteen runbooks, three policy
files, plus fifty-seven mirrored skills and nineteen mirrored agents and a generated
instruction file two hundred and ninety-four lines long that points at two documents which
do not exist. Its two workflows invoke six scripts, a secret scanner and a static analyser.
Not one line of the install participates in the work or in the checks. That repository's own
constitution already sorts those files into a column marked Framework and everything that
does the work into a column marked Team. This is the five-hundred-and-twenty-eight-file
failure that produced this rewrite, observed in the wild, in the repository that would be
the first customer of any new skill.

**The experiment has already been run, at the shortest distance it can be run at.** Three
skills live inside that repository: `ai-si`, `ai-si-audit`, `ai-si-sync`. They describe how
to write a Solution Intent. They describe the third version of the document mould — fourteen
sections, a requirements-clause syntax, three diagrams, a changelog inside the document, and
a block of machine state sitting under the header. The corpus is on the fifth version: six
sections, a two-thousand-token ceiling on the whole file, and that block moved out to a
separate file. The skills are wrong about every one of those. They rotted with the same
author, the same reviewer, the same repository and nothing between them and the original
except the intention to keep them in step. A model that reads them produces a document the
repository's own validator rejects.

**A control written never to fail stopped looking, and reported clean weeks.** The weekly
freshness watcher compares when a document was last checked against the code with when that
code was last pushed, and opens an issue when the gap is wide. It reads the check date by
searching the document body for the block that the fifth mould moved out. Zero of sixteen
documents still contain it. So every document resolves to "cannot measure", the drift count
is permanently zero, and the issue has not been raised once. The state file it commits as
proof of life is the last run before the mould changed: it still names two documents that
were retired and is missing three that are live. The watcher's empty answer and its
all-clear answer print the same thing.

### And what it has not earned yet

Of the sixteen documents, none is approved or done. Four carry any approved version at all.
Nine are deployed without one, under a rule that is advisory by choice. Seven carry a
hand-authored field that disagrees with the value computed from the same document, warned
about and never enforced. The prose budget gate runs advisory although the comment beside
it in the pipeline states the condition for making it binding and that condition has already
been met.

## Options considered

1. **Ship a skill here that authors and audits Solution Intents, with its scripts and its
   guards.** It is what was asked for, and it is the fastest route to "offer it to
   everybody". Rejected. A skill that describes another repository's document mould is the
   three rotted skills again, except now on a release train, landing in every project on
   every machine that installs this framework, wrong the moment the mould moves to a sixth
   version, in repositories whose owners never adopted the mould and never asked for it.
   The machinery cannot come either: it is roughly eleven hundred lines of JavaScript in a
   package that is standard-library Python with a hard line ceiling, and half of it names
   things — a work-tracker's three endpoints, one company's divisions, a prioritisation
   formula — that are content, not mechanism. And the deciding objection is ownership: it
   would place a mould, a schema and six scripts inside somebody else's repository, which is
   the single act this framework's constitution forbids.

2. **Extract the generic half of both repositories into a shared library and depend on it
   from all three.** It looks like the clean answer and it is the expensive one. The generic
   half of the site is about seven hundred lines whose parser is coupled to the fifth
   mould's tag names, so "generic" already means "reusable if you adopt the mould". The
   schema's first layer is generated from a file in a third repository. Extracting it now
   forks a surface that is live and mid-redesign, to serve zero users, and creates the
   second copy that this framework exists to delete.

3. **Nothing crosses. The shapes of the gates travel outward, the estate earns its own
   gates first, and the product question is answered with what it would take rather than
   with a package.** Chosen.

## Decision

**No skill, verb, assertion or template for Solution Intents enters this framework, and the
line ceiling does not move for it.** The mould, the two-layer schema, the six scripts, the
sidecar and the site all stay where they are. The three rotted skills are hard-deleted
there, with no replacement shipped from here — instructions that produce a document the
validator rejects are worse than no instructions, because a model obeys them. The two
hundred and eleven installed framework files and the mirrored skills and agents are deleted
there too: nothing invokes them, that repository's own constitution already classifies them
as not its work, and `ai-eng doctor` assertion 18 returns this verdict today without being
asked.

**What crosses is the shape of a gate, and not one line of code.** Three shapes, each
already working here, each copyable in an afternoon, each costing this framework nothing:

- Assertion 7's rule, that a control which has not fired is not a control. Applied to the
  blind watcher it becomes a printed count of how many documents were actually measured
  against how many exist, and a non-zero exit when the first number is below the second.
  A threshold on the drift count would not have caught this; a count of the denominator
  would have caught it on day one. That is the whole difference, and it is four lines.
- `Undecidable`'s rule, that an answer of *cannot tell* is never a pass. The watcher already
  prints "not measurable" honestly, in Spanish, and even says in its own output that this
  does not mean the documents are up to date — and then exits zero. The instrument was
  honest. Nothing consumed its honesty. That is the missing half.
- Assertion 19's shape, a textual condition that either holds or does not and needs no
  judgement to evaluate. It is what the advisory gates over there are waiting to become:
  deployed-without-approval, the prose budget, a decision pointer that resolves to a file
  that exists.

**On offering it to everybody: today it ships nothing, and that is the correct answer.**
The only shape it could take is a repository a team forks once. A fork transfers ownership
completely on the first day — their bytes, their divergence, no upstream that can rot them.
An install transfers the files and keeps the ownership, which is the five-hundred-and-
twenty-eight-file failure restated as a distribution model. So it is not a skill, not a
command, not an installer, and not a hosted service: a hosted renderer for a format with one
user is a company with availability promises and billing, staffed by the person who is
currently the sole author of all sixteen documents.

Four things have to be true before that fork is worth offering, and the first is the one
that matters. **The estate has to be able to show its own gates going red.** A governance
product whose own corpus has no approved document, nine deployments without approval under
an advisory rule, a prose gate still advisory past its own written flip date, and a watcher
that has measured nothing since the mould changed, is selling the green nobody earned —
which is the exact failure this framework was built to cure, and the first thing a buyer
checks. Then: the dead weight goes, so a forker does not inherit it. Then the document
contract has to be showable without shipping the private site, since the contract is the
product and the schema's authority currently lives behind a login. Then the mould is
de-organised in place rather than forked, because a fork is two copies drifting from day
one. And last, the thing that turns all of it from packaging into a product: a corpus
nobody here owns adopts the mould and survives one version bump of it.

The honest sentence, when there is something to sell: *your specs merge under the same rules
as your code — a decision document that misses its budget, its schema or its acceptance
criteria does not merge*. There is no format-agnostic path to it. The first outside user
adopts the mould or gets nothing.

One thing to say plainly to any buyer, because the constitution requires it: the buyer most
drawn to that sentence is a regulated organisation that has lost an audit, and what they
want is signed, timestamped, write-once evidence. This estate produces none. Its evidence
story is a secret scanner in a pipeline.

Rule 10, one line each, because a refusal has to justify itself the same way an addition
does:
**KISS** — the cure for a blind watcher is counting its denominator in four lines, not a
schema for the sidecar it failed to read.
**YAGNI** — a library extracted from the generic halves of three repositories serves zero
users today, and the trigger for revisiting it is written down rather than assumed.
**DRY** — a value stated twice drifts and the drifting copy is always the one nobody runs,
which is a hand-authored field disagreeing with its computed value on seven of sixteen
documents, and is the same defect this framework carries in its own always-loaded doctrine.
**SOLID** — two hundred and eleven installed files that nothing imports are not a
dependency, and a repository that has to keep a column in its constitution to explain them
is paying to describe something it does not use.
**TDD** — every task over there names a command that fails against the corpus as it stands
today; none of them is a check that has to wait for something to be built before it can go
red.
**Clean Code** — instructions describing a mould that no longer exists are deleted rather
than updated, because a model obeys them and produces a document its own validator rejects.
**Clean Architecture** — the direction of the dependency is the entire ruling: the shape of
a gate travels outward, no code travels inward, and no file of ours lands in anybody's tree.

The context-engineering guidance for this model generation says the fix for an agent doing
the wrong thing is a better interface rather than another sentence of rules. The three
rotted skills are that sentence, written by people who owned the mould, inside the
repository that owned it, and they were still wrong within one version. That is the whole
argument against shipping a fourth one from further away.

## Decisions

```yaml
adr: 0004
title: No document mould from another repository enters this framework
```
```yaml
decision: The three ai-si skills are hard-deleted there, with no replacement shipped from here
date: 2026-08-08
rationale: They describe the third version of a mould whose corpus is on the fifth: fourteen sections, a requirements-clause syntax, three diagrams, an in-document changelog and a machine-state block that moved out to a separate file. A model that obeys them produces a document the repository's own validator rejects, so instructions that are wrong are worse than no instructions. Hard delete, said in the changelog, no shim and no replacement from this side, because a replacement shipped from here is the same rot at a greater distance.
```
```yaml
decision: The estate earns its own gates before it is offered to anyone
date: 2026-08-08
rationale: None of the sixteen documents is approved, nine are deployed without an approval under a rule that is advisory by choice, seven carry a hand-authored field that disagrees with the computed one, and the prose gate is still advisory past the date its own comment set for making it binding. A governance product that cannot show its own gates going red is selling the green nobody earned, which is the failure this framework exists to cure and the first thing a buyer checks.
```
```yaml
decision: Offering this to anybody ships a fork, never an install
date: 2026-08-08
rationale: A fork transfers ownership completely on the first day: their bytes, their divergence, no upstream that can rot them. An install transfers the files and keeps the ownership, which is the five hundred and twenty eight file failure restated as a distribution model. So the shape is a repository a team forks once, and never a skill, a command, an installer or a hosted service. A hosted renderer for a format with one user is a company with availability promises and billing, staffed by the sole author of all sixteen documents.
```
```yaml
decision: The framework install that repository never runs is deleted there
date: 2026-08-08
rationale: Two hundred and eleven files of this framework sit in that repository and nothing invokes them: nine command-line tools, fifty-six hooks, fifty-four per-language override files, nineteen reference documents, fifteen runbooks, three policy files, fifty-seven mirrored skills, nineteen mirrored agents and a generated instruction file that points at two documents which do not exist, and its two workflows name none of those paths. Its own constitution already keeps a column marked Framework to explain them, and `ai-eng doctor` assertion 18 returns that verdict there today without being asked. The deletion comes before anything is offered to anybody, because a forker inherits whatever is in the tree and forms their first impression from it. It is that repository's commit, not this one's.
```
```yaml
decision: No generic half of these two repositories is extracted into a shared library
date: 2026-08-08
rationale: The generic half of the site is about seven hundred lines whose parser is coupled to the fifth mould's tag names, so generic already means reusable if you adopt the mould, and the schema's first layer is generated from a file in a third repository. Extracting it now forks a surface that is live and mid-redesign in another session, to serve zero users, and creates the second copy this framework exists to delete. The trigger for revisiting it is written down rather than assumed: a corpus nobody here owns adopts that mould and survives one version bump of it. Not before.
```
<!-- ai-eng decide writes yaml blocks here -->

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command.

- [x] CI/CD — `just check`, run by `.github/workflows/check.yml` on every push; this spec adds one file under `docs/adr/` and no product line, so there is nothing here to build and nothing to deploy
- [x] Logs — not applicable: no code is added, and `ai-eng digest` still reads the one JSON line every verb already emitted
- [x] Traces — not applicable, and that is the rule: one process, no second hop, no trace
- [x] Errors — not applicable: nothing new executes, so there is no new uncaught exception, and `cli.main` is untouched by this spec
- [x] Health and data age — `ai-eng doctor` assertion 19 reads this list the moment the spec is shipped, and `ai-eng decide --list` prints the ADR with its status, which is the only state this spec has and the only thing about it that can go stale
- [x] External check — `ai-eng doctor` run in `solution-intents`: assertion 18 counts the framework files committed there without being told what to look for, which is the finding this refusal rests on. What it cannot check is the deletions in the plan — they are that repository's commits, in its reviews, and nothing here can see them
- [x] Second path — the counts this spec publishes were read there by two routes that share no line of code, `git ls-files` and that assertion, and this repository republishes none of them: the decision is stated once, in the ADR, and this spec holds a pointer rather than a copy
- [x] Security — `just security`: gitleaks, semgrep and trivy on every push, over a change that adds no dependency, no code and no network call
