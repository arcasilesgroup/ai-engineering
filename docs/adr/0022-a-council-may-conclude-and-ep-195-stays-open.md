---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0022"
title: "A council may conclude, and EP-195 stays open"
date: "2026-08-21"
spec: "023"
status: "accepted"
authority_role: "repository owner"
approval_ref: "ae523990"
approved_at: "2026-08-21T12:43:47Z"
supersedes: "0019"
---

# 0022. A council may conclude, and EP-195 stays open

## Context and problem statement

`0019` shipped a council whose defining property is that it cannot conclude. Its Decision
outcome says so in the words a reader would search for: the members are lenses rather than
opinions, no lens sees another's answer, "there is no vote, no ranking and no field in which
the word approved could be written." That was the answer to `EP-195`'s stated fear — a second
model manufacturing consensus — and it answered that fear by design because no benchmark
existed to answer it by measurement.

On 2026-08-21 the repository owner asked for the LLM Council method, whose chairman produces a
verdict and a recommendation. Told that `0019` decides the opposite, he answered "pero debemos
hacerlo". Specification 023 is that change and `0021` approves it at exact digests.

A deferral is reopened by a record and not by a commit that quietly disagrees with one. That
sentence is `0019`'s, written about itself, and this record is what it asked for.

## Considered options

1. **Edit `0019`.** Refused. It is `accepted`, and a record that changes its mind in place
   leaves a reader unable to see that anybody ever thought otherwise. The schema's own
   transition graph allows `accepted → superseded` and allows nothing else out of `accepted`,
   which is that refusal expressed as code.

2. **Supersede `0019` entirely, and treat its fear as answered.** Refused, and this is the
   option worth writing down because it is the tempting one. `0019`'s fear was consensus
   manufactured by a second model, and the research gathered for specification 023 —
   `.ai/reports/003-council-peer-review-evidence.html` — says that fear was well founded.
   Multi-agent debate flips correct answers to wrong ones at rates between 22.8% and 71.0%
   under a unanimous wrong majority; 57% to 77% of stance changes attributable to conformity
   go from correct to incorrect; and the only head-to-head measurement of the exact shape being
   imported puts it *below* the best single reader. Declaring the fear answered because the
   owner asked for the feature would be the record lying about what it knows.

3. **Supersede `0019` on the boundary it drew, and keep the half it left open, open.** What
   this record does.

## Decision outcome

Option 3.

**What changes.** A council may now conclude. Its chairman writes a verdict, the disagreements,
the blind spots, a recommendation and one first step. `0019`'s sentence — "no field in which the
word approved could be written" — is replaced by a narrower one that comes from
`CONSTITUTION.md:53` rather than from doctrine: models "may investigate, propose and review;
they never grant authority or accept risk." Recommending is proposing. Approving is granting.
The test that enforced the old boundary was, measured by executing it, both stricter than the
Constitution in one direction and looser in the other — it refused the word `recommendation`
while failing to detect a bare `approved`, a bare `PASS` or an accepted risk at all. Task 4 of
specification 023's plan is that repair, and it is the first time three of those four are caught.

**What does not change, and this is the half that matters.** `EP-195` is **not closed by this
record.** Anybody grading it PROVEN on the strength of this document is doing what `0019`
warned about when `EP-171` moved to PROVEN because a council shipped. Two further rows record
`EP-195` elsewhere — `specs/013-origin-first-coordination/spec.md:194` as `NON-GOAL` and
`docs/requirements.toml:1445` as `NO-EVIDENCE`, whose evidence command `tests/ledger_run.py`
executes — and **both stay exactly as they are.** They move when there is a series to move them
on, and not before.

**What is different from `0019`, factually.** `0019` closes by saying no benchmark defines the
improvement a council shows. One now exists in instrument form: specification 023's `D-023-05`
makes a script count, per run, how many findings appeared only after the cross-read and how many
were deleted for carrying no command or for being refuted. It has been run once, on
specification 023 itself: five independent lenses produced 28 findings, the cross-read added 11
gaps none of them had named and refuted 3, each refutation carrying a command that was executed.
That is one run, one document, one model family. It is evidence that the instrument reads
something. It is not a benchmark and this record does not offer it as one.

**And the design keeps the part of `0019` that was load-bearing.** The cross-read does not rank.
Ranking is the mechanism every negative result in the evidence measures, and it is the mechanism
the one head-to-head isolates as the loser. What round two asks for is a refutation carrying a
command, which is an artifact and not an opinion, and a refutation that carries no command is
discarded exactly as a finding without one already is.

## Consequences

The good one: the two documents no longer contradict each other silently, and the boundary that
survives is one a command can read rather than one a paragraph asserts.

The one that gets worse, stated as plainly as `0019` stated its own. **This is the fourth record
in two days that reopens something an earlier record closed** — `0018`, `0019`, `0021` and this.
`0019`'s consequences section says "two is not a pattern yet. Three would be." Four is. What is
different about the last two is that a person made the call rather than a standing grant; what is
not different is the direction, which has been the same every time: each record loosens something
an earlier one tightened. Nothing in this repository counts that. A human reading the pull
request is the only control on it, and this paragraph is the only place the count is written down.

A second one, smaller and concrete: after this lands, a council file may contain the word
`Verdict:` and the word `Recommendation:`, and consumer repositories that pinned an earlier
version will see a council that concludes where theirs does not. That is a behaviour change in a
shipped wheel and `CHANGELOG.md` carries it.
