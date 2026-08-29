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
  mechanism named in spec 037 as B-037-3, `validate_intake`, does not exist in
  `src/ai_engineering/` — a workspace search for its definition returns nothing. The
  gate is prose, and the spec 037 challenge record already flagged the loose reading
  ("Capped is a loose reading… not a cited term", `specs/037-…/challenge.md:393`).
- Nothing is written to disk during intake. The scaffold arrives at step 8, after
  evidence, problem, options, recommendation and BDD examples have all been composed
  from conversation memory. A session that dies mid-intake restarts from zero.
- The only legibility check on the agent's understanding is step 2's "state the problem
  in words a non-technical reader can follow" — which scores the problem prose, not the
  owner's idea, and nothing makes the owner confirm the understanding before the record
  is drafted.
- Facts the environment could answer are not routed away from the owner: no text in the
  corpus separates "look it up" from "ask", beyond the harness's tool policy.
- The harvest ceiling is real arithmetic: the `ai-spec` body scores 10.87 fog against
  `contract.SKILL_FOG_CEILING = 11.03` (measured with the gate's own
  `contract.fog(contract.prose(...))`). Headroom is 0.16. Several sentences of new
  intake prose added to `SKILL.md` in place will cross the ceiling; the edit either
  stays tiny or the material lives in a `references/` file, the convention
  `ai-review` and `ai-verify` already use.
- Any rewrite of step 0 moves three pins in the same commit: the verbatim tuple entry in
  `tests/test_contracts.py:578` (`AI_SPEC_SECTIONS["Procedure"]`), the whole-file sha256
  in `GOVERNING_SKILL_TEXT` (`tests/test_contracts.py:1573-1588`), and the fog ratchet.

The harm of leaving it unchanged: intake is the one phase where the cheapest error is
also the most expensive to undo — every later stage (grill, council, plan, build)
inherits a misread goal, and rule 12 says a judgement that keeps resolving the same way
should already be machinery.

What came from outside, with its provenance problem: `~/Downloads/handshake/SKILL.md`,
134 lines, no license file, no author. GitHub code search found zero public matches for
its distinctive phrases. Report 025's conclusion stands: harvest the patterns, write
them in this tree's own voice, do not vendor the file and do not copy its prose.

## Options considered

1. **Fold the three mechanisms into `ai-spec` step 0 in place.** Rewrite step 0 to
   cover: live draft on disk from the first answer (into `specs/NNN` after
   `ai-eng spec new`, or `.ai/` before it, honoring one-home), the plain-words read-back
   with a pass/fail example pair as the exit gate, and fact-vs-decision routing with
   unanswered items written visible. Cost: step 0 grows several sentences in a file at
   0.16 fog headroom, so most of it must be compressed to a pointer. Rules out: any
   `references/` file (the material stays inline and must fit). Risk: the pins fight
   back hard — every word of step 0 is verbatim-pinned, and the whole-file digest makes
   this a three-file commit minimum.
2. **A new `ai-handshake` skill that runs before `/ai-spec`.** Cost: a 21st skill whose
   domain the intake (037) and the grill (045) already govern, two triggers that
   overlap ("I'm thinking about…" fires both `ai-spec` and a handshake skill), and the
   catalogue budget (`CATALOG_MAX`) pays the duplicate description. Risk: it is the
   second convention beside an existing one, which the review criteria forbid; report
   021 set the precedent for exactly this candidate class — fusion, not a new skill.
   Rules out nothing except honesty about the overlap.
3. **Baseline: keep report 025 as the record and change nothing.** Cost: the three
   mechanisms stay prose in a report nobody executes; intake keeps losing sessions at
   question twelve; the fog arithmetic in this spec was measured and thrown away.
   Named for why it loses: the research exists precisely to be folded, and a finding
   that never reaches a skill is the false-green of learning — the values call this
   "Learning: turn repeated judgement into checked knowledge".

## Decision

Option 1, with one amendment drawn from option 3's cost analysis: the read-back
pass/fail example pair and the gap-list order live in a new `references/intake.md`
beside `ai-spec/SKILL.md` (the `ai-review` convention), and step 0 grows only a
self-sufficient pointer plus three short clauses — live draft from the first answer,
plain-words read-back confirmed by the owner before drafting, facts looked up and
decisions asked. The other options lose: 2 duplicates a governed domain and pays the
catalogue for it; 3 keeps measured knowledge out of the executor.

## Challenged once

Strongest realistic case that the decision is wrong: the amendment is the fog gate
gaming itself — `contract.prose` strips fenced blocks and tables, so moving material to
a `references/` file is structurally the trick that makes a harder skill score as
readable. The rule 12 test applies too: the read-back is a judgement ("can a child get
it") that will resolve differently every time, so prose is right — but the gate's own
docstring says a formula cannot tell whether anybody understood, and the reference file
hides the bulk from the one formula that does watch.

Response: keep the recommendation, revise its confidence. The hedge is a bound, not a
vibe: `references/intake.md` must itself stay fog-cheap and the build records its
measured score in the plan; the pointer in step 0 must be self-sufficient ("read
`references/intake.md` before the first question"), so an agent who skips the file
skips a named step, not a hidden one. If a future audit finds the reference grew past
what the skill could carry inline, that is the signal the material was skill-body
material all along.

## Grill

TODO: when a grill round lands, replace this prompt with its declaration on its own
line — `ran: round <n>, <ISO date> — <n> min` — then one `### Q` per question with its
`**A:**` answer beside it, and what it changed. A round that attacked and found nothing
says `nothing checkable failed`. While this prompt stands undeclared, the critic step
reads the grill as not run.

## Council

TODO: when the council pass lands, replace this prompt with its declaration on its own
line — `ran: round <n>, <ISO date> — <n> min` — and name the lenses that read:
`lenses: cost, reversibility, undecidable, trust, example`. The shape below is what the
critic step reads — top-level bullets only, each heading carrying bullets or a literal
`none` line, every finding and every refutation carrying a command. The pass may
conclude; it may not approve.

### Gaps no single lens named

### Findings cut for carrying no command

### Findings the cross-read refuted, with the command that refuted them

### The two counts

- Gaps that appeared only after the cross-read: **N**
- Findings deleted, for carrying no command or for being refuted: **N**

## Assumptions and unresolved risks

Assumptions (taken as true, not proven here):

- The owner treats a failed read-back as a stop, not a formality. Nothing in the tree
  can force the confirmation to be honest; the record only makes skipping it visible.
- The fog gate keeps scoring only the skill's own body prose. Verified today by reading
  the readability tests and measuring with `contract.prose`; assumed stable because it
  is pinned there.

Unresolved risks:

- Provenance of `~/Downloads/handshake/SKILL.md` is unidentified (no license, zero code
  search hits on its phrases). Mitigated by design: this spec authorizes pattern
  harvest written in this tree's voice only, and no literal copy. The risk closes only
  if the owner names the source; if it turns out MIT, a NOTICE can be added later, and
  nothing in the plan depends on that.
- The three pins (`AI_SPEC_SECTIONS` verbatim step-0 text, `GOVERNING_SKILL_TEXT`
  digest, fog ratchet) make a stale-pin green impossible but a four-file commit
  mandatory; the plan must name all four or the gate goes red at the worst moment.
- Intake is still prose-gated: no `validate_intake` exists. Mechanizing it (a script
  that refuses a spec whose record lacks the read-back confirmation line) is allowed to
  be a later spec; rule 12 says it becomes code when the judgement resolves the same
  way a third time, and this spec is the first written attempt.
- NotebookLM deep research on this question (report 025, task `e3e1f305` in notebook
  `bc861818-6ed7-405e-bfc7-fb6357a88f18`) was never harvested; if it contradicts any
  external claim above, the citation list in report 025 is what this spec rests on.

## Examples somebody can check

**The session that dies.** Given an `/ai-spec` run where intake has reached question
twelve of a long interview, When the session ends without a commit, Then a draft file
named in the transcript exists under `specs/NNN-…/` or `.ai/` carrying the answered
parts, a `TODO` per open gap, and no invented answers — checked by
`git status --porcelain specs/` listing the draft as untracked-or-committed before the
next session starts. (Before: nothing on disk; the next session restarts at one.)

**The read-back that fails.** Given an owner who answers "that is not what I meant" to
the two-sentence plain-words read-back, When `/ai-spec` continues, Then no `ai-eng spec
new` scaffold is created and the next question targets the correction, not the next gap
— observable because `ls specs/` gains no directory until the owner confirms.

**The routable fact.** Given an intake question the repository can answer ("does X
already exist?"), When the agent is about to ask the owner, Then the question is absent
from the transcript and replaced by a cited `file:line` found by search — the denial
path is the owner being asked about something in plain sight, which the review of the
session catches.

**The undecidable path.** Given an unanswered decision at early exit, When the record
is written, Then it appears under `## Decisions still open` with a recommended default
or under unresolved risks with its owner named; silence is the only wrong outcome, so
the check is that the section is non-empty whenever the interview ended without full
confirmation.

**The gate arithmetic.** Given the step-0 rewrite lands, When
`uv run --with pytest==9.1.1 pytest -q tests/test_contracts.py -k "fog or ai_spec"`
runs, Then it exits 0 with `17 passed` (the pre-rewrite count is also 17; the pin
updates keep the same tests, and a red names which pin lagged) — the three pins move in
that one commit or the gate refuses the commit.

## Decisions

<!-- One `**D-NNN-NN — <the decision>**` per line, each with a `**Rationale:**` under it.
     Prefix a line with `- [X]` to claim the decision earns promotion: it constrains
     specs that do not exist yet, and `ai-eng decide` promotes only marked lines.
     `ai-eng decide` does not write here: it writes a record under docs/adr/. -->

**D-048-01 — Fold the handshake mechanisms into `ai-spec` step 0; no new skill.**
**Rationale:** intake is already a governed step of the governing skill; a parallel
skill is a second convention beside an existing one, and report 021's precedent for
overlapping external skills is fusion into the verb that owns the moment.

**D-048-02 — The bulk of the mechanism prose lives in `references/intake.md` with a
self-sufficient pointer in step 0, because the fog headroom is 0.16.**
**Rationale:** the ceiling is arithmetic, not taste (measured with the gate's own
functions); a rewrite that crosses it either gets the ceiling raised without cause or
dies at the gate — the reference convention lets the material exist where the skill can
still name every step.

**D-048-03 — Harvest patterns, never the external file's prose.**
**Rationale:** the source is unlicensed and untraceable to an author; the wheel carries
MIT-harvested text only with attribution (report 021's NOTICE rule), and here there is
nothing to attribute — writing it in this tree's voice is the only clean path.

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
