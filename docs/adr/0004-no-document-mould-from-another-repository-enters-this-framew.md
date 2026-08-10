---
status: proposed
date: 2026-08-10
spec: 004-solution-intent-home
supersedes: ""
---

# 0004. No document mould from another repository enters this framework

## Context and problem statement

A second repository holds sixteen governed documents, one per project, each saying what a
system is for, who it hurts when it is missing, what was decided and at what cost, and what
nobody has verified. Around them sit eighty-eight decision records, a two-layer schema, six
scripts and a hundred and seven tests, and a site built from them that is already in
production. The question put to this framework was whether that work should become a skill
here, with its scripts and its guards, and behind it sat the intention to eventually offer
the whole thing to everybody.

Three facts from that repository settle it, and none of them is an opinion. Every count
below was measured there on 2026-08-08, by `git ls-files` and by `ai-eng doctor` assertion
18, and nothing in this tree can see them or re-check them.

Two hundred and eleven files of this framework are installed there and not one of them
runs. Version 0.12.3: nine command-line tools, fifty-six hooks, fifty-four per-language
override files, nineteen reference documents, fifteen runbooks, three policy files, plus
fifty-seven mirrored skills, nineteen mirrored agents and a generated instruction file two
hundred and ninety-four lines long that points at two documents which do not exist. Its two
workflows invoke six scripts, a secret scanner and a static analyser, and name none of those
paths. That repository's own constitution keeps a column marked Framework to explain them.
This is the five-hundred-and-twenty-eight-file failure that produced this rewrite, observed
in the repository that would have been the first customer of any new skill.

The experiment has already been run, at the shortest distance it can be run at. Three skills
live inside that repository — `ai-si`, `ai-si-audit`, `ai-si-sync` — and they describe the
third version of its document mould: fourteen sections, a requirements-clause syntax, three
diagrams, a changelog inside the document and a block of machine state under the header. The
corpus is on the fifth version: six sections, a two-thousand-token ceiling on the whole file,
and that block moved out to a separate file. They rotted with the same author, the same
reviewer and the same repository between them and the original, and a model that obeys them
produces a document that repository's own validator rejects.

The control written never to fail stopped looking and reported clean weeks. The freshness
watcher reads each document's check date out of the document body, where the fifth mould no
longer puts it. Zero of sixteen documents resolve, so the drift count is permanently zero
and the issue it exists to open has never been raised once. Its empty answer and its
all-clear answer print the same thing.

## Considered options

1. **Ship a skill here that authors and audits those documents, with its scripts and its
   guards.** It is what was asked for and the fastest route to offering it to everybody. It
   is also the three rotted skills again, on a release train, landing in every project on
   every machine that installs this framework, wrong the moment the mould moves to a sixth
   version, in repositories whose owners never adopted it. The machinery cannot travel
   either: roughly eleven hundred lines of JavaScript into a standard-library Python package
   with a hard line ceiling, half of it naming one company's divisions and one work
   tracker's endpoints, which is content and not mechanism.
2. **Extract the generic half of both repositories into a shared library and depend on it
   from both.** The generic half is coupled to the fifth mould's tag names, so "generic"
   already means "reusable if you adopt the mould", and the schema's first layer is generated
   from a file in a third repository. Extracting it now forks a surface that is live and
   mid-redesign, to serve zero users, and creates the second copy this framework exists to
   delete.
3. **Nothing crosses. The shape of a gate travels outward, in prose, and no code travels in
   either direction.**

## Decision outcome

Option 3.

The rule, stated so it applies to specs nobody has written yet: **a document mould owned by
another repository never enters this framework as a skill, a verb, an assertion or a
template, and the line ceiling does not move for one.** The test for "mould" is ownership,
and it is decided by who breaks when the other side moves: if a version bump of somebody
else's document format can make a file in this tree wrong, it is a mould, and it stays where
its owner is.

What may cross is the shape of a gate, as prose somebody re-implements in their own
language, and never a file of ours in anybody's tree. Three shapes crossed with this
decision and each already works here: assertion 7's rule, that a control which has never
fired is not a control, which turns the blind watcher into a printed count of documents
measured against documents that exist; `Undecidable`'s rule, that *cannot tell* is never a
pass, which is the half that watcher was missing while printing the truth and exiting zero;
and assertion 19's shape, a textual condition that needs no judgement to evaluate, which is
what every advisory gate over there is waiting to become.

## Consequences

Better: the next person who arrives with a document format and a good reason gets the answer
and the reasoning without having to find the spec it was argued in. This framework stays a
mechanism rather than a library of somebody else's content, so nothing here goes stale when
a format somewhere else moves. And no file of ours lands in a tree we do not own, which is
the one act this project's constitution forbids.

Worse, and worth saying rather than discovering: the request was real and this answers it
with nothing shippable. Somebody who wants documents governed the way this framework governs
code copies three shapes and writes the code themselves, and a second team pays that cost
again from scratch. This decision also cures none of the rot it is founded on — the three
skills stay wrong until their owner deletes them, and nothing here can reach them.

The answer changes when a corpus nobody here owns adopts that mould and survives one version
bump of it. Until then option 2 stays rejected, and this file is allowed to change only by
superseding it.
