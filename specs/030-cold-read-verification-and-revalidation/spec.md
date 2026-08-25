---
id: "030"
slug: cold-read-verification-and-revalidation
status: draft
date: 2026-08-25
ref: ""
supersedes: "010"
---

# Cold-read verification, coverage rules and revalidation

## Who this is for, and what it is worth to them

The person who runs `/ai-goal` on this repository and approves what it produces, and every
stranger who installs the wheel for a repository they are accountable for. The research goal
(`.ai/reports/018`) marked, and spec 029 closed the first half of, five gaps this repository
did not cover. This specification supersedes parts of spec 010's target to close the
**verification and cost** second half in one reviewed, TDD'd increment (the research paquete
2: its N4, N8 and N16):

- **N4** — a verifier that reads the spec cold, with no tools that write, and never the
  constructor's reasoning (Loop-Engineering's adversary + graph-engineering's
  `second-opinion`), so a review is performed by someone who cannot defend the work;
- **N8** — coverage rules (what a guard scans) separated from prompts (how it interprets),
  so adjusting what a guard covers never inflates its reasoning context (deepsec matchers +
  astryx detector→verdict);
- **N16** — revalidation: after a correction, re-run the guard over the same file with the
  diff, and mark a finding `fixed` without a full re-scan (deepsec `revalidate`).

Nothing here grants authority, adds a service, or creates a second control plane. It adds
three checked behaviours to the backbone spec 029 already built.

## Context and problem

**What is true today, measured in this tree on 2026-08-25, after spec 029:**

- `tests/evals/` now scores review skills against planted defect packs with recall and
  precision, and the evals lane runs in `just check` (B-029-1). But the *skill* that does
  the scoring is a deterministic reporter standing in for the real judgement — there is no
  **adversarial verifier** that reads a spec cold and judges the delivered work with no
  write tools and no access to the constructor's conversation. A skill can still review the
  work it just built and find nothing wrong (Loop-Engineering's central lesson; the
  research N4).
- `evidencing.py` re-executes a claim (B-029-3) and `answer_key.py` applies a decided
  standard (B-029-2). But **coverage** — what paths and fields a guard scans — is written
  inside the prompt or the gate body, so widening what a guard covers means editing its
  reasoning text, and every edit risks inflating the context the guard runs in (deepsec's
  matchers separate this exactly; the research N8).
- `recheck_one` re-runs a whole check, and nothing **revalidates at finding granularity**:
  after an agent applies a fix to one file, there is no cheap second look that reads the
  diff and marks the specific finding `fixed` without re-running the entire lane (deepsec's
  `revalidate`; the research N16). Every fix pays the full scan again, so fixes are batched
  and stale.

**The problem, in words a non-technical reader can follow:**

A person who wrote the work cannot be the only person who checks it — they will find it
good. A guard whose instructions say both what to scan and how to judge it is one document
where two different changes meet, so every small change is a big edit. And when a bug is
fixed, the whole scan runs again instead of the checker taking a second look at just the
file and saying "that one is now fixed". The three changes in this spec add those three
controls: a reviewer who reads the spec cold and cannot write, coverage rules kept apart
from reasoning, and a cheap revalidation of a fixed finding.

## Options considered

1. **Add the three controls as one reviewed superseding spec (chosen shape).** N4
   (cold-read verifier), N8 (coverage rules) and N16 (revalidation) land as their own TDD
   tasks with a red fixture first, building on the evals and answer-key backbone spec 029
   shipped. Gives: one increment that names the verifier shape before the coverage rules it
   will apply, and a revalidation loop that closes the false-positive cycle the evals
   harness measures. Costs: a wide block; mitigated by atomic commits. Rules out: weakening
   any of the three.
2. **Do N4 alone, defer N8/N16.** Gives: a smaller block. Costs: a cold-read verifier with
   no separated coverage rules re-derives its scope from prose every run, and no
   revalidation means every correction re-pays the full lane — the two inefficiencies the
   research paired with N4. The user's rule is that nothing in the goal is a ceiling, so
   deferring reachable work is not the conservative choice here.
3. **Adopt all three as external tooling (claude -p, semgrep plugins).** Gives: faster
   delivery. Costs: the framework's philosophy is that deterministic facts live in code and
   the product's own tests prove its claims; outsourcing the verifier shape to a specific
   harness's subprocess (`claude -p`) would make a command this wheel cannot run a claimed
   control, which spec 010's portable-command rule refuses. Rules out: external-only.

## Decision

**Option 1**, as paquete 2 of the research. The spec supersedes spec 010 only where it
extends the target with the three behaviours below; it does not weaken, drop or relabel any
normative requirement 010 already states. Each behaviour is closed, versioned, and comes
with both a positive fixture and a nearby clean control. The three are:

### B-030-1 — Cold-read verifier with no write access (research N4)

A verifier skill that reads **only** the spec (or answer key) and the delivered files —
never the constructor's conversation, never the plan's rationale — and has **no write
tools**. Its rules: "an uncertain check is a fail"; it reports what it *saw*, not what the
builder said; it cannot edit the work it judges. In this repository the shape is a
deterministic `verify_cold` runner in `src/ai_engineering/` plus an `ai-review`/`ai-verify`
corpus route "verify this cold" — the runner walks the named files read-only and applies
the answer key with `--recheck`, and a negative fixture proves a cold-read verifier with
write access or with the constructor's reasoning is refused by the framework's guard shape.

### B-030-2 — Coverage rules separated from prompts (research N8)

Every guard whose scan surface can change has its coverage declared as **data**, not prose:
a `policy/coverage/*.toml` file per guard naming the roots, globs and fields it may scan,
read by the guard at run time. Adjusting what a guard covers is a one-file data change and
never touches the guard's reasoning text. A coverage rule that escapes the declared roots,
or a guard that scans outside its coverage file, is `INCOMPLETE` — the same fail-closed
rule `evidencing` and `answer_key` already enforce. The evals harness's reporters become the
first consumers: a pack's `scan.py` must declare its roots in the pack's `coverage` table,
and a reporter that reads outside them is refused.

### B-030-3 — Revalidation at finding granularity (research N16)

After a correction, a `--revalidate <finding-id>` step re-reads the specific file's diff
and marks the finding `fixed` only when the change actually removed the trigger, without
re-running the whole lane. A finding whose file was not touched stays open; a finding
touched by a diff that does not remove the trigger is `INCOMPLETE` (the fix cannot be
believed), never silently `fixed`. The verdict vocabulary matches the answer key's
PASS/FAIL/BLOCKED, and revalidation writes a check-evidence receipt like every other
executed lane.

## Challenged once

**"A cold-read verifier with no write access is only as good as the spec it reads; a weak
spec yields a review that finds nothing."** True, and it is the point: the verifier's blind
spot is the spec's own gaps, which is exactly what `answer_key`'s `BLOCKED: U<n>` exposes —
the verifier reports the unknowns it cannot judge rather than inventing a pass. The answer
key (spec 029) supplies the decided standard; the cold-read verifier is the reader who
applies it without the constructor's bias. Neither works without the other, which is why
this spec lands on top of 029 rather than beside it.

**"Coverage rules as data are extra indirection for three guards."** The evals harness
already proved the cost of prose coverage: the pack's `scan.py` embeds its roots in code,
and a reporter that silently broadens its scan changes what the harness measures with no
diff anybody can read as a coverage decision. A declared `coverage` table turns "what this
guard may look at" into a one-line, reviewable data change — the same move this repository
made for skill routing (`skill-sequence.toml`) and the register (`pilot-register.toml`),
and the same rule 12: a decision that always comes out the same becomes data with a check.

## Assumptions and unresolved risks

- Assumption: the `ai-verify`/`ai-review` skills can name a cold-read mode without colliding
  with the answer-key consumer route already added by spec 029. The corpus evaluator
  (`skill_eval`) will catch a fork, and the baseline moves with the measured reason.
- Unresolved: an `a/b pick` check still needs a judge (human or model) and has no fully
  automated CI path — spec 029 recorded it and this spec does not change that.
- Unresolved: the inherited `madr.validate` red from ADR 0025. Like spec 029, this spec
  records it and does not authorise rewriting that history.
- Assumption: `revalidate`'s diff is available from git in the running tree; a machine
  without git (the stranger's wheel install) reports `INCOMPLETE` rather than guessing.

## Examples somebody can check

Given a cold-read verifier with read-only filesystem access and no write tools,
When it applies a spec's answer key to a delivered file with `--recheck`,
Then it reports PASS, FAIL or `BLOCKED: U<n>` from what it observed, and a verifier with
write access or the constructor's reasoning is refused (`uv run --with pytest==9.1.1
pytest -q tests/test_cold_read.py` → `3 passed`).

Given a guard whose scan surface can change,
When its coverage is declared in `policy/coverage/<guard>.toml`,
Then the guard reads those roots at run time, a coverage rule escaping them is `INCOMPLETE`,
and a guard scanning outside its coverage file is refused (`uv run --with pytest==9.1.1
pytest -q tests/test_coverage_rules.py` → `3 passed`).

Given a finding marked open and a correction that touched its file,
When `--revalidate <finding-id>` re-reads the diff,
Then the finding is marked `fixed` only if the diff removed the trigger; a touched file that
keeps the trigger is `INCOMPLETE`, never silently fixed (`uv run --with pytest==9.1.1
pytest -q tests/test_revalidate.py` → `3 passed`).

Given the evals harness with the coverage contract,
When a pack's `scan.py` reads outside its declared `coverage` roots,
Then the harness refuses the pack as `INCOMPLETE` and the lane fails closed (`uv run --with
pytest==9.1.1 pytest -q tests/test_evals_harness.py -k coverage` → `1 passed`).

Given the register's baseline,
When the corpus routes a cold-read case,
Then the skill-routing baseline moves only with the measured reason in the same commit
(`uv run python tests/skill_eval.py` → `RAN skilleval=<n>` with the baseline moved).

## Decisions

**D-030-01 — a cold-read verifier with no write access and no access to the constructor's
reasoning is the review shape for delivered work; "an uncertain check is a fail."**
Rationale: Loop-Engineering's adversary and graph-engineering's `second-opinion` both
proved that a reviewer who can see the builder's conversation will find excuses; the
deterministic runner makes the shape checkable, and the answer key (spec 029) supplies the
standard it applies.

**D-030-02 — guard scan surfaces are declared as coverage data per guard, separated from
the reasoning prompt; a guard scanning outside its coverage file is INCOMPLETE.**
Rationale: deepsec and astryx both isolate "what to scan" from "how to judge"; a data file
keeps coverage changes reviewable and never inflates reasoning context — the same move as
`skill-sequence.toml` and `pilot-register.toml`.

**D-030-03 — revalidation is finding-granular: `--revalidate <finding-id>` re-reads the
diff and marks `fixed` only when the trigger is gone; otherwise INCOMPLETE.**
Rationale: deepsec's `revalidate` cut false positives ~50%; the cheap second look is what
makes fixes affordable, and the fail-closed verdict keeps a touched-but-unfixed file from
silently going green.

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