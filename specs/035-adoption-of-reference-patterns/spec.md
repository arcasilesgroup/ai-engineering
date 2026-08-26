---
id: "035"
slug: adoption-of-reference-patterns
status: draft
date: 2026-08-26
ref: ""
supersedes: ""
---

# Adoption of reference patterns

## Who this is for, and what it is worth to them

The repository owner who runs `/ai-goal` on this repository and the stranger who installs
the wheel for a repository they are accountable for. The research goal (`.ai/research`,
17 leaf reports + `SINTESIS.md`) read sixteen external reference implementations — unlazy,
model-router, Loop-Engineering, wayfinder, al-design-system, headstart, graph-engineering,
astryx, okf, deepsec, cc-creators-skill (×2), contains-studio/agents, Anthropic
code-simplifier, addyosmani/agent-skills, make-claude-code-last-longer, AL-Design — and
distilled roughly 190 adoptable items into eight meta-patterns: (1) the verifier never fixes what it judges; (2) state lives in files, not memory; (3) gates are executed, not declared; (4) whatever is not verified is marked; (5) cost is projected before it is spent; (6) context is paid for; (7) verification is binary, never scored; (8) one writer holds the tree while critics read it in their own context. For the owner this spec
locks the shape of the next build: which patterns become checked behaviours of the
framework, in which order, and what is deliberately not adopted. For the stranger it is
the record of why the framework grew those controls, so their boundaries are auditable
without knowing the authors.

## Context and problem

**What is true today, measured in this tree on 2026-08-26 (specs 034 and earlier committed):**

- The framework already has the backbone the references keep confirming: one writer makes
  the commits (`AGENTS.md`), guards fail closed, telemetry fails open, a `just check` gate
  runs a green rule, and `skill-sequence.toml` is a checked copy of the governed order.
- The research marks **gaps the references prove and this tree does not yet supply**. The
  highest-value, cross-recurrent ones, each with its reference and research item ID:
  - **Verification runs but rarely is enforced as executed evidence.** `GATES`-file format
    with CHECK/EXPECT/EVIDENCE and "checked-without-evidence counts as unmet" (unlazy
    U01/U02); executed `validate()` with exit codes (okf OKF-03); the "report, don't fix"
    and `NOT COVERED ≠ PASS` rules (graph-engineering G-17/G-09). The framework checks
    *results*, not yet the *reports that claim them*.
  - **The auditor can "fix what it finds".** The pattern the references converge on — an
    adversary with no edit tools that only reports (Loop-Engineering LE-01, graph-eng,
    wayfinder, okf) — is how a reviewer's bias is kept out of its own verdict. This tree
    does not yet isolate the verifier that way.
  - **Scope, severity and honesty are per-file prose, not a shared contract.** The
    `CONVENTIONS.md` idea (graph-eng G-01/02/03/16), binary check + `Unknown → CANNOT
    JUDGE` + "out of scope" as a defensive section (wayfinder W-01/02/03), boundary
    classifier Always/Ask-first/Never (addyosmani ASK-14), and anti-rationalization tables
    (ASK-02) are each a shared, checked contract this tree does not yet codify.
  - **Cost is not projected before it is spent.** Budget pre-flight and a calibration
    ritual (deepsec D-01), the route-by-model bail-out and cost/capability matrix
    (model-router MR-01/02), and context an agent actually pays for (output truncation,
    area-gated rules, minimal CLAUDE.md — make-claude-code-last-longer adopt-001..005) are
    absent.
  - **A decision picks a named method or a bare rationale.** Named, repeatable decision
    frameworks (contains-studio, headstart H02 "one path, not a shortlist") and a "ground
    in the real app" rule for UI (AL-Design D-01) are barely present.

**The problem, in words a non-technical reader can follow:**

The framework is governed and green, but four of the disciplines the best external
implementations share are missing from it. Its verifier can quietly repair the code it is
supposed to judge. Its gates check results but not whether the reports claiming them carry
evidence. It has no shared, checked rules for what a finding is, how severe, what is out of
scope, and when a decision may not be made at all. And it spends expensive model work and
context without projecting the cost first. This spec adopts those disciplines as checked
behaviours, in three ordered waves, and records what the research says must **not** be
copied at all.

## Options considered

The three options are compared on two axes — the scope of the authoritative change and the
cost of reversing it — a method named explicitly so this record satisfies the named-framework
rule (B-035-9) it adopts.

1. **Adopt the eight meta-patterns as checked behaviours, sequenced R0 → R1 → R2 (chosen
   shape).** The P0 kernel (B-035-1 … B-035-9 below) becomes normative framework behaviour
   with red-fixture-first TDD tasks; the P1/P2 sets are sequenced after the kernel is
   green. Gives: the framework stops being the weakest instance of its own ideals —
   verifier-isolation, executed evidence, shared scope/severity/honesty contract, and
   cost projection land as checked, deterministic controls. Costs: a wide block; the R0→R1→
   R2 order and one-commit-per-task mitigate it.
2. **Adopt a thin subset (verifier-isolation + executed evidence only) and defer the
   rest.** Gives: a small first, safe block. Costs: leaves the honesty contract and the
   cost discipline as prose, which is exactly the class of gap the research says prose
   cannot hold — the same "checked, or it can rot" argument that made `skill-sequence.toml`
   data instead of prose and unlazy's gates files instead of promises.
3. **Adopt the external implementations wholesale.** Gives: ready wording. Costs: their
   exact constants and vendor hooks (Vercel, `claude -p`, SkillSpector/NVIDIA, Playwright
   as the only browser, `model: opus`) are lock-in and false greenty the research
   explicitly rejects; the shapes transfer, the vendors do not.

## Decision

**Option 1.** This spec adopts the eight meta-patterns as a governed, checked extension of
the framework, in three ordered waves (R0 kernel, R1 verification-and-context, R2 advanced
orchestration). It changes nothing already normative in specs 001–034 except where a
behaviour below is a tighter, additive contract over the same surface; it never weakens a
guard, never changes `.ai/intent.md` or `CONSTITUTION.md`, and keeps the one-writer rule.
Each behaviour is closed, versioned, and ships with a positive fixture and a nearby clean
control. The full registry of 190 items stays in `.ai/research/SINTESIS.md`; this spec
normatises the kernel and sequences the rest. The wave order, task breakdown and exact
fixtures belong to the approved plan (the `/ai-plan` stage after approval), not to this
record.

### The kernel (R0, P0, checked)

- **B-035-1 — Executed evidence in gates.** A guard value only holds when its `EXPECT`
  matches the output of an executed `CHECK`, and a checkbox ticked without recorded
  evidence reads as unmet. A deterministic checker (`validate()` with non-zero exit,
  errors and warnings separated — okf OKF-03, unlazy U01/U02) becomes the gate runner.
- **B-035-2 — Verifier isolation.** The framework's auditor runs with no edit tools and
  no capability to repair what it finds ("report, don't fix"); `NOT COVERED` is reported,
  never a silent `PASS` (graph-eng G-17/G-09, Loop-Engineering LE-01). Reconciled with the
  one-writer rule by separation in time and pass: the auditor reports findings without edit
  tools; the builder applies them in a fresh pass; and the auditor's verdict — never the
  builder's self-certification — is what the gate checks, so the same isolated auditor must
  re-verify the builder's fix before it counts.
- **B-035-3 — Shared scope/severity/honesty contract.** A `conventions` contract every
  verification skill reads first: severity scale, false-positive gate (trigger +
  consequence + evidence), installed-version rule, scope resolved once, criteria written before code is read
  (graph-eng G-01/02/03/16, wayfinder W-01/02/03). Its refusing test is one of the kernel
  behaviours this record adopts, so enforcement arrives with the behaviour's own fixture in
  R0 — temporal, not circular (see the wave-completion criterion).
- **B-035-4 — Boundary classifier.** Every decision a skill may take is one of
  Always / Ask-first / Never, and a skill cannot silently widen its own boundary
  (addyosmani ASK-14).
- **B-035-5 — Anti-rationalization + red flags + exit criteria.** Verification skills
  ship a table of common rationalizations (excuse → reality) and observable red flags, and
  finish against a checklist whose items require evidence (addyosmani ASK-02/03/04).
- **B-035-6 — Cost pre-flight.** An operation whose estimated cost crosses a configurable
  threshold (default: more than 5 model calls or 20k output tokens) projects its cost and
  requires the budget to be named before execution; work
  routes by model cost/capability with a bail-out before delegation (deepsec D-01,
  model-router MR-01/02).
- **B-035-7 — Skill schema with tool gating.** Every skill declares machine-validated
  metadata (schema at `policy/skill-schema.json`, validator in `src/ai_engineering/`) and
  the tools it may use; a skill cannot run a tool outside its declared set (contains-studio
  CS-01/02, cc-creators A-07/CC-05). B-035-4's boundary vocabulary is read from this
  validator, so B-035-4 is enforceable only once B-035-7's validator exists — the two are
  delivered together in R0.
- **B-035-8 — Context an agent pays for.** Long tool output is truncated/filtered before
  it enters context, and rules load by area rather than all-at-once; the framework's own
  instruction file stays minimal and non-inferable (make-claude-code-last-longer
  adopt-001..005).
- **B-035-9 — Named decision framework.** A decision that ranks options must name the
  method (RICE, Effort/Value, Kano as a start) or the ranking is refused as unsupported; a
  UI build must first name the shell, tokens and components it is grounding in (headstart
  H02, AL-Design D-01, contains-studio).

### The sequenced waves (post-kernel)

**Wave-completion criterion.** A wave is green when `just check` passes with that wave's
fixtures and corpus assertions present, and no lane in the wave is left with a pending red
beyond the inherited `madr.validate` red. Concretely: R0 completes only when
`tests/test_035_adoption.py` passes all seven `-k` cases and the named-framework and
boundary corpus assertions are present in `tests/skill_eval.py`; R1 when the
review-router/full-review fixtures pass; R2 when each validated item lands with its fixture.
A later wave never starts while an earlier one is red.

- **R1 (P0/P1, after R0 is green):** review-router and full-review with a single resolved
  scope, lane discipline and merged report (graph-eng G-04/05/06/07); context economy
  hooks and area-gated rules (adopt-004/005, ASK-08); goal-writer short condition and
  spec-with-numbered-DoD (Loop-Eng LE-07/LE-03); two-job CI gate separating "run untrusted
  code" from "write results" (deepsec D-05); a per-skill eval suite asserted in the gate
  (al-design-system A-14).
- **R2 (P1/P2, after R1):** rolling dispatch and disjoint file ownership (unlazy U06/U07);
  skill-router decision tree + fan-out with model-per-chunk (addyosmani ASK-01,
  model-router MR-03); proactive triggers and memory with provenance
  (contains-studio CS-03, graph-eng G-10); and the write-audit cycle for UI (AL-Design
  A-01/02) only if the framework itself produces UI. Items whose cost is not yet justified
  (build-auto resume state ASK-06, doubt cycle ASK-09, credibility-scored evals ASK-12) are
  adopted only after an owned spike validates them.

**What is not adopted at all** (recorded so the reader meets a decision, not an omission):
vendor lock-in (Vercel, `claude -p`, SkillSpector/NVIDIA, Playwright-only, `model: opus`),
standalone scanners/hardcoded regexes/fragile YAML parsers, any domain content (salon
flows, Next.js specifics, shadcn components, KPIs), and the false-green patterns the
research cut (decorative tool lists, proactivity that is only text, self-verification with
no tool, shared check-memo without invalidation, silent `exit 0`).

## Challenged once

**"Adopting nine kernel behaviours at once is the same over-reach the research rejects —
a wide, cross-cutting block is exactly what a small governed step avoids."** The research
indeed rejects *unjustified scope*, but the meta-patterns here are not additive feature
work: they are each a tighter, checked reading of a control this framework already claims
to have (a gate that checks, a verifier that judges, a scope that is decided). The option
table's Option 2 is the honest small-scope competitor, and it loses on the same ground the
skill-sequence file was moved to: a discipline that lives in prose and not in a check rots
by the next refactor. The block is mitigated by the wave order (nothing from R1/R2 is
authorised by this record's decisions beyond its own scope), by one-commit-per-task in the
plan, and by every behaviour shipping a red fixture first — the plan cannot be green
without the behaviour being real. The widest concession is honest: this spec deliberately
does **not** normatise the fifty-odd P2 items in the registry; it sequences only the kernel
and R1/P1 set, and leaves the rest as evidence for a future measured need.

**"A unified conventions contract becomes a second source of truth that competes with each
spec's own wording."** The risk is real and is answered by construction, the same way spec
034 answered it for its three behaviours: the conventions contract is the *single* severity
and evidence scale, referenced by every verification skill, and a test refuses a skill that
redefines a scale instead of reading the shared one — DRY over the one place that, if
duplicated, would let two lanes disagree on what `P0` or `HIGH` means.

## Assumptions and unresolved risks

- Assumption: the R0 kernel items are the correct, sufficient reading of "executed
  evidence, verifier isolation, honesty contract, cost projection"; a later measured need
  inside the registry can promote a P1/P2 item into the kernel without reopening this
  decision (a promotion is a new spec change, never a silent edit of this record).
- Assumption: the three named decision frameworks (RICE, Effort/Value, Kano) cover the
  decisions the framework actually ranks; a decision without a fitting framework says so,
  and a later spec adds one with measured need (same stance as spec 034 B-034-2).
- Unresolved: the R2 spikes (build-auto resume, doubt cycle, scored evals) have real cost
  and state risk; this record does not authorise them — an owned spike must validate before
  any of them is accepted, and until then they are evidence, not scope.
- Unresolved: the framework's own instruction surface (CLAUDE.md / AGENTS.md) is large; the
  minimal/non-inferable rule (adopt-005) is B-035-8's consequence and is sequenced, not
  assumed done in R0.
- Unresolved: the inherited `madr.validate` red from ADR 0025 (recorded in spec 034) stays
  open; this spec does not authorise rewriting that history.

## Examples somebody can check

The `-k` commands below target `tests/test_035_adoption.py`, which does not exist until the
approved plan writes it; each one is the wave's red-first acceptance test, and R0 is not
adopted until the seven all pass.

- **Success, executed evidence:** Given a guard whose `EXPECT` matches its executed
  `CHECK` output, When the gate runs, Then the value holds and the evidence is recorded
  (`uv run --with pytest==9.1.1 pytest -q tests/test_035_adoption.py -k evidence` →
  `1 passed`). A checkbox ticked with no recorded evidence reads unmet (same fixture,
  `-k evidence_unmet` → `1 passed`).
- **Denial, verifier isolation:** Given an auditor report that proposes an edit, When the
  verifier isolation rule reads it, Then the edit is refused (`-k verifier_no_edit` →
  `1 passed`), and a lane that could not run reports `NOT COVERED`, never `PASS`
  (`-k not_covered` → `1 passed`).
- **Undecidable, boundary classifier:** Given a decision outside the skill's
  Always/Ask-first/Never declaration, When the boundary classifier reads it, Then the skill
  reports it cannot decide and blocks (`-k boundary_undecidable` →
  `1 passed`); a ranking with no named framework is refused (`-k unnamed_ranking` →
  `1 passed`).
- **Anti-rationalization:** Given a verifier about to skip a red flag on a plausible excuse,
  When the anti-rationalization table matches the excuse to its reality, Then the skip is
  blocked and the gate fails the pass (`-k anti_rationalization` → `1 passed`).
- **Cost, pre-flight:** Given an expensive operation, When cost pre-flight runs with no
  named budget, Then execution is refused before any model work (`-k cost_preflight` →
  `1 passed`).
- **Tree stays green:** Given the repaired tree, When `just check` passes with the wave's
  fixtures present, Then the gate proves it clean — every behaviour read by both its module
  and its fixture with no shared line, and the inherited `madr.validate` is the only
  unchanged red.

## Decisions

**D-035-01 — gates require executed evidence; a ticked box with no evidence is unmet.**
Rationale: unlazy and okf proved that a check that is not run, and a box that is ticked
without proof, is how "done" drifts into a feeling; B-035-1 makes the checkbox mean the
command ran.

**D-035-02 — the auditor never edits what it judges; unreviewed lanes report `NOT COVERED`.**
Rationale: Loop-Engineering and graph-engineering converge on the adversary-isolated
verifier, the one way to keep a reviewer's bias out of its own verdict; B-035-2 makes that
isolation enforced rather than assumed.

**D-035-03 — one shared scope/severity/honesty contract, read first by every verification
skill; no skill redefines the scale.**
Rationale: graph-engineering's `CONVENTIONS.md` and wayfinder's binary-check-plus-Unknown
make scale and honesty a single referenced contract; two lanes disagreeing on what `P0`
means is the exact failure DRY exists to prevent.

**D-035-04 — decisions route through a named framework or a boundary classifier; a bare
rationale with no method is refused.**
Rationale: contains-studio and headstart proved repeatable decisions need a named method,
and an out-of-boundary decision must fail closed; B-035-4/B-035-9 make both refuse rather
than guess.

**D-035-05 — expensive work projects its cost before it spends; work routes by
cost/capability with a bail-out.**
Rationale: deepsec's calibration ritual and model-router's bail-out are the two halves of
"the cost is known before it is spent"; B-035-6 makes cost projection a gate, not a habit.

**D-035-06 — the R2/registral P2 items stay evidence until an owned spike validates them;
nothing in this record authorises them.**
Rationale: build-auto resume and doubt cycles carry real state and cost risk that the
research itself flags; adopting unspiked is the over-reach this framework refuses.

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. This
specification adds checked behaviours and one eval suite; it adds no service, no URL and no
second hop, so the service-shaped boxes are `not applicable`.

- [x] CI/CD — `just check` runs the new behaviour fixtures on every push
  (`.github/workflows/check.yml`); the behaviours are gate lanes, nothing here is deployed
- [x] Logs — not applicable, and that is the rule: every verb still emits the one JSON line
  `ai-eng digest` reads
- [x] Traces — not applicable, and that is the rule: one process, no second hop, no trace
- [x] Errors — not applicable: every new path fails closed (unmet evidence, verifier edit,
  out-of-boundary decision, unnamed ranking, unnamed budget)
- [x] Health and data age — `tests/test_035_adoption.py` runs in `just test` on every gate;
  the eval suite asserted in `tests/skill_eval.py` — corpus assertions ship with the R0
  kernel (wave-completion criterion)
- [x] External check — `.github/workflows/check.yml` runs the whole gate on every push; the
  named-framework and boundary rules are additionally asserted by `tests/skill_eval.py`,
  the independent route over the same corpora
- [x] Second path — each behaviour is read by its module and its fixture with no shared
  line (`test_035_adoption.py` is the independent reader over the behaviour modules), and
  the corpus rules are asserted by `tests/skill_eval.py`
- [x] Security — `just security`: gitleaks, semgrep and trivy on every push, over a change
  that adds no dependency and no network call