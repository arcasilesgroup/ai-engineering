---
id: "029"
slug: evidence-executed-and-answer-keys
status: draft
date: 2026-08-25
ref: ""
supersedes: "010"
---

# Evidence executed and answer keys governed

## Who this is for, and what it is worth to them

The person who runs `/ai-goal` on this repository and approves what it produces, and every
stranger who installs the wheel for a repository they are accountable for. The research goal
(`.ai/reports/018`) audited sixteen external references and marked, across four of them, the
same gaps this repository does not yet close: it does not measure whether its own review
skills detect what they claim; it has no answer key decided before a gate runs; it has no
verifier that re-executes rather than trusts; and it has no cost gate before expensive work.
This specification supersedes parts of spec 010's target to close the **verification and
cost** half of those gaps in one reviewed, TDD'd increment (the research paquete 1: its N1,
N2, N3 and N7).

Nothing here grants authority, adds a service, or creates a second control plane. It adds
four checked behaviours to the existing backbone: evaluation of review skills, an answer key
artefact, re-execution of claimed verification, and a cost calibration gate.

## Context and problem

**What is true today, measured in this tree on 2026-08-25:**

- `tests/adversarial/run.py` attacks the guards with planted cases and demands, for each, a
  clean control that must not fire. It proves the **guards** detect what they claim. It says
  nothing about whether the **review skills** (`ai-review`, `ai-security`, `ai-verify`) find
  the defects a review is for (the research N1) — this is the largest gap.
- `tests/ledger_run.py` + `docs/requirements.toml` already run "every command the ledger
  calls proof" and write receipts. This is a partial answer key, but it answers the
  *framework's* requirements at a fixed age; it is not a per-deliverable answer key decided
  before the work starts (wayfinder's pattern, N3).
- The check/evidence schema (spec 010) requires digests and freshness on every check record,
  and `--recheck` exists in no tool here: nothing re-executes a *claimed* verification
  without trusting the claim that it passed. unlazy's `--recheck` + `EVIDENCE:pending =
  UNMET` rule (N2) is the missing half.
- The CLI has ten verbs and `just check` runs the gate; there is no `--limit`/calibration
  step before a pipeline whose agent cost scales with the tree (deepsec `calibrate.sh`,
  headstart's ArXiv gate — N7). A user can point a costly run at a large repository with no
  cost projection and no confirmation.
- The inherited red: `madr.validate` returns `INCOMPLETE [MADR_SCHEMA_INVALID]` from ADR
  0025 of spec 026, documented in `.ai/reports/014`. Spec 029 does not authorize rewriting
  that history.

**The problem, in words a non-technical reader can follow:**

The guards that stop a dangerous action are tested. The skills that *judge* work quality are
not — nothing measures whether a review skill finds a planted bug or stays quiet on clean
code. There is no standard, decided before work starts, that a reviewer applies to the
delivered thing (an answer key). There is no re-run that ignores a claim that a check passed
and executes it again. And before a run that costs money, there is no step that says "this
will cost about this much — go ahead?" The four changes in this spec add those four missing
controls. They make the framework honest not just about preventing harm, but about whether
the judging it promises actually works, and about how much of your money it spends.

## Options considered

1. **Add the four controls as one reviewed superseding spec (chosen shape).** Each of N1
   (skill evals), N2 (recheck/evidence semantics), N3 (answer key artefact) and N7 (cost
   gate) lands as its own TDD task with a red fixture first, in dependency order: measure
   judgment before shaping the artefact it informs. Gives: a target extension of spec 010
   that states *what* is now checked before *how*; each control owns its fixture. Costs: a
   wide block; mitigated by the plan splitting it into atomic commits, one change each.
   Rules out: none of the four is weakened.

2. **Do them as four separate specs.** Gives: smaller reviews. Costs: N2 and N3 are one
   mechanism (a decided standard + re-executing it), N1 measures skills the other two will
   make checkable; splitting them forces re-arguing the same evidence-vs-claim rule four
   times. Risks: the research's ordering — measure before you assert — is lost.

3. **Ship skill evals now, defer answer key / recheck / cost gate.** Gives: a smaller first
   block. Costs: an evaluation of skills with no way to record and re-execute its standard,
   and no cost protection before the most expensive lanes; this is the high cost of
   discipline the research measured without the gate that makes it affordable. The user's
   instruction was that nothing in the goal is a ceiling and the goal is the single law —
   there is no reason to defer reachable work.

## Decision

**Option 1**, as paquete 1 of the research. The spec supersedes spec 010 only where it
extends the target with the four behaviours below; it does not weaken, drop or relabel any
normative requirement 010 already states. Each behaviour is closed, versioned, and comes
with both a positive fixture and a nearby clean control. The four are:

### B-029-1 — Evaluation of review skills against planted defects (research N1)

A review-skill evaluation harness `tests/evals/` with a `plant` half that injects a known,
*independently graded* defect pack into a clean fixture tree (answer key written **outside**
the tree, so a skill that reads the list of bugs cannot fake a pass) and a `score` half that
reports per-skill **recall** and **precision**. Defects use the three tiers the research
measured as load-bearing:

- **Tier 1 (gimmes)** — prove the skill runs and reports at all;
- **Tier 2 (near-misses)** — plausible code that is wrong; prove recall against a skill that
  only greps;
- **Tier 3 (traps)** — correct code that pattern-matches a defect; prove the skill does not
  fire on code that is fine.

Every reviewed skill that owns a defect class (`ai-review`, `ai-security`, `ai-verify`;
their audit lanes) has at least one pack with recall **and** precision floor. A review skill
that reports nothing on a pack that contains defects, or reports findings on a clean control,
is `FAIL`. The harness writes a check-evidence receipt like every other executed lane, and
`just check` runs it. Cross-skill scoring is per-skill, never merged into one number that
hides a zero.

### B-029-2 — Answer key decided before a gate runs (research N3)

`ai-spec` flow gains an **answer key** output: the spec's observable requirements become a
machine-readable list of binary checks, each with `judged_by` (`run it` or `a/b pick`),
attached to the committed spec. It is immutable during execution — it travels with the spec
digest. A reviewer (human or agent) applies it to the delivered work:

- every check reports `PASS` → the deliverable meets the decided standard;
- any check reports `FAIL` → `FAIL`;
- a check whose observable was **unknown** or un-specified → `BLOCKED: U<n>`, never an
  invented score.

The answer key does not replace tests — tests are a subset of `run it` checks. It adds the
checks tests cannot hold, and it records the "unknown" honestly instead of pretending. The
existing `docs/requirements.toml` ledger becomes a *kind* of answer key; the new artefact is
per-deliverable, decided in `ai-spec`, and consumed by `ai-verify`/`ai-ship`.

### B-029-3 — Re-executed verification; claimed-is-not-passed (research N2)

A recheck mode over the check/evidence schema: before a green is claimed, an orchestrator or
gate may `--recheck`, which ignores what any claim or checkbox says, re-executes the named
command against the named input and artifact digests, and resets evidence to
`INCOMPLETE`/`pending` on mismatch or failure. The rule "a marked check with no executed,
fresh evidence is `UNMET`, not passed" becomes a checked semantic across the ledger, the
evals harness and the answer-key consumer. The verification of a claim is never delegated:
the parent re-runs, it does not relay a child's summary.

### B-029-4 — Cost calibration gate before expensive lanes (research N7)

The CLI and `just check` gain a calibration step for operations whose agent/run cost scales
with the tree: `--limit <n>` runs a small, bounded batch first, projects total cost and
wall-time from observed samples, and refuses to continue without confirmation above a
declared threshold or when asked non-interactively and un-authorized. A `doctor` pre-run
verifies prerequisites (config, credentials, git, pinned engine versions) before a costly
lane starts, rather than mid-run.

## Challenged once

**"The framework does not pay for verification, so a cost gate is scope creep."** The cost
gate is not about the framework's own CI — it is about the *user's* runs: an orchestrator
user points at a 5k-file repo and spends four figures with no warning. deepsec measured
$500-$1,200 for 2,000 files and its own docs warn the calibration is voluntary. Here it is a
gate: bounded-sample first, confirm, or refuse. That is not creep; it is the difference
between a tool a company trusts with its budget and one it learns to fear. The threshold
lives in `policy/`, is checked, and fails closed when consent is required but absent.

**"An answer key is a plan another way; we already have specs."** A spec says *what should be
built*; an answer key says *how you will know the delivered thing is right*, in binary
checks. wayfinder's insight (research): a plan cannot be falsified, an answer key can. The
key sharpens the spec's existing "observable BDD examples" into a decided, machine-readable
standard that `--recheck` can execute — which is precisely the evidence-vs-claim rule this
tree already runs on.

## Assumptions and unresolved risks

- Assumption: the three skills named in B-029-1 can each name the defect class they own,
  and a tier-3 clean control can be written that genuinely masks a defect. If a skill has no
  defensible pack, its row says `no_instrument` with the reason (the pilot-register's honest
  shape) rather than inventing a number.
- Unresolved: an alternatives `a/b pick` check needs a judge (human or model) and has no
  fully automated CI path — the research flagged this in wayfinder. Spec 029 records the
  check type and its `BLOCKED` state; automated taste-judging is later work, not this block.
- Unresolved: the inherited `madr.validate` red from ADR 0025. This spec does not authorise
  rewriting that history; the reconciliation follows the `--recheck` semantics it introduces.
- Assumption: the answer key lives beside the spec it judges and is referenced by digest, so
  it cannot drift from the committed requirement text.

## Examples somebody can check

Given a skill-eval pack with a Tier-2 defect planted in a clean fixture and an answer key
written outside the tree,
When `just check` runs the evals lane,
Then the skill that owns the class is scored, the planted defect is counted in recall, and
a skill reporting nothing on a non-empty pack is `FAIL` (`uv run python tests/evals/score.py`
→ `RAN evals=pass`).

Given a spec carrying an answer key with a `run it` check,
When the deliverable is reviewed after `--recheck`,
Then the check is re-executed against the named digests and a claim that it passed is not
trusted; a mismatch is `INCOMPLETE`, never `PASS` (`uv run --with pytest==9.1.1 pytest -q
tests/test_recheck.py` → `1 passed`).

Given the evals harness and a clean control,
When the clean (tier-3) tree is scored,
Then the skill that owns the class reports no finding on it or loses precision; a skill that
fires on correct code cannot pass `just check` (`uv run --with pytest==9.1.1 pytest -q
tests/test_evals_harness.py -k clean` → `1 passed`).

Given `policy/` declares a cost threshold and a non-interactive run would exceed it,
When the pipeline is invoked without authorization,
Then it refuses with `INCOMPLETE` and runs nothing beyond the bounded sample (`uv run --with
pytest==9.1.1 pytest -q tests/test_cost_gate.py` → `1 passed`).

Given the answer-key consumer,
When a deliverable touches an `U<n>` unknown named by the key,
Then the verdict is `BLOCKED: U<n>`, never a fabricated score or a silent pass (`uv run
--with pytest==9.1.1 pytest -q tests/test_answer_key.py -k blocked` → `1 passed`).

## Decisions

**D-029-01 — the review skills are evaluated against planted defects with recall and
precision, tiered gimmes/near-misses/traps, answer key outside the tree.**
Rationale: the guards are already mutatively and adversarially tested; the judging skills are
not (research N1, graph-engineering + astryx `clean-stays-quiet`). A skill whose number of
detections is never measured is a green nobody earned.

**D-029-02 — the `ai-spec` flow emits a machine-readable answer key, decided and immutably
digest-bound, consumed by `ai-verify`/`ai-ship` with a `BLOCKED: U<n>` verdict for unknowns.**
Rationale: wayfinder's falsifiable-standard pattern closes the "spec says what, judge says
nothing" gap; the existing requirements ledger proves the command-execution half already
works, and this keys it to a per-deliverable standard.

**D-029-03 — verification is re-executed, not relayed: `--recheck` + "claimed is not
passed" are checked semantics across ledger, evals and answer-key consumer.**
Rationale: unlazy's measured lesson is that auto-certification is the failure to catch; the
parent re-runs and never trusts a child's summary (research N2, model-router).

**D-029-04 — expensive lanes carry a bounded-sample cost calibration gate with a
`policy/`-declared threshold and fail-closed confirmation; `doctor` pre-runs prerequisites.**
Rationale: deepsec/headstart both proved that un-gated agent cost surprises users; an
orchestrator user must not meet a four-figure bill with no warning (research N7).

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. This
specification changes the gate: an evals harness, an answer-key consumer, a recheck mode
and a cost-calibration pre-run; it adds no service, no URL and no second hop, so the
service-shaped boxes are `not applicable`.

- [x] CI/CD — `just check` runs the four behaviours on every push (`.github/workflows/check.yml`), and the evals lane writes its check-evidence receipt like every other executed lane; nothing here is deployed
- [x] Logs — not applicable, and that is the rule: this spec adds check lanes, not stages; every verb still emits the one JSON line `ai-eng digest` reads
- [x] Traces — not applicable, and that is the rule: one process, no second hop, no trace
- [x] Errors — not applicable: the new code paths are gate lanes that fail closed — an unevaluable review skill, an unknown answer-key observable and an unauthorized costly run each end the gate red rather than inventing a score
- [x] Health and data age — `just evals` re-plants the defect packs and re-scores on every gate, and `just cover` re-checks the answer key against the tree, so the evidence cannot go stale without the gate saying so
- [x] External check — `tests/evals/` grades each review skill against independently-graded defect packs whose answer key lives outside the fixture tree (`tests/evals/answer-keys/`), so a skill that reads the list of bugs cannot fake a pass; the cost lane's `doctor` pre-run verifies prerequisites before the expensive lane starts
- [x] Second path — the answer key is decided in `ai-spec` and consumed by `ai-verify`/`ai-ship` (two routes that share no line), and the evals receipt is written by the harness and re-read by `just check`; the declared coverage rules are separated from prompts so the two cannot drift
- [x] Security — `just security`: gitleaks, semgrep and trivy on every push, over a change that adds no dependency and no network call