---
id: "047"
slug: autonomous-cycle-wall-budget
status: draft
date: 2026-08-29
ref: ""
supersedes: ""
---

# Autonomous cycle with a wall budget

## Who this is for, and what it is worth to them

The repository owner, who pays for every cycle in wall-clock and in trust. The only giant
block ever timed cost 19 h 42 min (report 023's postmortem, measured on the 045 session);
seven of every ten active minutes went to critics without a budget, ceremony repeated per
commit, a gate that serializes its own errors, and clock nobody was watching. The owner
set the ceiling on 2026-08-29: a governed cycle fits 180 minutes for a giant block, and
normal blocks fit far under it. When this is done, a cycle that breaks the ceiling says so
on its own recap, and a critic that dies silently can no longer stall a night.

## Context and problem

The postmortem measured where the 19 h 42 min went and priced five fixes (B1-B5). Three
of the five exist only as prose in that report: the watchdog, the critic timebox and the
batched gate. The tree carries none of them. Meanwhile the doctrine already states the
rule this spec turns into an instrument — rule 12: a decision that always comes out the
same is code, not a prompt. Whether a cycle fit its budget is exactly such a decision:
it is arithmetic over `.ai/events.jsonl`, which every hook already stamps.

What is true today, file by file:

- `contract.py` names every budget the framework enforces (`RECAP_TABS_MAX`,
  `LOAD_TIER_MAX`, `SKILL_FOG_CEILING`) — but no wall budget. PO-27 in
  `docs/requirements.toml` holds the ceiling open until `grep CYCLE_WALL_BUDGET_MINUTES
  src/ai_engineering/contract.py` answers.
- The five critic skills (`ai-challenge`, `ai-council`, `ai-review`, `ai-verify`,
  `ai-security`) carry a two-round cap per digest (spec 041) but no time and no I/O
  contract. Measured: Grill 75 min, Review 212 min, Verify 47 min, Security 102 min and
  dead with no verdict delivered.
- `.ai/events.jsonl` carries every command, guard block and exception with an ISO `ts`
  field and a `session` id — 7 300+ lines and no reader that can answer "where did the
  last six hours go". (`stamp` is the chain-seal hash, not a time; the reader uses `ts`.)
- `just check` fail-fasts: k independent defects cost k full passes of ~13 min. The
  postmortem measured three full gates burned between 03:59 and 04:06Z this way. `just
  1.58` was verified on 2026-08-28: the `-` prefix continues after a failed step; `just
  -a` and `--ignore-errors` do not exist.
- `ai-goal` says the cycle runs "without me" in its name and nowhere in its body forbids
  a step waiting for a person. The 045 session lost ≈340 min to forks that hung or waited
  and told nobody.

## Options considered

1. **A prose budget in `ai-goal`** — "aim to finish in three hours". Cheapest to write.
   It loses because the framework already proved the shape: a commitment that no command
   checks is the "266 of 385" defect this repository exists to undo, and the postmortem
   itself is the evidence — the timeboxes have been prose since 2026-08-28 and nothing
   moved.
2. **A hard runtime killer** — a watchdog process that kills any fork past its timebox.
   It loses because the framework does not own the host: forks are launched by whatever
   surface runs the skills, and a guard that cannot decide (whose child is this?) fails
   open or strangles healthy work. The doctrine reserves hooks for fail-closed decisions
   on events the chain already sees.
3. **Budget as data, verdict as a derived report** (chosen) — the ceiling and the
   timeboxes live in `contract.py` beside every other named budget; the critic skills
   carry the bound as their own text (a critic that cannot finish says `TIMEBOXED`
   instead of dying); `ai-eng report vitals` recomputes the truth from the event stream
   and a cycle over budget exits `INCOMPLETE [OVER_BUDGET]` on its own recap; `just
   check-all` batches the gate so k defects cost one pass. Nothing is killed; everything
   is measured, and the measurement fails closed.

## Decision

Option 3. The wall budget becomes a named constant, the critics become bounded and
self-reporting, the session becomes measurable from events already recorded, and the gate
becomes batched. The clock disqualifies a run and never approves one — PO-26 stays true:
no elapsed-time claim opens a box; only a green gate does. The other options die here:
prose without a command (option 1) is what produced 19 h 42 min, and a killer (option 2)
is a guard that cannot decide.

If this decision constrains specs that do not exist yet, mark it `[X]` under `## Decisions`
and give it a record of its own: `ai-eng decide "<title>"`.

## Challenged once

The strongest case against: *the budget will be gamed — an agent under a wall-clock bound
skips the critics it cannot finish inside the box, and the framework's whole product is
that a green nobody earned is the disease.* The case is real and the design answers it
three ways. First, `TIMEBOXED` is an exit the recap counts: a cycle that returns zero
critic verdicts inside its budget is `INCOMPLETE`, not fast. Second, the vitals reader
reports per-phase minutes, so a cycle that "fits" by skipping review shows a review lane
with no verdict — the same shape the postmortem found in Security's 102 minutes. Third,
the budget disqualifies only upward: no box ever ticks because the clock said so. The
budget changes what a stall costs, not what green means.

## Grill

ran: round 1, 2026-08-29 — 3 min

### Q1 — The context says the event stream carries a `stamp` for wall arithmetic. Does `stamp` hold a time?
**A:** No — `stamp` is the chain-seal hash (`_emit.stamp()` keys off the home's key); the
time field is `ts`, ISO-8601 written by the emitting hook. The context names `ts` now and
says what `stamp` is. This changed lines 41-43.

### Q2 — Task 1 justifies `CRITIC_CALLS_MAX = 120` as "the order of magnitude Review
burned in 212 minutes". Does the postmortem measure a per-critic call count?
**A:** No — it measures 409 calls for the whole 19 h 42 min session. 120 is derived from
the owner's ceiling (five critics sharing the box), not measured. The assumption now says
which numbers are decisions and which are measurements.

### Q3 — Do the examples' phase buckets (tool-wait / model / idle-or-hung) come out of
`events.jsonl`?
**A:** They do not — that split belongs to the host transcript, and D-047-03 refuses the
host log. The examples now name the buckets the event stream really carries: minutes per
`cls` (command, blocked, error, bypassed), which is what a stall looks like from inside
the framework's own record.

### Q4 — Does the line count the context cites hold?
**A:** It was stale at write time — `wc -l .ai/events.jsonl` answers 7 323 today, not
3 700. Fixed.

### Q5 — Does anything contradict PO-26 or the doctrine?
**A:** Nothing checkable failed on that axis: the Decision states the clock disqualifies
and never approves, PO-26's grep still returns nothing over src/, hooks/, tests/, specs/.

## Council

ran: round 1, 2026-08-29 — 6 min
lenses: cost, reversibility, undecidable, trust, example

### Gaps no single lens named

none

### Findings cut for carrying no command

- Cost lens: "the plan has no per-task minute budget" — true, and the plan is the house
  format, which budgets by check command, not by minutes; no command distinguishes the
  finding from the convention. Cut.

### Findings the cross-read refuted, with the command that refuted them

- "Task 4's check pipes through bare `python`, which is not on PATH" — refuted: the
  check reads `uv run python` as written; `which python` confirms bare `python` is
  absent, and the plan never used it.
- "Tasks 1-8 are CLAIMED-NOT-REAL: the constants, the test file, vitals.py, check-all,
  the timeboxes do not exist" — refuted: this is a draft whose boxes all read `[ ]`; the
  spec's "what is true today" claims only the absence, and `grep -c '\[ \]'
  specs/047-autonomous-cycle-wall-budget/plan.md` answers 8. A draft is not a lie.
- "The example pytest -k timebox fails on a missing file" — refuted: task 2 is the red
  fixture, committed red on purpose; the house order is red-then-green.

### The two counts

- Gaps that appeared only after the cross-read: **0**
- Findings deleted, for carrying no command or for being refuted: **4**

## Assumptions and unresolved risks

- The `ts` field is written by the emitting hook at event time and the line is sealed
  with it; a forged or edited line fails the chain check the seal exists for, and vitals
  refuses a session whose chain is broken rather than trusting its clock.
- `just 1.58` keeps the `-` prefix semantics through upgrades; the pin lives in the
  justfile and a recipe test asserts the prefix appears in `just -n check-all`. If a
  future just removes it, `check-all` degrades to today's `check` and nothing lies.
- Forks report their own wall time only as well as the host's transcripts allow; vitals
  reads the event stream, which the framework controls, and not the host log, which it
  does not.
- Unresolved: whether `report vitals` should also gate `ai-ship`. This spec ships it as a
  verb plus the recap's banner; a gate before merge needs a measured baseline of normal
  cycles first — three real cycles, not one postmortem.


## Examples somebody can check

- Given a cycle whose events span 200 minutes of wall time, When `uv run ai-eng report
  vitals --session <id>` runs, Then it exits `INCOMPLETE` and its output names
  `OVER_BUDGET` and the `cls` bucket that holds the largest gap.
- Given a cycle whose events span 90 minutes, When `uv run ai-eng report vitals
  --session <id>` runs, Then it exits `PASS` and prints minutes attributed per `cls`
  (command, blocked, error, bypassed) beside the wall time between first and last `ts`.
- Given a critic skill with no timebox line, When `uv run --with pytest==9.1.1 pytest -q
  tests/test_cycle_budget.py -k timebox` runs, Then it fails naming the skill — the bound
  is checked text, not hope.
- Given a plan task whose check is a red lint and a red test, When `just check-all` runs,
  Then it reports both in one pass and exits non-zero — k defects, one pass.
- Undecidable on purpose: whether a given cycle's 180th minute was "wasted" — vitals
  prints where the minutes were, and a person decides what waste means. The command
  refuses the judgement, not the arithmetic.

## Decisions

**D-047-01 — The wall budget is a named constant in contract.py, and only the recap
enforces it.**
**Rationale:** every other budget the framework enforces lives there; enforcement is
disqualification on the recap, never approval on the clock, which keeps PO-26 true.

- [X] **D-047-02 — Critics carry a timebox and an I/O contract in their own text; a
  critic that hits the box returns `TIMEBOXED` with what it has.**
  **Rationale:** the framework cannot kill a fork it does not own (option 2 died there),
  but a bound the critic reads and obeys converts "102 min and no verdict" into "40 min
  and a partial verdict" — the verdict is the artifact, the silence was the defect. This
  constrains every future critic skill: a critic without a box cannot land.

**D-047-03 — Vitals reads only `.ai/events.jsonl`, never the host transcript.**
**Rationale:** the event stream is the framework's own record with its own stamp and
chain; a reader that leaned on a host log would be a reader with a per-surface fork.

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. The
External-check and Second-path boxes carry a named wrinkle: the second path for vitals is
the independent recomputation inside the same command (wall = sum of phases, asserted),
and the external check is CI running `just check-all` on the push that lands it.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI
