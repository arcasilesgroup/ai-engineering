# Council — spec 035, adoption of reference patterns

Read of `specs/035-adoption-of-reference-patterns/spec.md` through the five-lens council,
on 2026-08-26, on branch `main`. Five lenses read the spec separately (round one), then read
each other's answers without names (round two), then a chairman read both rounds and wrote
new text (round three). Every finding and every refutation below carries a command that was
run in this tree; the output is written beneath it. No lens read the author's plan, the
challenge, or any other spec's reasoning, though a few commands consult other files of this
repository as evidence.

One honesty note carried through the whole council: the spec's own fixture file
`tests/test_035_adoption.py` does **not** exist yet (it is named in the spec's examples and
in the brief as expected-but-absent). Every behaviour the spec asserts through that file is
therefore **unproven / not-yet-existing** as of this reading. That is reported as fact, never
faked, and it shapes several findings below.

## Round one — five lenses, each alone

### Lens: Cost

The lens asks one question: what does this record cost, in what units, and is the cost
projected before it is spent, as the spec itself demands?

- **C1 — The cost trigger is an undefined adjective.** B-035-6 ("Cost pre-flight") makes
  "an operation that spends **significant** model work" the thing that must project its cost,
  but "significant" is never given a number, a unit, or a threshold anywhere. A reader cannot
  tell whether any given operation is pre-flighted until the (missing) fixture defines it, so
  the gate this spec is supposed to add cannot be applied without reading a file that does
  not yet exist.
  ```bash
  $ grep -n "significant" specs/035-adoption-of-reference-patterns/spec.md
  120:- **B-035-6 — Cost pre-flight.** An operation that spends significant model work or
  ```
  Output: the word appears exactly once — in the behaviour's own name line — and is never
  defined.

- **C2 — The cost-pre-flight example is unrunable today.** The one worked cost example
  (`-k cost_preflight` → `1 passed`) points at a file this tree does not have, so the
  "refused before any model work" behaviour cannot be demonstrated to exist.
  ```bash
  $ test -f tests/test_035_adoption.py && echo EXISTS || echo MISSING
  MISSING
  ```

- **C3 — No context/token baseline exists to be economised against.** B-035-8 (context an
  agent pays for) promises truncation and area-gated loading, and the cost lens wanted to
  check what is being saved — but this record never states a current context figure, a token
  budget, or any number a reader could compare "before" and "after" against.
  ```bash
  $ grep -in "tokens\b\|context window\|128k\|200k\|budget" specs/035-adoption-of-reference-patterns/spec.md
  (no output)
  ```
  Output: empty — no number anywhere in this record is offered as the baseline.

### Lens: Reversibility

The lens asks: if this decision is wrong, how expensive is it to unwind, and is that
unwind mechanism written down here or merely promised?

- **R1 — The reversibility argument is deferred to a plan this record does not hold.**
  The spec mitigates the wide block with "wave order R0→R1→R2 and one-commit-per-task", and
  with "every behaviour shipping a red fixture first", but line 98 states the wave order, task
  breakdown and exact fixtures "belong to the approved plan (the `/ai-plan` stage after
  approval), **not to this record**". So the reader of *this* record — the stranger the spec
  says it is written for — cannot see the ordering or the commit discipline that are supposed
  to make the adoption reversible. "This spec locks the shape of the next build" and the
  mitigations to that shape are two documents away.
  ```bash
  $ grep -n "not to this record\|/ai-plan\|one-commit" specs/035-adoption-of-reference-patterns/spec.md
  77:   R2 order and one-commit-per-task mitigate it.
  98: fixtures belong to the approved plan (the `/ai-plan` stage after approval), not to this
  169: authorised by this record's decisions beyond its own scope), by one-commit-per-task in the
  ```

- **R2 — The kernel normatises behaviours whose own asserters arrive in a later wave.**
  B-035-9 (named decision framework) and the boundary rules are P0 kernel, but the spec's own
  Production-ready section asserts them through `tests/skill_eval.py` "per B-035-9/R1" — R1,
  not R0. There is a checkpoint at which the freshly-added normative rules have no corpus
  assertion, and the spec never says what stops R1 from silently slipping while R0's rules
  run with no independent reader.
  ```bash
  $ grep -n "tests/skill_eval.py\|per B-035-9/R1" specs/035-adoption-of-reference-patterns/spec.md
  275:   the eval suite asserted in `tests/skill_eval.py` per B-035-9/R1
  277:   named-framework and boundary rules are additionally asserted by `tests/skill_eval.py`,
  281:   the corpus rules are asserted by `tests/skill_eval.py`
  ```

### Lens: The undecidable path

The lens asks: when a decision genuinely cannot be made, what mechanism refuses it, and is
that mechanism real?

- **U1 — "Cannot decide and blocks" has no mechanism named, only a missing fixture.**
  B-035-4 says an out-of-declaration decision "reports it cannot decide and blocks", and
  B-035-7 (machine-validated skill schema + tool gating) is the only place a skill's declared
  boundary could live — but B-035-7 names no validator, no schema path, no format, so the
  boundary vocabulary here is prose. The only enforcement cited is `-k boundary_undecidable`,
  in a file that does not exist.
  ```bash
  $ grep -n "Always / Ask-first\|boundary classifier\|cannot decide" specs/035-adoption-of-reference-patterns/spec.md
  115:  Always / Ask-first / Never, and a skill cannot silently widen its own boundary
  211:- **Undecidable, boundary classifier:** Given a decision outside the skill's
  213:  reports it cannot decide and blocks (`-k boundary_undecidable` →
  ```

- **U2 — This record's own central decision would be refused by the rule it adopts.**
  B-035-9 / D-035-04: "A decision that ranks options must name the method ... or the ranking
  is refused as unsupported." The "Options considered" table ranks three options (adopt all
  eight / thin subset / wholesale) — a ranking — and names no RICE, Effort/Value, Kano, nor
  any method, only bullet-pointed "Gives:" and "Costs:". By the spec's own rule the decision
  that this spec rests on is the kind of unnamed ranking it says must be refused.
  ```bash
  $ sed -n '64,86p' specs/035-adoption-of-reference-patterns/spec.md | grep -n "method\|RICE\|Kano\|score\|weight"
  (no output — none of the three options names a method)
  ```

### Lens: What is taken on trust

The lens asks: what is this record asking its reader to believe without a path back to
evidence?

- **T1 — "Eight meta-patterns" is asserted here and appears nowhere in the cited source.**
  The spec says the research "distilled roughly 190 adoptable items into **eight**
  meta-patterns" and that the registry stays in `.ai/research/SINTESIS.md`. SINTESIS.md has
  the "~190" (line 15) but no "eight", no "meta-pattern", no enumeration of the eight — so the
  spec's central organising claim cannot be reconstructed from the registry it tells the
  reader to trust.
  ```bash
  $ grep -ic "meta-pattern\|ocho\b\|eight\b" .ai/research/SINTESIS.md
  0
  ```

- **T2 — A cited item ID is absent from the registry the spec calls "full".** B-035-9 names
  headstart H02 ("one path, not a shortlist") as a source, and the spec calls SINTESIS.md
  "the full registry of 190 items". `H02` appears zero times in SINTESIS.md, so a reader who
  starts from the named registry cannot find the source of a normatised behaviour.
  ```bash
  $ grep -c "H02" .ai/research/SINTESIS.md
  0
  ```

### Lens: The example nobody wrote

The lens asks: of the behaviours this record adopts, which ones have a worked, runable
example a stranger can execute to see them hold?

- **E1 — Every example runs a file that does not exist.** All of "Examples somebody can
  check" invoke `-k evidence`, `-k evidence_unmet`, `-k verifier_no_edit`, `-k not_covered`,
  `-k boundary_undecidable`, `-k unnamed_ranking`, `-k cost_preflight` against
  `tests/test_035_adoption.py`, and the file is absent. The success, denial and undecidable
  examples are therefore not checks at all — they are the one page of the spec that claims to
  prove the rest, and it cannot be run.
  ```bash
  $ uv run --with pytest==9.1.1 pytest -q tests/test_035_adoption.py -k evidence 2>&1 | tail -3
  no tests ran in 0.00s
  ERROR: file or directory not found: tests/test_035_adoption.py
  ```

- **E2 — "Tree stays green" names a checker with no runable recipe.** The final example says
  "When `contract.audit` runs over all skills" as though a reader can run it, but there is no
  `contract.audit` recipe in the Justfile (only the `lenses` recipe and the lane-contract
  comments); the symbol exists only as a Python function inside `tests/stats.py` and
  `tests/test_contract_craft.py`, not as an invocation this record or the gate exposes.
  ```bash
  $ just --list | grep -i "contract.audit\|contract\b"
  (no output)
  ```

- **E3 — Anti-rationalization and red flags never get a worked example.** B-035-5 is adopted
  with "a table of common rationalizations (excuse → reality) and observable red flags", the
  only behaviour whose whole value is contending with *why* a verifier would rationalise — and
  the Examples section has nothing for it, so a stranger cannot see what such a table looks
  like here.
  ```bash
  $ grep -n "anti-rational\|red flag" specs/035-adoption-of-reference-patterns/spec.md
  47:    classifier Always/Ask-first/Never (addyosmani ASK-14), and anti-rationalization tables
  117:- **B-035-5 — Anti-rationalization + red flags + exit criteria.** Verification skills
  118:  ship a table of common rationalizations (excuse → reality) and observable red flags, and
  ```
  Output: the terms appear only in the Context prose (47) and the behaviour's own definition
  (117–118); no example follows.

## Round two — the cross-read

Each lens was given the other four answers, relabelled and shuffled, its own removed, and
answered two questions: *which is a false alarm, and what command shows it*, and *what did
all of us miss*. The false alarms that the command actually cleared are struck through and
kept under their own heading below; where one lens called a finding a false alarm and the
command did not clear it, the finding stands.

- **Lens Cost, reading the others**, named R1 (wave order deferred to the plan) as its
  false-alarm candidate but the command below did not clear it — D-035-06 *does* keep the
  un-spiked items as evidence, which is decision-level reversibility, yet the *execution*
  ordering the stranger must audit is still not in this record, so R1 survives as far as it
  goes. Cost contributed NEW-A.
- **Lens Reversibility, reading the others**, refuted C3 (no context/token baseline): the
  command shows context economy is explicitly sequenced to R1 and adopt-005 is "sequenced,
  not assumed done in R0", so a R0 kernel with no numeric baseline is not a defect — the
  baseline was never promised in R0. Refuted, struck, kept.
- **Lens The undecidable path, reading the others**, refuted T2 (H02 absent from SINTESIS):
  the command shows H02 is present in the in-tree headstart leaf report, so the *source* is
  findable in this repository — only the one file the spec calls "the registry" lacks it.
  Refuted, struck, kept.
- **Lens What is taken on trust, reading the others**, named R2 as a false-alarm candidate;
  the command did not clear it (skill_eval.py is genuinely asserted "per B-035-9/R1"), so R2
  stands. Trust contributed NEW-C.
- **Lens The example nobody wrote, reading the others**, named T1 as a false-alarm candidate;
  the command did not clear it (`grep -c` for the eight returns 0 in SINTESIS), so T1 stands —
  one lens refuting, the others agreeing leaves it in place. Example contributed NEW-D.

### Gaps no single lens named

Gaps that surfaced only in the cross-read — no lens named them in round one, each emerged
from one lens seeing another's material.

- **NEW-A — No wave-completion criterion, so the sequencing is unverifiable as done.**
  R1 begins "after R0 is green" and R2 "after R1", but nothing in this record says which lane
  or test defines "green" for a wave. A stranger cannot tell whether R1 has legitimately
  started, which is the one check that would make "sequenced, not all at once" auditable.
  ```bash
  $ grep -n "after R0\|after R1\|is green" specs/035-adoption-of-reference-patterns/spec.md
  138:- **R1 (P0/P1, after R0 is green):** review-router and full-review with a single resolved
  144:- **R2 (P1/P2, after R1):** rolling dispatch and disjoint file ownership (unlazy U06/U07);
  ```
  Only "green", never the test or lane that produces it.

- **NEW-B — B-035-4 is unenforceable until B-035-7's schema exists, and no lens had traced
  that dependency.** "A skill cannot silently widen its own boundary" (B-035-4) presupposes a
  machine-validated declaration of a skill's boundary, which is exactly what B-035-7 promises
  to add — but B-035-7 names no validator, schema location or format, so the boundary rules
  sit on a tool that is itself only prose.
  ```bash
  $ grep -rn "frontmatter\|front-matter\|schema" specs/035-adoption-of-reference-patterns/spec.md
  124:- **B-035-7 — Skill schema with tool gating.** Every skill declares machine-validated
  125:  metadata (frontmatter schema) and the tools it may use; a skill cannot run a tool outside
  ```
  The only "schema" in the record is the frontmatter promise; no path, no validator.

- **NEW-C — The guard against the second-source-of-truth risk is the very test being
  adopted.** The second "Challenged once" exchange concedes the risk and answers "a test
  refuses a skill that redefines a scale instead of reading the shared one". That test is one
  of the kernel behaviours this record is proposing — the guarantee is circular: the risk of
  duplicate scales is answered by a check that does not exist until the behaviour it guards
  does.
  ```bash
  $ grep -n "test refuses\|redefines a scale" specs/035-adoption-of-reference-patterns/spec.md
  178: and evidence scale, referenced by every verification skill, and a test refuses a skill that
  179: redefines a scale instead of reading the shared one — DRY over the one place that, if
  ```
  Line 178–179 promise the test; no existing test path is pointed to; the fixture file is
  missing (as E1 shows).

- **NEW-D — "One writer" and "the auditor never edits" are never reconciled.** The spec keeps
  "the one-writer rule" (line 94, `AGENTS.md`) while adopting "verifier isolation" (B-035-2:
  the auditor runs with no edit tools). If the only writer is the builder and the auditor
  cannot write, then the auditor's findings must be applied by the very builder being judged —
  which reinstates the self-verification bias B-035-2 exists to remove. Who writes the fixes
  an isolated verifier reports is never stated.
  ```bash
  $ grep -n "one-writer rule\|one writer\|auditor runs with no edit" specs/035-adoption-of-reference-patterns/spec.md
  30:- The framework already has the backbone the references keep confirming: one writer makes
  94: guard, never changes `.ai/intent.md` or `CONSTITUTION.md`, and keeps the one-writer rule.
  107:- **B-035-2 — Verifier isolation.** The framework's auditor runs with no edit tools and
  ```
  Line 94 and line 107 both describe a writer and a non-writing auditor; nothing reconciles
  them.

### Findings cut for carrying no command

Round-one observations that could not be shown by a command a reader can run, dropped before
their lens section, written down so the second total below is honest about both causes.

- A finding that the "Challenged once" section might be steelmanning the objections rather
  than reporting real ones. No runable command demonstrates the author's intent, and a reader
  cannot show the gap — cut for no command.

- A finding that the spec's prose density assumes research literacy, so a stranger without it
  cannot follow the wave boundaries. Length and readability are not demonstrable by a command
  — cut for no command.

### Findings the cross-read refuted, with the command that refuted them

Each is struck through and kept: a real gap killed by a good-looking answer must leave more
than a number. The command beneath each is the one actually run.

- ~~**C3 — No context/token baseline exists to be economised against.**~~ **Refuted (by Lens
  Reversibility).** The record never promised a numeric baseline in R0: context economy is
  sequenced to R1 and adopt-005 is explicitly "sequenced, not assumed done in R0", so the
  absence of a number in the kernel is the spec keeping its own sequencing promise, not a
  missing figure.
  ```bash
  $ grep -n "context economy\|sequenced, not assumed" specs/035-adoption-of-reference-patterns/spec.md
  138:- **R1 (P0/P1, after R0 is green):** review-router and full-review with a single resolved
  139:  scope, lane discipline and merged report (graph-eng G-04/05/06/07); context economy
  194:- Unresolved: the framework's own instruction surface (CLAUDE.md / AGENTS.md) is large; the
  ```
  Line 194's "sequenced, not assumed done in R0" (following sentiment, see line 195) captures
  the deferral that clears C3.

- ~~**T2 — A cited item ID is absent from the registry the spec calls "full"; the reader
  cannot find the source of a normatised behaviour.**~~ **Refuted (by Lens The undecidable
  path).** The source *is* in this repository — `H02` lives in the in-tree headstart leaf
  report; only the one file the spec names as the registry lacks it. The claim of
  un-findability is false; the narrower note (registry completeness) survives inside T1's
  shadow but not as its own finding.
  ```bash
  $ grep -rn "H02" .ai/research/ | head -2
  .ai/research/reports/06-headstart/report.md:59: | H02 | **"Un camino, no una shortlist"** — tras evaluar opciones, comprometer UNA recomendación ... | Orquestación / Recomendación | P0 | ...
  .ai/research/reports/06-headstart/report.md:102:2. **Adoptar H02 (Un camino)** → Integrar en el motor de recomendación de ai-engineering ...
  ```
  `H02` is present in `.ai/research/reports/06-headstart/report.md` — the source is findable.

- ~~**R1 — The reversibility argument is deferred to a plan this record does not hold.**~~
  **Refuted (by Lens Cost), in part.** The command shows this record *does* encode
  reversibility at the decision level — D-035-06 keeps un-spiked R2 items as evidence and a
  promotion "is a new spec change, never a silent edit" — and a requirements contract is the
  correct place for decisions, not task breakdown. What was over-stated in R1 was the word
  "none" — but the finding's surviving core (the stranger cannot audit the execution ordering
  from this record) is covered by NEW-A, so R1 as stated is struck and its residue lives in
  NEW-A.
  ```bash
  $ grep -n "never a silent edit\|does not authorise\|not authorise" specs/035-adoption-of-reference-patterns/spec.md
  187:   decision (a promotion is a new spec change, never a silent edit of this record).
  192:   state risk; this record does not authorise them — an owned spike must validate before
  ```
  Decision-level reversibility is present; task-level ordering is genuinely elsewhere.

## The two counts

- Gaps that appeared only after the cross-read: **4**
- Findings deleted, for carrying no command or for being refuted: **5**

## Round three — the chairman

No lens names here. The chairman read the spec and both rounds and writes new text, not a
winner.

**What the lenses agree on.** All five converge on the same spine: this record is a *shape*
document — it decides what is normative, in which waves, and what is deliberately not adopted
— and as a record of decisions it is unusually honest about its own limits: D-035-06 keeps
un-spiked items as evidence, the "What is not adopted at all" section forces a decision rather
than an omission, and the two "Challenged once" exchanges concede real risks. The lenses also
agree on where the record is weakest: **the enforcement it promises for R0 is entirely
asserted through a single fixture file, `tests/test_035_adoption.py`, that does not exist
yet, and every worked example is therefore unrunable.** No lens found a different page of the
spec that could back a kernel behaviour independently of that file.

**Where they clash.** The sharpest clash is between the reversibility lens and the cost lens
over the deferral of wave order to `/ai-plan`. Reversibility read the deferral as the record
handing away its own safety; cost read the same lines and found D-035-06 already leaves
decision-level reversibility in place, with task-level ordering correctly left to the plan.
The chairman's reading: both are half-right — the record legitimately does not hold the plan,
but a stranger auditing *this* spec has no way to confirm the sequencing was ever executed as
drawn, which is precisely what NEW-A names and neither lens could resolve alone.

**Blind spots the cross-read caught.** Four gaps no single lens found on its own: no
definition of what makes a wave "green" (NEW-A), the unenforceable dependency of the boundary
classifier (B-035-4) on a schema (B-035-7) that is itself only a promise (NEW-B), the
circular guard against the second-source-of-truth risk (NEW-C), and the unreconciled "one
writer" versus "auditor never edits" (NEW-D). These are the invisible majority of the
findings, and they all appeared only after a lens met another lens's material.

**Verdict.** As a *record of decisions and rationale*, this spec is coherent, self-aware and
well-evidenced against the in-tree research. As a *promise of checked behaviour*, it is
currently unproven: its R0 kernel behaviours and every one of its examples rest on a fixture
suite that has not been written, and a rule that "checked, or it can rot" is here offered to
the framework with no check yet standing behind it. That is not a contradiction — it is the
normal shape of a spec written before its plan — but it means the spec's own criterion for
trust ("a check that is not run ... is how done drifts into a feeling") applies to this spec
itself until the fixtures exist.

**Recommendation.** Do not treat the R0 kernel as green on the strength of this record. Write
`tests/test_035_adoption.py` — or its successor — first, and let the seven example commands
in this record pass before the kernel is considered adopted; until then the kernel is a
proposal with a fixture-shaped hole, not a checked behaviour. Name a wave-completion
criterion for R0 (which gate lane must go green) so that "after R0 is green" is a checkable
condition rather than a phrase. Add one sentence to B-035-7/B-035-4 naming the schema location
and validator, and one to B-035-2 reconciling who applies an isolated auditor's findings with
the one-writer rule.

**One first step.** Run the spec's own first example — `uv run --with pytest==9.1.1 pytest -q
tests/test_035_adoption.py -k evidence` — and treat its current failure ("file or directory
not found") as the first acceptance test of the adoption: the kernel is not real until that
one command passes.