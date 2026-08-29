---
id: "048"
slug: handshake-intake-mechanisms
status: draft
date: 2026-08-29
ref: ""
supersedes: ""
---

# Handshake intake mechanisms

## Who this is for, and what it is worth to them

The repository owner, who is the only human in this loop and pays twice for every
misread goal: first in the interview or grill that builds on the wrong framing, then in
the build that ships it. Report 025 measured what an external skill does before the spec
exists and found three mechanisms this tree lacks (`.ai/reports/025-handshake-skill-
harvest.html`, commit `2f06e993`). When this is done, a thirty-question intake that
loses its session at question twelve loses nothing, an owner who cannot recognise their
own idea in the agent's two-sentence read-back stops the cycle before a spec is
written, and an unanswered question becomes a visible line in the record instead of a
silent guess.

## Context and problem

What is true today, verified in this tree on 2026-08-29:

- `ai-spec` step 0 validates intake (goal, constraints, acceptance) and asks capped
  questions when a part is missing (`.agents/skills/ai-spec/SKILL.md:34-39`). The
  mechanism named in spec 037 as B-037-3, `validate_intake`, was built (`fae2ac65`)
  and deleted unused as one of 044's twelve orphan modules (`14eaaeb1`); no
  `def validate_intake` survives in `src/ai_engineering/`. The gate is prose, and
  the spec 037 challenge record had already flagged the loose reading ("Capped is a
  loose reading… not a cited term", `specs/037-…/challenge.md:393`).
- Nothing is written to disk during intake. The scaffold arrives at step 8, after
  evidence, problem, options, recommendation and BDD examples have all been composed
  from conversation memory. A session that dies mid-intake restarts from zero.
- The scaffold never reads the draft back: `spec.py` writes a blank `TEMPLATE` with
  `TODO` placeholders, so a live draft is crash-recovery between interview sessions,
  not a merge source. Any mechanism that keeps one must say who moves its contents
  into the record (the author, by hand) and where the draft goes after (deleted).
- The only legibility check on the agent's understanding is step 2's "state the problem
  in words a non-technical reader can follow" — which scores the problem prose, not the
  owner's idea, and nothing makes the owner confirm the understanding before the record
  is drafted.
- Facts the environment could answer are partly routed already: step 1 says read the
  evidence "before asking anyone" and step 7 caps questions to those that change the
  decision. The gap is inside intake itself: its questions come before step 1, and
  nothing separates a lookup from an ask while the interview is still open.
- The legibility floor is real arithmetic: the `ai-spec` body scores 10.87 fog against
  `contract.SKILL_FOG_CEILING = 11.03` (measured with the gate's own
  `contract.fog(contract.prose(...))`). Fog is an average, not a word budget — adding
  plain prose can lower it (inlining the whole intake reference over HEAD's body
  scores 9.92, green). The ceiling bounds sentence density. The material still lives in a
  `references/` file (the convention `ai-review`, `ai-design` and `ai-report` run)
  for step-0 line economy and maintainability.
- Any rewrite of step 0 moves two stored pins in one file (the verbatim entry at
  `tests/test_contracts.py:575-580`, the digest at `tests/test_contracts.py:1584-1586`)
  plus the skill body. The fog ratchet re-measures live and needs touching only if
  the rewrite crosses the ceiling; the named test selection must include
  `pinned_whole`, because `-k "fog or ai_spec"` deselects the digest pins entirely.

The harm of leaving it unchanged: intake is the one phase where the cheapest error is
also the most expensive to undo — every later stage (grill, council, plan, build)
inherits a misread goal, and rule 12 says a judgement that keeps resolving the same way
should already be machinery.

What came from outside, with its provenance problem: `~/Downloads/handshake/SKILL.md`,
134 lines, no license file, no author. GitHub code search found zero public matches for
its distinctive phrases. Report 025's conclusion stands (and its headline number was
corrected in a follow-up commit: the reproducible measure is 8.50 with the gate's own
prose method, not the 9.17 raw-body figure it first printed): harvest the patterns,
write them in this tree's own voice, do not vendor the file and do not copy its prose.

## Options considered

1. **Fold the three mechanisms into `ai-spec` step 0 in place.** Rewrite step 0 to
   cover: live draft on disk from the first answer (under `.ai/`, with the author
   moving its contents into the scaffold by hand, honoring one-home), the plain-words
   read-back with a pass/fail example pair as the exit gate (and a branch for the
   unattended goal, where no owner is there to confirm), and fact-vs-decision routing
   with unanswered items written visible. Cost: step 0 is a verbatim-pinned sentence;
   every added clause re-measures against a 10.87 body and moves both stored pins.
   Rules out: nothing — the mechanism lands where the cycle already runs it.
2. **A new `ai-handshake` skill that runs before `/ai-spec`.** Cost: a 21st skill
   whose domain the intake (037) and the grill (045) already govern, and two triggers
   that overlap ("I'm thinking about…" fires both `ai-spec` and a handshake skill).
   The catalogue budget does not decide this (20 skills sit at 25% of
   `CATALOG_MAX`); the second-convention risk does — the review criteria forbid it,
   and report 025 applied report 021's precedent ("fusión, no skill nuevo") to this
   exact file. Rules out nothing except honesty about the overlap.
3. **Baseline: keep report 025 as the record and change nothing.** Cost: the three
   mechanisms stay prose in a report nobody executes; intake keeps losing sessions at
   question twelve; the arithmetic in this spec was measured and thrown away.
   Named for why it loses: the research exists precisely to be folded, and a finding
   that never reaches a skill is the false-green of learning — the values call this
   "Learning: turn repeated judgement into checked knowledge".

## Decision

Option 1, detailed in `references/intake.md` (new, beside `ai-spec/SKILL.md`): step 0
grows a self-sufficient pointer and the clauses it must enforce itself — live draft
with a TODO per gap from the first answer, plain-words read-back confirmed by the
owner before scaffolding with an unattended-goal branch, facts looked up and decisions
asked. The other options lose: 2 duplicates a governed domain and puts a second
convention beside the intake that already governs this moment; 3 keeps measured
knowledge out of the executor.

## Challenged once

Strongest realistic case that the decision is wrong: the `references/` split is the
fog gate gaming itself — `contract.prose` strips fences and tables and the ratchet
globs only `*/SKILL.md`, so moving material out hides its bulk from the one formula
that watches (live proof: `ai-report/references/documentation-writer.md` scores 11.70,
above the ceiling, with the suite green). And the read-back gate is contradicted by
its own tree: `/ai-goal` declares "no step of an unattended run waits for input" while
a read-back needing an owner's yes would hang that run — the council executed the two
texts against each other and found the deadlock.

Response: keep the recommendation, repaired on both halves. The reference split is
kept because fog is an average and the pointer in step 0 is the enforceable contract
("read `references/intake.md` first" is a named step an agent can be audited against,
which a hidden appendix cannot be); the honesty about the loophole is this sentence and
the measured 11.70, and the bound is that intake.md itself scores 8.82 by the gate's
own method, re-measured at these bytes. The deadlock is removed by the unattended
branch: no owner, no wait — the
run records the read-back as unconfirmed in the spec's assumptions and carries on,
which keeps `/ai-goal`'s no-wait rule true and the confirmation duty visible.

## Grill

ran: round 1, 2026-08-29 — 20 min

### Q1 — Does the fog arithmetic force the material out of SKILL.md?

**A:** No — the sentence "several sentences of new intake prose… will cross the
ceiling" is WRONG: fog is an average; inlining the whole `references/intake.md`
(8.73 itself) into the HEAD body scores 9.93, below the current 10.87. Command
`uv run python -c "…contract.fog(contract.prose(head+ref))…"` output `10.87 9.93
8.73`. The Context and D-048-02 now say the ceiling bounds sentence density and the
reference exists for line economy. This changed the Context bullet, Option 1's cost,
and D-048-02's rationale.

### Q2 — Do `ai-review` and `ai-verify` run the references/ convention?

**A:** Only `ai-review` does — `ls` shows `ai-verify/` has no `references/`
directory (it borrows ai-review's); the convention's owners are `ai-review`,
`ai-design`, `ai-report`. Corrected in place.

### Q3 — Do step-0 rewrites move "three pins" and force a "four-file commit"?

**A:** No — two stored pins, one file (`tests/test_contracts.py:575-580` and
`1584-1586`); the fog ratchet stores nothing and re-measures live. The landed rewrite
in this tree's worktree moved skill + tests + reference. Corrected; the examples'
command now selects `pinned_whole` too, because `-k "fog or ai_spec"` was measured to
deselect all digest-pin params (council refuted the old claim with the same run).

### Q4 — Is it true that "no text in the corpus separates look-up from ask"?

**A:** Overclaimed — step 1 already says read evidence "before asking anyone" (and
that phrase is itself an attack-pin) and step 7 caps questions. The gap is routing
inside intake, which precedes step 1. The Context bullet now says exactly that.

### Q5 — Is `validate_intake` merely un-built?

**A:** No — built in `fae2ac65` (spec 037), deleted orphaned in `14eaaeb1` (044).
The Context and the mechanization risk now carry 044's lesson: a validator with no
caller gets deleted, so any later mechanization names its caller in the same commit.
The dangling pointer in `specs/new-goal-template.md` was fixed in the build.

### Q6 — Does report 025's 9.17 reproduce?

**A:** No — `fog()` on the raw body without the gate's `prose` stripping; with it,
8.50, and the 21-skill range no longer matches today's 20 (6.66–10.87). The
conclusion (plain enough) survives; the Context records the corrected number and
report 025 got a dated correction rather than a silent rewrite.

### Q7 — Is the 578 anchor right?

**A:** Off by three — the pinned step-0 entry spans `tests/test_contracts.py:575-580`
(578 is mid-entry). Now cited as a range.

### Q8 — Does the "17 passed" example hold?

**A:** Holds: `uv run --with pytest==9.1.1 pytest -q tests/test_contracts.py -k "fog
or ai_spec"` → `17 passed, 157 deselected` on both sides of the rewrite (the diff
touches string literals only). Kept, and superseded by the wider selection in the
examples.

### Q9 — Zero public matches for the handshake file?

**A:** Holds within the tree's limits: a third distinctive phrase (`gh search code
"Every answer updates the draft file on disk"`) returned nothing; 134 lines, no
license/author string. Still `[unsourced]`-grade confirmation, and the risk keeps
that wording.

### Q10 — Did report 021 evaluate this candidate?
**A:** No — 021's precedent is real but it never saw the handshake; 025 applied it.
Option 2's cost now credits 025 for applying 021's precedent, which is the stronger
claim.

## Council

ran: round 1, 2026-08-29 — 31 min
lenses: cost, reversibility, undecidable, trust, example

### Gaps no single lens named

- The read-back gate deadlocks `/ai-goal`: the goal skill forbids waiting for input
  while intake demanded an owner's yes before scaffolding. Fixed in step 0, the
  reference, the Options and the challenge with the unattended branch; the fold-in
  records it here.
- The example and undecidable lenses independently caught the invented heading: the
  scaffold ships twelve fixed sections and none is `## Decisions still open`, and the
  reference I first wrote codified the same lie. Both now name the real section,
  `## Assumptions and unresolved risks`.
- The draft does not merge: `spec.py`'s `TEMPLATE` is blank placeholders with no
  draft-read path, so "the draft moves to `specs/NNN`" was wrong in the reference.
  It now says `.ai/` only, author moves contents by hand, draft deleted after.
- The routable-fact example was UNPROVEN as written (the tree's event record holds
  tool telemetry only, never question text). Rewritten onto an artifact the tree
  owns: the draft file carries a cited `file:line` fact instead of an open TODO.

### Findings cut for carrying no command

- Trust lens: "the reference split is fog-gate gaming" — the mechanism is real (the
  ratchet globs only `SKILL.md`; measured: a reference scoring 11.70 sits green), but
  it arrives with no new command beyond Q1's and its corrective force is already in
  the Challenged-once section. Cut as duplicate of a carried finding, not as noise.

### Findings the cross-read refuted, with the command that refuted them

- "A stale-pin green is impossible under the spec's own example command" — refuted
  with `pytest -q tests/test_contracts.py -k "fog or ai_spec" --collect-only -q`:
  zero `pinned_whole` params collected; the digest pins only fire under the wider
  selection. The example now runs `-k "fog or ai_spec or pinned_whole"` (measured:
  `20 passed`).
- "Option 2 is paid for by `CATALOG_MAX`" — refuted by measurement: 12 444 of 50 000
  (25%) with 20 skills; a 21st description cannot approach the ceiling. Option 2's
  cost is the second-convention risk; the budget claim is gone.

### The two counts

- Gaps that appeared only after the cross-read: **4**
- Findings deleted, for carrying no command or for being refuted: **3**
  (the fold first declared the pass's raw 7 new; `tests/council_counts.py` refused the
  inflated total — three gaps duplicate grill Q1/Q3/Q5 — until the counts matched the
  bullets, so the number here is the recompute's, not the run's)

## Assumptions and unresolved risks

Assumptions (taken as true, not proven here):

- The owner treats a failed read-back as a stop, not a formality. Nothing in the tree
  can force the confirmation to be honest; the record only makes skipping it visible,
  and the unattended branch makes its absence visible too.
- The fog gate keeps scoring only the skill's own body prose (references escape the
  ratchet — measured, and named as a loophole above, not hidden in it).

Unresolved risks:

- Provenance of `~/Downloads/handshake/SKILL.md` is unidentified (no license, zero
  code search hits on three distinctive phrases). Mitigated by design: this spec
  authorized pattern harvest written in this tree's voice only, and no literal copy —
  even the pass/fail example pair was rewritten onto a different domain. The risk
  closes only if the owner names the source.
- The mechanization of intake died once already (built 037, deleted as orphan 044).
  If it is rebuilt, the commit must name its caller or rule 12's audit deletes it
  again; that is a later spec's problem, recorded here so it does not arrive as news.
- NotebookLM deep research on this question (report 025, task `e3e1f305` in notebook
  `bc861818-6ed7-405e-bfc7-fb6357a88f18`) was never harvested; if it contradicts any
  external claim above, the citation list in report 025 is what this spec rests on.

## Examples somebody can check

**The session that dies.** Given an `/ai-spec` run whose intake draft under `.ai/`
carries answers and open `TODO` lines, When the session ends, Then the draft is still
on disk and the next session continues from it rather than from zero — checked by
`ls .ai/intake-*.md && grep -c TODO .ai/intake-*.md` returning the file and a
non-zero TODO count while gaps remain. (Before this spec: nothing on disk; the next
session restarts at one.)

**The read-back that fails.** Given an owner who answers "that is not what I meant"
to the two-sentence plain-words read-back, When `/ai-spec` continues, Then no
`ai-eng spec new` scaffold exists — `ls specs/` gains no directory until the owner
confirms, and the next question targets the correction.

**The unattended goal.** Given `/ai-goal` with no owner at the keyboard, When intake
ends, Then the run does not wait: it records "read-back unconfirmed" in the spec's
`## Assumptions and unresolved risks` and the cycle proceeds — grepping that section
in a goal-run spec returns the line.

**The routable fact.** Given an intake gap the repository can answer ("does X already
exist?"), When the draft is updated after that gap closes, Then the draft carries the
answer as a cited `file:line` fact and not as a `TODO` question to the owner —
`grep TODO` over the draft returns decisions only, never lookups the tree could close.

**The gate arithmetic.** Given the step-0 rewrite lands, When
`uv run --with pytest==9.1.1 pytest -q tests/test_contracts.py -k "fog or ai_spec or
pinned_whole"` runs, Then it exits 0 with `20 passed` — both stored pins and the
whole-file digest move in the same commit as the skill body, and the selection that
proves it names all three (`17 passed` was the old selection's count and collected
zero digest pins, which is exactly what the council refuted).

## Decisions

<!-- One `**D-NNN-NN — <the decision>**` per line, each with a `**Rationale:**` under it.
     Prefix a line with `- [X]` to claim the decision earns promotion: it constrains
     specs that do not exist yet, and `ai-eng decide` promotes only marked lines.
     `ai-eng decide` does not write here: it writes a record under docs/adr/. -->

**D-048-01 — Fold the handshake mechanisms into `ai-spec` step 0; no new skill.**
**Rationale:** intake is already a governed step of the governing skill; a parallel
skill is a second convention beside an existing one, and report 025 applied report
021's precedent to this exact file: fusion into the verb that owns the moment.

**D-048-02 — The mechanism prose lives in `references/intake.md`, pointed to by a
self-sufficient clause in step 0.**
**Rationale:** not the fog ceiling (grill Q1 measured the average moves the other way)
but line economy and auditability: a named "read X first" step is a step an audit can
catch an agent skipping; an inline appendix nobody is told to open is not. The
loophole the split leans on (references escape the ratchet) is named in
`## Challenged once` rather than relied on silently.

- [X] **D-048-03 — Harvest patterns, never the external file's prose.**
**Rationale:** the source is unlicensed and untraceable to an author; the wheel carries
MIT-harvested text only with attribution (report 021's NOTICE rule), and here there is
nothing to attribute — writing it in this tree's voice (including the example pair,
rebuilt on a different domain) is the only clean path.

- [X] **D-048-04 — The read-back gate carries an unattended branch.**
**Rationale:** the council executed the intake gate against `/ai-goal`'s no-wait rule
and found the deadlock; a confirmation that cannot happen headless must be recorded as
unconfirmed, not waited for, so the same clause that binds the attended flow keeps the
headless flow honest by writing its absence down.

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
