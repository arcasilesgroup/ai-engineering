---
id: "031"
slug: verification-dag-loop-termination-and-spec-containment
status: draft
date: 2026-08-25
ref: ""
supersedes: "010"
---

# Verification DAG, loop termination and spec self-containment

## Who this is for, and what it is worth to them

The person who runs `/ai-goal` on this repository and approves what it produces, and every
stranger who installs the wheel for a repository they are accountable for. The research goal
(`.ai/reports/018`) marked, and specs 029 and 030 closed the verification and cost gaps, the
third cluster this repository does not yet cover: **orchestration** — how multiple lanes of a
review are verified, merged and terminated, and what a spec owes a builder that reads only
it. This specification supersedes parts of spec 010's target to close the research paquete 3
in one reviewed, TDD'd increment (its N23, N24 and N25):

- **N23** — a verification DAG: each node's output is verified before it becomes the next
  node's input, and an orchestrator merges parallel lanes with dedupe by file:line, re-ranks
  globally by real consequence and surfaces lane conflicts (graph-engineering's full-review);
- **N24** — a loop-termination criterion: an autonomous loop is done only after two
  consecutive identical green runs, and a no-op pass still counts as a pass, so neither a
  lucky single green nor an invisible-progress loop can pass or stall (Loop-Engineering);
- **N25** — a self-contained spec contract: a spec carries the whole job on its own — no
  "as discussed", no "the remaining work" — and an evaluator can resolve a section by number
  without duplicating it (Loop-Engineering's numberless-interface rule).

Nothing here grants authority, adds a service, or creates a second control plane. It adds
three checked behaviours to the orchestration backbone specs 029 and 030 built.

## Context and problem

**What is true today, measured in this tree on 2026-08-25, after specs 029 and 030:**

- `verify_cold.py` (030) applies the answer key read-only; `evidencing.py` (029) rechecks a
  claim; `revalidate.py` (030) revalidates one finding. But nothing **merges the outputs of
  several independent lanes**: a review that runs security and correctness and design lanes
  gets N reports nobody reduces to one verdict, no dedupe by file:line, no global re-rank by
  real consequence, and no conflict surfaced when two lanes disagree on the same line.
- `src/ai_engineering/dag.py` (spec 013) orders *claims* deterministically — it is the
  coordination DAG for the one-writer rule, not a **verification** DAG. It does not gate that
  a node's output is verified before the next node consumes it, which is the check that stops
  a downstream node building on an upstream error.
- There is no **loop-termination criterion**: an autonomous orchestrator has no rule that two
  consecutive identical green runs mean done, and no rule that a pass which changed nothing
  still counts as a pass. Without them it either stops on a lucky single green or loops
  forever on an agent making no-op edits (Loop-Engineering's measured stall-at-80% lesson).
- A spec is not yet a **self-contained contract**: nothing refuses the conversation leaks
  ("as we discussed", "the remaining work") that make a spec unreadable by a builder who only
  gets the file, and no helper resolves a spec section by number for an evaluator that must
  not duplicate its content.
- The inherited red stands: `madr.validate` returns `INCOMPLETE [MADR_SCHEMA_INVALID]` from
  ADR 0025 of spec 026, recorded in `.ai/reports/014` and specs 028/029/030. Spec 031 does
  not authorise rewriting that history.

**The problem, in words a non-technical reader can follow:**

A review that is several checks long needs one answer, not several. An autonomous loop of
build-and-check needs a rule for when it is finished and what counts as progress. And a
spec must be a thing that explains itself to a builder who sees only that one file — not a
note that says "as we discussed". The three changes in this spec add those three controls:
merge several lanes into one verdict with the noise removed, stop an autonomous loop only
when it has really settled, and make a spec carry its whole meaning alone.

## Options considered

1. **Add the three controls as one reviewed superseding spec (chosen shape).** N23 (verification
   DAG + lane merge), N24 (loop termination) and N25 (spec self-containment) land as their own
   TDD tasks with a red fixture first, on top of the evals/answer-key/cold-read backbone.
   Gives: one increment that names the merge before the loop that terminates on its verdict,
   and a spec contract that makes the spec the only interface the DAG's nodes read. Costs: a
   wide block; mitigated by atomic commits. Rules out: weakening any of the three.
2. **Do the loop criterion alone, defer the DAG and spec contract.** Gives: a smaller first
   block. Costs: a loop that terminates on a merged verdict that does not exist, and specs
   that still leak conversation into the only interface the loop's nodes read. The user's
   rule is that nothing in the goal is a ceiling.
3. **Adopt graph-engineering wholesale as external tooling.** Gives: speed. Costs: the
   framework's philosophy is deterministic facts in code; importing a `claude -p` fan-out
   would make a command this wheel cannot run a claimed control, which spec 010's
   portable-command rule refuses. Rules out: external-only.

## Decision

**Option 1**, as paquete 3 of the research. The spec supersedes spec 010 only where it
extends the target with the three behaviours below; it does not weaken, drop or relabel any
normative requirement 010 already states. Each behaviour is closed, versioned, and comes
with both a positive fixture and a nearby clean control. The three are:

### B-031-1 — Verification DAG and lane merge (research N23)

A `lane_merge` runner in `src/ai_engineering/` with two halves:

- **`gate_nodes`** — each node carries a `verify` command; before the node's output is
  consumed as the next node's input, the verify command must pass. A node whose verify fails
  leaves its downstream input `INCOMPLETE` — nothing builds on an unverified output.
- **`merge`** — findings from several lanes (each `{file, line, consequence, lane}`) are
  deduped by `(file, line)`, re-ranked globally by consequence severity, and a lane conflict
  on the same `(file, line)` is surfaced as a high-signal conflict entry rather than hidden
  by whichever lane won.

This is distinct from `dag.py` (spec 013), which orders *claims*; this orders and gates
*verification output*. The evals harness's reporters are the natural lanes.

### B-031-2 — Loop termination (research N24)

A `loopgate` runner in `src/ai_engineering/` that keeps a pass history:

- **done** — the loop is done only when the last two recorded runs are both green **and**
  their outcome digests are identical. A single green, or two greens that differ, is not
  done.
- **no-op passes count** — a pass that changed nothing in the tree still records a green, so
  a converged or stalled loop reaches the two-identical-stop instead of looping forever; a
  pass that *diverged* (changed the digest) restarts the identical-run requirement.
- a failed pass resets the consecutive-green run.

This is the termination criterion an autonomous orchestrator uses to decide when to stop: it
cannot stop on a lucky green, and it cannot run forever on invisible progress.

### B-031-3 — Spec self-containment (research N25)

`spec.py` gains two checked behaviours:

- **`self_contained`** — refuses a spec text that carries conversation-dependent phrases
  ("as we discussed", "as discussed", "the remaining work", "per our conversation", "like we
  said"); a spec that cannot stand alone is not a governed record.
- **`section`** — resolves a spec section by number (`§N` → the Nth `## ` heading) via a
  deterministic, position-based helper, so an evaluator can reference a part of the spec
  without copying it. The `ai-spec` corpus gains the rule that the spec is the whole
  interface to the builder.

## Challenged once

**"A loop gate is over-engineering — this repository already has a one-writer rule."** The
one-writer rule governs *who may write to the repository*; the loop criterion governs *when
an autonomous orchestrator stops rebuilding and re-verifying a feature*. They are different
controls and one does not imply the other: an orchestrator can respect one-writer strictly
and still loop forever on no-op edits. Loop-Engineering built the no-op-rule precisely
because attention, not authority, is the scarce resource in a long loop.

**"Section numbers are a formatting bikeshed."** The `section` helper is position-based —
it does not force renumbering the thirty existing specs and touches no template. The
load-bearing half is `self_contained`, which is what actually stops a builder from receiving
a spec that says "as we discussed". The numbered reference is a small, deterministic,
tested convenience for the DAG's nodes, and it is optional.

## Assumptions and unresolved risks

- Assumption: the `verify` commands a DAG node runs are the same executable checks
  `evidencing.py` re-executes — one evidence vocabulary, so a fail is a fail in both.
- Assumption: outcome-digest equality is the right identity for "identical green runs".
- Unresolved: an `a/b pick` check still needs a judge (human or model) and has no fully
  automated CI path — carried from specs 029 and 030 unchanged.
- Unresolved: the inherited `madr.validate` red from ADR 0025; recorded, not fixed here.
- Assumption: a lane conflict is surfaced, never auto-resolved; the orchestrator or a person
  decides which lane was right.

## Examples somebody can check

Given a node whose verify command fails,
When its output would feed the next node,
Then the downstream input is INCOMPLETE and nothing consumes the unverified output
(`uv run --with pytest==9.1.1 pytest -q tests/test_lane_merge.py` → `1 passed`).

Given two lanes reporting the same (file, line),
When merge runs,
Then one deduped finding remains, findings are re-ranked by consequence globally, and a
conflicting verdict on the same line is surfaced as a conflict
(`uv run --with pytest==9.1.1 pytest -q tests/test_lane_merge.py` → `2 passed`).

Given a loop with one green run,
When done is asked with a single or a differing second run,
Then it is not done; a second identical green run makes it done
(`uv run --with pytest==9.1.1 pytest -q tests/test_loopgate.py` → `2 passed`).

Given a no-op pass after an identical green,
When done is asked,
Then it is done — a no-op pass counts, so a converged loop stops
(`uv run --with pytest==9.1.1 pytest -q tests/test_loopgate.py -k noop` → `1 passed`).

Given a spec whose text carries "as discussed",
When self_contained reads it,
Then it reports the phrase and refuses the record; a clean spec passes, and section(text, 2)
resolves the second ## heading without copying it
(`uv run --with pytest==9.1.1 pytest -q tests/test_spec_containment.py` → `2 passed`).

## Decisions

**D-031-01 — verification DAG and lane merge: each node's output is verified before the next
consumes it, and lanes merge with dedupe by file:line, global re-rank by consequence and
surfaced conflicts.**
Rationale: graph-engineering's full-review proved that verification in each node, before its
output becomes the next node's input, catches the error at its origin, and that a merge which
dedupes and re-ranks is what turns N opinions into one verdict. Distinct from `dag.py` (claim
ordering, spec 013).

**D-031-02 — loop termination: done only after two consecutive identical green runs; a no-op
pass counts; a diverging pass restarts the identical run; a failure resets it.**
Rationale: Loop-Engineering's two lessons — a single green can be luck (the double-pass
kills it) and a no-op change must still count as a pass (the invisible-progress loop stops).

**D-031-03 — a spec is a self-contained contract: `self_contained` refuses conversation
leaks and `section` resolves a part by number, so the spec is the only interface to the
builder.**
Rationale: Loop-Engineering's builder reads only the spec; a spec that says "as discussed"
cannot carry the whole job, and a position-based section reference lets an evaluator point
at one part without duplicating it.

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