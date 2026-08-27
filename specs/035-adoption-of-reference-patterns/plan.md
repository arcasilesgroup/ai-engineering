# Plan: adopt reference patterns as checked behaviours — 035 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**, recorded at their digests in their own record. One repository writer, on a
branch carrying the whole 035 change. Each task is one atomic commit touching one primary
production, policy or skill file plus only the files that task names. Rollback for every task
is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the whole gate in the same
chain as the commit itself. `ai-eng spec show 035 --task <n>` refuses any task whose digests
have moved.

## The order, and why

**R0 kernel behaviours first, tools before rules.** The umbrella fixture
(`tests/test_035_adoption.py`) is written first — red on all seven `-k` cases the spec
names — so every later task turns a real red green. Modules (evidence checker, verifier
isolation, conventions contract, boundary classifier, cost pre-flight, skill schema
validator, trim, decision framework) ship before their corpus routes, exactly as specs
028-034 did. Then the corpus routes and any skill repair, then the gate. R1 is sequenced
behind R0 by the spec's wave-completion criterion: R0 is green only when the seven `-k`
cases pass and the named-framework/boundary corpus assertions are in `tests/skill_eval.py`;
a later wave never starts while an earlier one is red.

## What this plan is not doing, and why

- **No change to `.ai/intent.md`, `CONSTITUTION.md`, or the one-writer rule.**
- **No new skill beyond the framework's corpus/rules.** The nine kernel behaviours are
  modules, one policy schema, contract rules and corpus routes; the existing skill set is
  unchanged (the spec adopts disciplines, not a fifteenth skill).
- **No R2 item is authorised here.** Build-auto resume, doubt cycle, scored evals and the
  rest of the R2/registry P2 set stay evidence until an owned spike validates them
  (spec D-035-06). This plan's last task is the R0→R1 gate; R2 is deliberately absent.
- **No acceptance of ADR 0025 / no history rewrite of spec 026.** The inherited
  `madr.validate` red is recorded, not fixed here; the final gate task asserts no new MADR
  failure.
- **No change to `justfile`/`test_quality_gate.py`** — those carry the repository owner's
  uncommitted work; the new suites are picked up by the existing `test` recipe with no
  wiring.
- **No CI/CD box ticked.** Adds no service, endpoint or URL (spec Production-ready is
  `not applicable` for the service-shaped boxes).

## The boundary this plan may not cross

The evidence checker never lets a ticked box with no recorded evidence pass. Verifier
isolation never grants edit tools to the auditor, and a non-running lane reports
`NOT COVERED`, never `PASS`. The conventions contract is the single severity/evidence scale
every verification skill reads; a test refuses a skill that redefines a scale instead of
reading the shared one. The boundary classifier returns Always/Ask-first/Never or refuses a
decision outside the declaration. Cost pre-flight refuses before any model work when the
budget is unnamed and the operation crosses the threshold (default >5 model calls or >20k
output tokens, configurable). The skill schema validator is the single machine-validated
declaration B-035-4 reads from. The trimmer never elides a failure marker and is
deterministic. The decision-framework module returns a named verdict (RICE, Effort/Value,
Kano) or refuses an unnamed ranking.

## Tasks

## Block A — R0 umbrella fixture and gate machinery (Tasks 1-4)

1. **Red fixture: the umbrella suite is all red** —
   **file** `tests/test_035_adoption.py` (new): one file, seven cases — `evidence`,
   `evidence_unmet`, `verifier_no_edit`, `not_covered`, `boundary_undecidable`,
   `unnamed_ranking`, `cost_preflight` — each an importable module fixture with a positive
   case and a nearby clean control. Today they fail at import (no modules yet); each turns
   green as its module lands.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_035_adoption.py`
   **rollback**: `git revert <commit>`.
   **done when**: the suite runs and every case is red for the right reason (missing
   module), proving the plan will turn real reds green — no case passes before its module
   exists.

2. **Evidence checker (B-035-1)** —
   **file** `src/ai_engineering/evidence.py` (new, stdlib-only: `check_value(entry)` reads
   CHECK/EXPECT/EVIDENCE; a box with no recorded evidence is unmet; `validate(path)` exits
   non-zero listing errors vs warnings), plus the green half of the `evidence` and
   `evidence_unmet` cases.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_035_adoption.py -k evidence`
   **rollback**: `git revert <commit>`.
   **done when**: `evidence` passes (EXPECT matches executed CHECK, evidence recorded) and
   `evidence_unmet` passes (tick with no evidence reads unmet).

3. **Verifier isolation (B-035-2)** —
   **file** `src/ai_engineering/verify.py` (new: `audit_report(finding)` refuses a proposed
   edit; a lane that did not run reports `NOT COVERED`, never `PASS`), plus the green half
   of the `verifier_no_edit` and `not_covered` cases.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_035_adoption.py -k "verifier_no_edit or not_covered"`
   **rollback**: `git revert <commit>`.
   **done when**: `verifier_no_edit` refuses an auditor edit; `not_covered` reports a
   non-running lane as `NOT COVERED`.

4. **Conventions contract (B-035-3)** —
   **file** `src/ai_engineering/conventions.py` (new: the single severity scale, the
   false-positive gate trigger/consequence/evidence, the installed-version rule) plus a
   contract rule refusing any verification skill that redefines the scale, and the green
   half of a `conventions_scale` case added to the umbrella.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_035_adoption.py -k conventions`
   **rollback**: `git revert <commit>`.
   **done when**: a skill reading the shared scale passes; a skill redefining `P0`/`HIGH`
   is refused.

## Block B — R0 classifier, cost, schema, context, decision (Tasks 5-10)

5. **Boundary classifier (B-035-4)** —
   **file** `src/ai_engineering/boundary.py` (new: `classify(decision, declarations)`
   returns Always/Ask-first/Never or None for out-of-declaration), plus the green half of
   `boundary_undecidable`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_035_adoption.py -k boundary`
   **rollback**: `git revert <commit>`.
   **done when**: an out-of-declaration decision returns None and blocks.

6. **Anti-rationalization + red flags (B-035-5)** —
   **file** `src/ai_engineering/rationalize.py` (new: a table of `excuse → reality` and an
   observable red-flag check; a matched rationalization blocks the pass) plus the green
   half of the `anti_rationalization` case.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_035_adoption.py -k anti_rationalization`
   **rollback**: `git revert <commit>`.
   **done when**: a verifier skipping a red flag on a plausible excuse is blocked and the
   gate fails the pass.

7. **Cost pre-flight + route by model (B-035-6)** —
   **file** `src/ai_engineering/cost.py` (new: `preflight(estimate, budget)` refuses when
   the budget is unnamed and the estimate crosses the configurable threshold, default >5
   model calls or >20k output tokens; `route(work)` maps work type to a model tier with a
   bail-out), plus the green half of `cost_preflight`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_035_adoption.py -k cost_preflight`
   **rollback**: `git revert <commit>`.
   **done when**: an expensive operation with no named budget is refused before any model
   work; the route map returns a tier or a bail-out.

8. **Skill schema + tool gating (B-035-7)** —
   **file** `policy/skill-schema.json` (new: machine-validated metadata — name, description,
   tools[], department, proactive_trigger?) + `src/ai_engineering/skillschema.py` (new:
   `validate(frontmatter)` and `assert_allowed_tool(run_tool, declared)`), plus a fixture
   proving a tool outside the declared set is refused.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_035_adoption.py -k skillschema`
   **rollback**: `git revert <commit>`.
   **done when**: valid skill metadata validates; a skill running a tool outside its
   declared set is refused; B-035-4 reads this validator.

9. **Context economy primitives (B-035-8, R0 slice)** —
   **file** `src/ai_engineering/context_econ.py` (new, stdlib-only: `trim_output(text,
   max_lines)` head+tail with a `… N elided …` marker that never elides a failure line, and
   `filter_test_output` keeping FAIL+summary), plus a fixture on the umbrella.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_035_adoption.py -k context`
   **rollback**: `git revert <commit>`.
   **done when**: trim/filter are deterministic, failure lines survive; the area-gated rule
   loading and instruction minimalism are R1 (sequenced, not assumed done here).

10. **Named decision framework (B-035-9)** —
    **file** `src/ai_engineering/decision_fw.py` (new: `RICE`, `EffortValue`, `Kano` each
    returning a deterministic verdict; an unnamed ranking returns None), plus the green half
    of `unnamed_ranking`.
    **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_035_adoption.py -k unnamed_ranking`
    **rollback**: `git revert <commit>`.
    **done when**: a named framework returns a deterministic verdict; a bare "ranked by
    impact" with no method is refused.

## Block C — R0 corpus routes and the gate (Tasks 11-12)

11. **Corpus routes for the R0 behaviours + skill-eval assertions** —
    **file** `.agents/skills/ai-review/corpus.md` and `.agents/skills/ai-verify/corpus.md`
    (route: name the decision framework, honour the shared severity scale, report
    `NOT COVERED` honestly) plus `tests/skill_eval.py` assertions for the named-framework
    and boundary rules — the corpus half of the spec's wave-completion criterion.
    **check**: `uv run python tests/skill_eval.py`
    **rollback**: `git revert <commit>`.
    **done when**: the corpus routes the behaviours with no fork, and `tests/skill_eval.py`
    asserts the named-framework and boundary rules (the independent route over the same
    corpora).

12. **The R0 gate reads the kernel green** —
    **file** none (verification).
    **check**: `just check`
    **rollback**: `git revert <commit>`.
    **done when**: `just check` exits 0 with the seven umbrella cases green, the corpus
    assertions present, `tests/test_madr.py` reporting exactly the same pre-existing
    failures as before this block (the ADR 0025 inherited red) — no fifth failure
    introduced. This is the spec's R0 wave-completion criterion; only then may R1 begin.

## Block D — R1 wave (Tasks 13-17, after R0 is green)

13. **Review-router (R1: graph-eng G-04)** —
    **file** `src/ai_engineering/review_router.py` (new: select verification lanes from the
    shape of a diff, never run zero lanes) + a fixture on a new
    `tests/test_035_r1.py`.
    **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_035_r1.py -k review_router`
    **rollback**: `git revert <commit>`.
    **done when**: lane selection is determined by diff shape and never returns an empty
    plan.

14. **Full-review orchestrator (R1: graph-eng G-05/06/07)** —
    **file** `src/ai_engineering/full_review.py` (new: resolve scope once, fan out lanes,
    dedup by file:line, merge) + fixture.
    **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_035_r1.py -k full_review`
    **rollback**: `git revert <commit>`.
    **done when**: one resolved scope feeds all lanes, dedup collapses duplicates, and a
    silent lane failure reads `NOT COVERED`.

15. **Goal-writer short condition (R1: Loop-Eng LE-07) + spec DoD shape (LE-03)** —
    **file** `src/ai_engineering/goal.py` (new: pointer + reporting clause + met condition,
    never duplicating the spec) + fixture.
    **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_035_r1.py -k goal_writer`
    **rollback**: `git revert <commit>`.
    **done when**: the goal condition is the three-part short form and does not copy the
    spec body.

16. **Two-job CI gate (R1: deepsec D-05)** —
    **file** `.github/workflows/check.yml` (split: analyze job without write permissions
    runs the gate; a comment job with write but without the secret publishes results) +
    fixture proving the split.
    **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_035_r1.py -k ci_gate`
    **rollback**: `git revert <commit>`.
    **done when**: the analyze job has no write scope, the comment job has write but no
    secret, and no job mixes untrusted code with write permissions.

17. **R1 gate** —
    **file** none (verification).
    **check**: `just check`
    **rollback**: `git revert <commit>`.
    **done when**: `just check` exits 0 with the R1 fixtures green and the same inherited
    `madr.validate` red. The spec, plan and approval of 035 are committed at their exact
    digests.

## Deliberate omissions (what R2 is, and why it is absent)

No R2 item is in this plan. Rolling dispatch and disjoint ownership (unlazy U06/U07),
skill-router decision tree and model-per-chunk fan-out (addyosmani ASK-01, model-router
MR-03), proactive triggers and memory provenance (contains-studio CS-03, graph-eng G-10),
and the UI write-audit cycle (AL-Design A-01/02) are each sequenced for R2 in the spec, and
per D-035-06 every one stays evidence until an owned spike validates its cost and state risk
— build-auto resume and doubt-cycle in particular. This plan's last task is R1's gate; R2
must begin with a new spec change that names the spike result, not a silent extension of
this record.