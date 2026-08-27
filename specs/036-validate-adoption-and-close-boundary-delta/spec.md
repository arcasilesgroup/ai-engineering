---
id: "036"
slug: validate-adoption-and-close-boundary-delta
status: draft
date: 2026-08-26
ref: ""
supersedes: "035"
---

# Validate the reference adoption and close the boundary delta

## Who this is for, and what it is worth to them

The repository owner who approved spec 035 and the stranger who audits the framework. Spec
035 adopted eight reference patterns as new kernel behaviours; before the first build task
ran, a pre-flight audit of the tree found that **eight of the nine kernel behaviours already
exist in this tree**, shipped by specs 013-034 with the same research provenance. This spec
records that validation as evidence (so the adoption goal is not silently re-adopted as new
work), supersedes 035's implementation scope, and adopts the one genuine gap the audit found
plus the checks that keep the validation from rotting. For the owner this turns a false-start
into a measured, honest delta; for the stranger it is the record of what the framework
already embodies, by module and by contract symbol, and why nothing more was built.

## Context and problem

**What is true today, measured in this tree on 2026-08-26, after specs 028-034 and before
any 035 build task:**

| Spec 035 kernel behaviour | Framework already ships (module · contract symbol · evidence) |
|---|---|
| B-035-1 executed evidence, ticked-without-evidence = unmet | `src/ai_engineering/evidence.py` (445 ln) · `verify()` / `VERIFIED` / `EVIDENCE_MISSING` / `EVIDENCE_STALE` / `EVIDENCE_DIGEST_MISMATCH` / `EVIDENCE_EXECUTED_FAIL` — the check-evidence receipt scheme, first shipped `feat(evidence): verify executable receipts` (2026-08-14), calibration formalised in spec 029 |
| B-035-2 verifier isolation, `NOT COVERED` ≠ PASS | `src/ai_engineering/verify_cold.py` (spec 030) · `Verdict` (PASS / FAIL / BLOCKED) — reads only the spec/answer-key and delivered files, no write tools, uncertain check = fail, `--recheck` via `evidencing` |
| B-035-3 shared scope/severity/honesty contract | `src/ai_engineering/contract.py` (specs 026-033) · `audit_one()` — lanes: `_output_contract_problems`, `_load_tier_problems`, `_incorrect_correct_problems`, `_corpus_problems`, `_dispatcher_problems` |
| B-035-5 anti-rationalization + red flags | `src/ai_engineering/contract.py` · `_anti_rationalization_problems` ("has no anti-rationalization section naming an excuse and answering it" = refused) |
| B-035-6 cost pre-flight | `src/ai_engineering/cost.py` (spec 029) · `calibrate()` — bounded-sample, policy threshold in `policy/cost-thresholds.toml`, fails closed without consent; its docstring cites deepsec and headstart, the same research references |
| B-035-7 skill schema + tool gating | `src/ai_engineering/capability.py` (capability specs 010/012/014/021, `feat(capability): enforce declared actions` 2026-08-13) · `preflight` — fail-closed declarations, unknown scope denied, `READY` never promoted without an executor; `policy/capability-manifest.schema.json` |
| B-035-8 context economy | `src/ai_engineering/trim.py` (spec 033) · `trim_output()` — head/tail + elision marker, failure lines never elided; plus `skillify.py` and `_load_tier_problems` |
| B-035-9 named decision frameworks | `src/ai_engineering/decision_fw.py` (spec 034) · `named()` — RICE / Effort/Value / Kano, an unnamed ranking is refused; its docstring cites contains-studio |

The audit commands behind the table: `wc -l src/ai_engineering/{evidence,verify_cold,contract,cost,capability,trim,decision_fw}.py`,
`grep -n "def verify\|EVIDENCE_MISSING\|def calibrate\|def named\|def audit_one\|def trim_output" …`,
`git log --format="%h %ad" -- src/ai_engineering/{evidence,capability}.py`, and the module
docstrings citing the same external references the research read. Every row was confirmed by
a command before this spec was written, and its contract symbol is the input B-036-3 checks.

**The missing piece the audit isolated:** spec 035's B-035-4 — a boundary classifier with
the explicit Always / Ask-first / Never vocabulary that reports `CANNOT DECIDE` and blocks
when a requested decision falls outside a skill's declared boundary (wayfinder W-02, in
`.ai/research/reports/04-wayfinder/report.md`). The existing `capability.py` preflight denies
unknown scope and gates `READY`, but it is not the three-class boundary vocabulary, and no
skill corpus carries the refusal in the case shape the routing harness parses (quoted
situations and `Not for … — …` refusals, the shapes `tests/skill_eval.py` admits). The
named-framework precedent (spec 034) proves the corpus mechanism: the rule lands in the
skill's `corpus.md` and is carried by the generic `skill_eval.py` routing lane; the same
mechanism will carry the boundary rule.

**The problem, in words a non-technical reader can follow:**

The plan spec 035 approved was about to rebuild things that already exist — a waste, and a
breakage risk, because two modules doing one job is how a framework rots. This spec records
the finding openly, stops that build, adopts the single genuinely missing control (the
decision-boundary classifier), and adds three small checks: the corpus rule in the parseable
shape, the proof objects that make the adoption measurable instead of promised, and a
freshness test that fails if the validated modules ever disappear — so the validation stays
true in writing, not in memory.

## Options considered

1. **Supersede 035 and adopt the measured delta (chosen shape).** Spec 036 supersedes 035
   at the record level ("never rewrite history" — label 035 as superseded at its digests,
   which this record and its approval name by value), keeps every shipped module as the
   validated answer, and adds B-036-1 (the decision-boundary classifier), B-036-2 (the
   parseable corpus rule + fixtures) and B-036-3 (the freshness test). Gives: an honest,
   small, tested delta, and a committed record that the adoption goal was already met.
   Costs: a two-stage record (this spec links its superseded predecessor instead of editing
   it; 035's spec/plan bytes stay frozen at their approval digests).
2. **Treat 035 as validation-only and defer the boundary work.** Gives: zero new code.
   Costs: the one real gap stays unclosed, and the research closes without the only
   behaviour it proved missing — the smallest honest adoption is cheaper than the ceremony
   of a finding with no action.
3. **Execute plan 035 as approved.** Gives: nothing but duplicated modules
   (`evidence.py`/`cost.py`/`decision_fw.py`/`trim.py`/`verify_cold.py`/`capability.py`
   re-implemented under new names) with name collisions, a red gate, and two sources of
   truth for the same contract — the exact failure DRY exists to prevent. Rejected on
   evidence, not on taste.

## Decision

**Option 1.** This spec
supersedes 035's implementation scope and adopts the measured delta. The superseded record,
by value: `specs/035-adoption-of-reference-patterns/spec.md`
`0bf6cb029f4c858bda7502c73b69eb72cab33f9b1b16c8962f13c62f88ca0677`,
`plan.md` `22c24bbbb907d9cde40a7db2ba1d3e4ddbe0fe7cc0a415ed7769152bec45062d`,
`approval.md` `33a5f58c0d19a07696f11883a5bc3889a0b925ddecc8a85d9c276979972ad805` —
frozen, unedited, and pointed at by this record and by a follow-up note added to 035's
`approval.md` (council F2.1 / re-council by-value gap: the link is written, not promised).
Specs 028-034, and all the modules in the table above, remain normative and are
**not** touched or rewritten. The behaviours 035 named are recorded here as validated —
already shipped — which is what this repository's research should have concluded all along.
The three additions:

### B-036-1 — Decision-boundary classifier (the wayfinder W-02 gap)

A `decision_boundary` module in `src/ai_engineering/` — the name deliberately avoids the
word `boundary` alone, which thirteen module files already use for filesystem, word
  and data boundaries (spec 036 council, gap G1). `classify(decision, declarations)`
  returns a `Classified` result — `verdict` one of `Always` / `Ask-first` / `Never` or
  `None` when the decision falls outside the declared boundary, plus an indexed `reason`
  (`U0` for undeclared or malformed declarations, `U1`, `U2`, … for each out-of-declaration
  class, the wayfinder `Unknown` numbering). An out-of-declaration decision reports
  `CANNOT DECIDE` and blocks — it never guesses, never silently widens its own boundary, and
  it distinguishes "declared but out" from "not declared at all". The declarations it reads
  come from the skill's machine-validated metadata (the `capability.py` manifest surface),
  so the classifier depends on the same single source of truth as tool gating. Source link
  recorded for checkability: `.ai/research/reports/04-wayfinder/report.md` (W-02, Unknown →
  CANNOT JUDGE).

### B-036-2 — Corpus rule in parseable shape, and the fixtures that prove it

The boundary rule lands on the two parse surfaces the routing harness actually admits
(spec 036 re-council, gap G1): the `Not for … — …` refusal clause goes in each skill's
`SKILL.md` description — the surface `tests/skill_eval.py`'s `_REFUSAL` parses — and one
quoted boundary situation with its destination goes in each `corpus.md` — the surface
`cases()` reads; a `Not for` row written into `corpus.md` instead is an empty-target send
that the problems lane skips, and the fixture proves that red half. The proof objects land
first, per the council's recommendation: `tests/test_036_boundary.py` (in-declaration and
out-of-declaration fixtures) and the `skill_eval` baseline move argued in the same commit
that adds the description refusals and corpus cases.

### B-036-3 — The validation freshness check

A small test file (`tests/test_036_validation.py`) asserts the validation table does not
rot: every row's module exists and exports the named contract symbol from the table above —
the symbol per row is the check's input (spec 036 council, gap G3) — and, where a row names
a provenance marker, the module docstring's first line carries it (spec 029, spec 030,
spec 033, spec 034, capability-era) so the provenance column is asserted, not remembered.
"Documented responsibility" is scoped to these two checkable facts; a future refactor that
deletes or splits one of the validated modules fails this check with the reason to update
the record first. The validation is a checked claim, not a memory.

## Challenged once

**"Superseding an approved spec because the plan found the work already shipped looks like
process theatre — the approval record exists, the delta is tiny, why not just build B-036-1
inside 035?"** Because the approval record is a governance claim at exact digests, and
governance is never edited silently: 035's digests describe seventeen tasks that would have
duplicated shipped modules. Leaving the record as-is while building something different from
it is exactly the "record says one thing, tree does another" state this framework exists to
expose. The supersede record is the honest exit. The one-directional-link wrinkle the
council named (F2.1) is answered by value, not by rewriting 035's frozen bytes: this
record's approval names 035's exact digests and states the supersession, and a follow-up
note is added to 035's `approval.md` — not to its spec/plan bytes — pointing a reader of
035's approval at this record.

**"A decision-boundary classifier adds a third classification surface next to
`capability.py`'s preflight — a second source of truth."** Concretely answered in B-036-1:
the classifier *reads* its declarations from the capability manifest and never defines its
own permission model; `capability.py` decides what an op may do, `decision_boundary.py`
decides whether a decision is out of declared scope at all. The two fixtures exercise
different questions, and B-036-3 asserts both modules keep their contracts.

## Assumptions and unresolved risks

- Assumption: the validation table is complete and its provenance attributions accurate —
  every row was checked by command, including git history for modules that predate their
  spec numbers (evidence.py 2026-08-14, capability.py 2026-08-13). The challenge is the
  second reader that tests this assumption.
- Assumption: specs 028-034 stay normative and none of their modules may be rewritten by
  this record; a later measured need may evolve a module, and that is a new spec change,
  never a silent edit.
- Unresolved: `capability.py`'s preflight and the new classifier's vocabulary overlap in
  intent; the plan sequences the classifier to read the same manifest, and the overlap is
  resolved by integration, not by a third declaration.
- Unresolved: `tests/skill_eval.py` has no content assertion today for either the
  named-framework or boundary rules — the harness carries both through the same generic
  routing lane (council finding F5.3). Whether a content-level assertion should be added is
  left to a later measured need; this spec adds the parseable corpus rows and the baseline
  move, nothing more.
- Unresolved: the inherited `madr.validate` red from ADR 0025 stays open; this spec does not
  authorise rewriting that history.

## Examples somebody can check

The commands below are the plan's red-first acceptance tests — `tests/test_036_boundary.py`
and `tests/test_036_validation.py` do not exist until the approved plan writes them, and the
counts are the goal, not a claim that they pass today (spec 036 council: land the proof
objects ahead of the prose).

- **Success, classified:** Given a decision inside the declared boundary, When
  `decision_boundary.classify` reads it, Then it returns `Always`, `Ask-first` or `Never`
  deterministically (`uv run --with pytest==9.1.1 pytest -q tests/test_036_boundary.py` →
  `5 passed`).
- **Denial, out-of-declaration:** Given a requested decision outside the declared boundary,
  When the classifier reads it, Then it returns `None`, reports `CANNOT DECIDE`, and blocks
  — it never guesses (`uv run --with pytest==9.1.1 pytest -q tests/test_036_boundary.py -k
  undecidable` → `1 passed`).
- **Corpus, parseable shape:** Given the boundary refusal in each `SKILL.md` description
  and one quoted boundary case in each `corpus.md`, When `tests/skill_eval.py` runs, Then
  the routing lane counts the new cases and the baseline moves with its reason in the same
  commit (`uv run python tests/skill_eval.py` → the boundary cases are counted); and a
  refusal written only in `corpus.md` is not counted — the fixture proves the red half.
- **Validation stays true:** Given the validation table's module-and-symbol rows, When
  `tests/test_036_validation.py` runs, Then every module exists with its contract symbol
  and responsibility, and deleting one fails the check with the reason to update the record
  first (`uv run --with pytest==9.1.1 pytest -q tests/test_036_validation.py` → `1 passed`).
- **Tree stays green:** Given the repaired tree, When `just check` passes, Then the gate
  proves it clean with the same inherited `madr.validate` red and no fifth failure.

## Decisions

**D-036-01 — spec 035 is superseded; the reference-adoption goal is recorded as already
met by specs 013-034, and the implementation scope of 035 is not built.**
Rationale: the pre-flight audit before any build task proved eight of 035's nine kernel
behaviours already ship in this tree with the same research provenance; building them again
duplicates modules and breaks the gate. "Never rewrite history" + DRY prescribe the
supersede record, not a silent edit.

**D-036-02 — the decision-boundary classifier is the adopted delta, reading the single
capability manifest source of truth, under a name that does not collide.**
Rationale: wayfinder's W-02 (out-of-declaration ⇒ CANNOT DECIDE, block) is the one proven
gap the audit found; `capability.py`'s preflight is a different question, and the classifier
reads the same declarations instead of creating a second permission model. The module name
avoids the thirteen module files using the word `boundary` for other concepts (council G1).

**D-036-03 — the corpus rule ships in the parseable case shape with fixtures first, and the
freshness test makes the validation checked, not remembered.**
Rationale: the routing harness admits only quoted situations and `Not for … — …` refusals
(council G2), so a prose rule would be unasserted; the proof objects land before the prose
claims counts (council), and per-row contract symbols give the freshness test a defined
input (council G3).

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. This
specification adds one module, three corpus rows and two fixtures; it adds no service, no
URL and no second hop, so the service-shaped boxes are `not applicable`. Boxes below are
ticked by the plan's gate tasks from command output, not from intent (council).

- [x] CI/CD — `just check` runs the new fixtures on every push (`.github/workflows/check.yml`); nothing here is deployed
- [x] Logs — not applicable, and that is the rule: every verb still emits the one JSON line `ai-eng digest` reads
- [x] Traces — not applicable, and that is the rule: one process, no second hop, no trace
- [x] Errors — not applicable: the new paths fail closed (out-of-declaration ⇒ `CANNOT DECIDE`, block; a `None` boundary is never coerced into a guessed class)
- [x] Health and data age — `tests/test_036_boundary.py` and `tests/test_036_validation.py` run in `just test` on every gate; `tests/skill_eval.py` counts the new corpus cases
- [x] External check — `.github/workflows/check.yml` runs the whole gate on every push; the corpus cases ride the generic `skill_eval.py` routing lane, the independent reader
- [x] Second path — the module is read by its fixture and the corpus rows are read by `skill_eval.py` with no shared line; `test_036_validation.py` is the independent reader over the validated modules
- [x] Security — `just security`: gitleaks, semgrep and trivy on every push, over a change that adds no dependency and no network call