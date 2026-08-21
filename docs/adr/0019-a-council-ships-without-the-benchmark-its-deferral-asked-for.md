---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0019"
title: "A council ships without the benchmark its deferral asked for"
date: "2026-08-21"
spec: "022"
status: "proposed"
supersedes: ""
---

# 0019. A council ships without the benchmark its deferral asked for

## Context and problem statement

Specification 013 deferred a council twice, and both deferrals are still on the page.
`EP-195` — "No council by default" — says a second model "must find a measurable gap, not
manufacture consensus, and no benchmark defines the improvement it would show". `D-013-06`
defers the authority envelope, council roles and budget/TTL, with the trigger `EP-173`
states: an independent autonomous orchestrator that consumes them, plus a test the simple
flow cannot pass.

On 2026-08-20 the repository owner asked for a council anyway, in his words: "si quiero que
esté para que hagamos un llm council entre varios agentes sobre la spec". He asked for
`/ai-challenge` in the same message and for the same reason — that the self-challenge inside
a specification is its own author asking itself questions.

`/ai-council` shipped in commit `8eeb13d1`. This record is written after it rather than
before, and that is a defect in the order of this work: a deferral is reopened by a record,
not by a commit that quietly disagrees with one. Writing it late is the repair available;
pretending the deferral did not exist is not.

## Considered options

1. **Treat the owner's request as satisfying the trigger.** It does not. `EP-173`'s trigger
   is an autonomous orchestrator plus a test the simple flow cannot pass, and neither
   exists. Reading a request as a trigger would make every written trigger decorative.
2. **Refuse until a benchmark exists.** Honest and wrong here. `EP-195`'s reason is that a
   council could manufacture consensus and nobody could tell whether it helped. That reason
   can be answered by design instead of by measurement, and the owner asked for the thing.
3. **Ship it, and make the deferral's stated fear structurally impossible.** What happened.

## Decision outcome

Option 3, with the boundary written where a command can read it.

`EP-195`'s fear is consensus manufactured by a second model. `/ai-council` cannot manufacture
consensus because it has nowhere to put one: its members are lenses rather than opinions, no
lens sees another's answer, there is no vote, no ranking and no field in which the word
approved could be written. A finding that carries no command is deleted before the file is
written, and the count of what was deleted is printed. That is not a benchmark and it is not
offered as one — it removes the failure the deferral named rather than measuring an
improvement the deferral asked for.

`D-013-06` is **not** reopened by this. What shipped is a review skill with no authority: no
authority envelope, no council roles in the coordination sense, no budget and no TTL. Those
stay deferred under their own trigger, which has not fired.

What remains unmet, stated plainly rather than folded away: **there is still no benchmark
that defines the improvement a council shows.** `EP-195` is not closed by this record and
must not be graded as proven on the strength of it. Anybody looking for evidence that a
council improves a specification will not find it in this repository today.

The `supersedes` field is empty because it takes a four-digit record number and the thing
being reopened is a decision identifier inside a specification. The reopening is in this
prose, which is where a reader will look for it.

## Consequences

The good one: the two documents no longer contradict each other silently. Specification 013
says no council by default and this record says why one exists anyway, at what cost, and
which half of the deferral still stands.

The one that gets worse. This is the second record in two days written under the standing
authority of `0016` rather than by a person reading it at the time — `0018` was the first —
and both reopen something a previous specification closed. The scope in `0016` is what
bounds that, and a person reading the pull request is the only thing checking the scope, as
`0016`'s own consequences section already says. Two is not a pattern yet. Three would be.

A smaller one, and it is the reason this record exists at all: `EP-171` moved from
UNFALSIFIABLE to PROVEN in commit `2e352289` because a council shipped, and that grade would
have been read as the deferral having ended. It has not. The gate proves the boundary holds;
it says nothing about whether the council was a good idea.
