---
id: "041"
slug: marked-promotion-bounded-loop-review-first
status: draft
date: 2026-08-26
ref: ""
supersedes: ""
---

# Marked promotion, bounded spec loop, review-first critics

## Who this is for, and what it is worth to them

The person who runs `/ai-goal` on this repository and approves what it produces, and every
stranger who installs the wheel for a repository they are accountable for. Spec 031 closed
the orchestration gap with code: a verification DAG (`lane_merge`), a loop terminator
(`loopgate`) and a self-contained spec contract (`self_contained`, `section`). This spec
closes the three gaps that code left open: the promotion trigger of `ai-eng decide` is
still prose nobody checks, the spec↔critics loop still has no bound on the skill layer, and
the cycle's parallel policy still records no order between the critics after build.

## Context and problem

**What is true today, measured in this tree on 2026-08-26:**

- `loopgate.done()` implements the two-identical-greens rule (spec 031 / B-031-2), but no
  skill in the cycle uses it: the spec↔challenge/council loop runs without a ceiling on any
  SKILL.md. Report 019 measured the adversarial-refinement case: convergence is typical in
  3–5 rounds but not guaranteed — the loop can oscillate or overfit [4], and the build loop
  already has its cap (two attempts per task and failing recipe, ai-goal) while the spec
  loop has none [9].
- `ai-eng decide` promotes any titled decision against the target spec; the promotion
  criterion ("constrains specs that do not exist yet") lives only in prose — the
  `decide.py` docstring and ai-spec paso 10. Report 019: "not every important decision is
  architectural" [5], "you don't need to log every choice" [8]; the trigger of promotion
  is what has to be tightened [9][10].
- `policy/skill-sequence.toml` records `policy = "fork contexts only; task-level
  parallelism inside ai-build per the approved plan"`. It records no order between the
  post-build critics. Report 019: independent readers buy coverage and pay in precision —
  14 findings per session vs 9 (+56%), but 22% false positives vs 5.3% without a filtering
  round [1][12]; defect detection is not what reviewers reliably contribute [2]; the
  filtering round must come after the sweep [12]. The evidence-backed order: review first,
  verify and security after [1][2][12].

**The problem, in words a non-technical reader can follow:** the low-level code for
terminating an autonomous loop exists, but nothing on the skill layer tells the loop when
to stop; any decision can still be promoted to a record of its own without the spec saying
it earns one; and when the gate sends work back through the critics, nothing says review
has to pass before verify and security start ticking boxes on bytes that may still change.
Three small gaps, each a sentence of policy or prose, each closing a loop the code already
makes possible.

## Options considered

1. **Skill-layer prose for the loop bound (chosen); the marker as the promotion trigger;
   review-first as the parallel policy's data.** The two-rounds-per-digest rule is written
   as an instruction into ai-challenge and ai-council; the `[X]` marker becomes the
   promotion trigger in the spec template, `spec.py` and `decide.py`; review-first becomes
   the `[parallel] policy`'s data. Gives: the three gaps close in the files people already
   read, and a stranger's repo gets them with the wheel. Costs: the loop bound is a bound a
   skill enforces by following it, not a runtime check — the same kind of instruction the
   build cap is in ai-goal today. Rules out: nothing.
2. **Wire `loopgate.done()` into a cycle orchestrator now.** Gives: a machine-checked
   termination criterion. Costs: there is no orchestrator yet — `/ai-goal` is the closest
   thing, and it is a skill, not a process; building the wiring means building the loop
   harness this spec is not about. Spec 031 recorded loopgate as the orchestrator's future
   instrument; this spec keeps that plan.
3. **Tighten the promotion trigger by deleting the title path.** Gives: no way to promote
   outside the marker. Costs: `ai-eng decide "<title>"` is the named command in the spec
   template and in tooling; the marker filter refuses unmarked titles, which is the same
   gate without the hard delete. The filter is chosen, the delete is not.

## Decision

**Option 1**, as the closing paquete of the orchestration story spec 031 opened — and for
the trigger, option 3's gate without its delete. Three behaviours:

### B-041-1 — The `[X]` marker: promoted decisions are marked in the spec, and `ai-eng decide` promotes only marked ones

The spec template's `## Decisions` section documents `- [X] **D-NNN-NN — <the decision>**`:
an author marks a decision `[X]` exactly when it constrains specs that do not exist yet —
architectural and cross-cutting: a boundary (API, auth, storage), a global convention
later specs must know and respect. `spec.py` gains `marked_decisions(text)`, which returns

every marked entry under `## Decisions` as `(id, title)`. The marker's place is under
`## Decisions`, before the `**D-NNN-NN —**` identifier — the one spot no plan task
occupies, which is what keeps it apart from the plan's tick column. `ai-eng decide
"<title>"` returns INCOMPLETE, writing nothing, for any title not marked in the target
spec. ai-spec paso 10 states the criteria for marking. Most decisions never earn a record
of their own; the spec is their record [5][8][10].


### B-041-2 — The spec↔critics loop is bounded at two rounds per digest

ai-challenge and ai-council each carry the bound: at most two challenge/council rounds

against the same spec digest — the canonical bytes `approval_bytes` signs, which is what
`ai-eng spec show` prints; a revision that changes the digest reopens the count; the
second round against an unchanged digest is the last — the critic writes the outstanding
findings worst first and hands the page to the person. This is spec 031's loop gate (two
identical greens, done) written as the skill layer's instruction; the orchestrator wires
`loopgate.done()` when it automates the cycle [4][9].


### B-041-3 — The parallel policy records review before verify and security

`policy/skill-sequence.toml`'s `[parallel] policy` records that the only concurrency is
fork contexts; `ai-review` runs before `ai-verify` and `ai-security`, so verify and
security only tick boxes on bytes review has not sent back; when the host can run both,
ai-verify and ai-security may run together as a pair once review is green. Task-level
parallelism inside ai-build per the approved plan is unchanged [1][2][12].

## Challenged once

**"A marker an author writes is prose again — anybody can add `[X]` to anything."** The
marker does not gate on the author's honesty; it gates on the record. The claim "this
decision constrains specs that do not exist yet" is now visible in the spec's own diff,
next to the decision it is about, reviewed with it — the loose trigger was prose no
reviewer saw at promotion time, and the tightened one is a checked claim at the same place
the decision is reviewed. The `[X]` line is the promotion's second reader.

**"Two rounds is a number without a source."** It mirrors the existing build cap on the
same loop (two attempts per task and failing recipe, ai-goal) and report 019's shape: the
adversarial loop saturates quickly but carries no convergence guarantee, so the ceiling is
the cost of oscillation [4][9]. It sits one round below the 3–5 typical saturation rounds
[4] because the ceiling exists to force the escalation page, not to absorb the loop.

## Assumptions and unresolved risks

- Assumption: the two-rounds-per-digest bound is enforceable by skill instruction in an
  agentic run, the way the build cap is enforced today.
- Assumption: an author marking `[X]` exercises the same judgement the promotion criterion
  asks for; the marker makes the judgement auditable, it does not replace it.
- Unresolved: `ai-eng decide` promotion stays gated on `madr.validate` returning PASS,
  which on this tree returns `INCOMPLETE [MADR_SCHEMA_INVALID]` from ADR 0025 of spec 026
  (recorded in `.ai/reports/014`, inherited through specs 028-040, not fixed here).
- Unresolved [sin fuente]: whether running verify+security in parallel with review wastes
  work is unmeasured (report 019, "Lo que nadie ha medido"); the policy therefore records
  the default sequence and names the pair only as an option the host may take when review
  is green.

## Examples somebody can check

Given a spec whose `## Decisions` carries `- [X] **D-041-01 — the first decision**`,
When `marked_decisions` reads it,
Then it reports the marked decision, and ignores unmarked entries and entries under other headings
(`uv run --with pytest==9.1.1 pytest -q tests/test_spec_marker.py` → `3 passed`).

Given `ai-eng decide "<title>"` against a spec where the title is not marked,
When the verb runs,
Then it returns INCOMPLETE, names the marker, and writes nothing
(`uv run --with pytest==9.1.1 pytest -q tests/test_spec_marker.py -k decide` → `1 passed`).

Given two rounds against the same spec digest,
When a third is asked for,
Then the critic stops at two and hands the page to the person; a revision that changes the digest reopens the count
(`uv run --with pytest==9.1.1 pytest -q tests/test_skill_bounds.py` → `1 passed`).

Given the cycle's map,
When the `[parallel] policy` is read,
Then it names review before verify and security, and the cycle tests still pass
(`uv run --with pytest==9.1.1 pytest -q tests/test_skill_sequence.py` → `5 passed`).

Given the whole block,
When the gate runs,
Then no new failure appears: the inherited 5 (4 `test_madr.py` + 1 `test_intent.py`) stay, everything else green
(`just check`).

## Decisions

**D-041-01 — a decision is born in its spec and is promoted only when the spec marks it `[X]`: the marker is the author's claim that the decision constrains specs that do not exist yet, and `ai-eng decide` refuses unmarked titles.**
Rationale: report 019 closes the loose trigger — "not every important decision is architectural" [5], "you don't need to log every choice" [8]; a checked, reviewed claim replaces an inferred one. The spec remains the decision's record [10][6]; the ADR is promoted only when future specs must know it.

**D-041-02 — the spec↔challenge/council loop is bounded at two rounds per digest on the skill layer, and `loopgate.done()` is integrated when an orchestrator automates the cycle.**
Rationale: spec 031 built the terminator as infrastructure; the loop that exists today is skill-driven, so the bound belongs where the loop runs. The ceiling is the escalation rule — oscillation is the documented failure [4], and the build cap is the precedent [9].

**D-041-03 — the parallel policy records review-first: `ai-review` gates `ai-verify` and `ai-security`, which may pair as fork contexts when review is green and the host can run both.**
Rationale: independent readers already buy their independence by forking [12]; the evidence supports review as the quality filter that passes before later critics tick boxes on bytes that may still change [1][2][12].

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. This
specification changes two verb behaviours and three prose/data surfaces; it adds no
service, no URL and no second hop, so the service-shaped boxes are `not applicable`.

- [x] CI/CD — `just check` runs the new suites (`tests/test_spec_marker.py`,
  `tests/test_skill_bounds.py`) and the skill-sequence tests on every push
  (`.github/workflows/check.yml`); nothing here is deployed
- [x] Logs — not applicable, and that is the rule: this spec changes verb refusals and
  policy data; every verb still emits the one JSON line `ai-eng digest` reads
- [x] Traces — not applicable, and that is the rule: one process, no second hop, no trace
- [x] Errors — the new paths fail closed: an unmarked title is INCOMPLETE with nothing
  written, and the loop bound stops with an escalation page, never a silent no-op
- [x] Health and data age — `tests/test_spec_marker.py` and `tests/test_skill_bounds.py`
  run in `just test` on every gate and pin the refusal and the bound; the skill-sequence
  suite pins the policy
- [x] External check — `.github/workflows/check.yml` runs the gate on every push
  (untouched); the negative fixture — an unmarked title refused with nothing written — is
  the check
- [x] Second path — the marker parse (`spec.py`) and the refusal (`decide.py`) are distinct
  routes over the same record, and `ai-eng decide --list` still reads the outcome
- [x] Security — `just security`: gitleaks, semgrep and trivy on every push, over a change
  that adds no dependency and no network call
