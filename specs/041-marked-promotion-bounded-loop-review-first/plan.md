# Plan: marked promotion, bounded spec loop, review-first critics — 041 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and
this exact `plan.md`**, recorded at their digests in their own record. One repository
writer, on a branch carrying the whole 041 change. Each task is one atomic commit touching
one primary production, policy or skill file plus the files that task names. Rollback for
every task is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the gate in the same
chain as the commit itself. `ai-eng spec show 041 --task <n>` refuses any task whose
digests have moved.

## The order, and why

The marker parser lands first (B-041-1) because `decide.py`'s filter reads it: the red
fixture, then the parser in `spec.py`, then the filter in `decide.py` — the filter's own
red fixture is a spec with no marked decision and a title the verb must refuse. The
criteria prose (ai-spec paso 10) follows the code it instructs. The loop bound (B-041-2)
lands next, on both critic skills, with the bound pinned by a test. The parallel policy
(B-041-3) is data and lands last before the gate. Each task starts with its **red
fixture** — the test that fails before the behaviour exists — implemented in the same
commit, exactly as specs 031 and 040 built theirs.

## What this plan is not doing, and why

- **No wiring of `loopgate.done()` into an orchestrator.** Spec 031 recorded loopgate as
  the future instrument of an orchestrator that does not exist; the bound here is the
  skill-layer instruction (D-041-02). The integration is a later spec's task.
- **No acceptance of ADR 0025 / no history rewrite of spec 026.** The inherited
  `madr.validate` red is recorded, not fixed here; the final task asserts no new MADR
  failure.
- **No hard delete of the `ai-eng decide "<title>"` path.** The marker filter is the gate
  (D-041-01); the command stays the named one in the spec template.
- **No change to `.ai/intent.md`, `CONSTITUTION.md`, or the one-writer rule.**
- **No new just recipe and no change to `justfile`/`test_quality_gate.py`** — the new
  suites are picked up by the existing `test` recipe with no wiring.
- **No CI/CD box ticked as new.** Adds no service, endpoint or URL.

## The boundary this plan may not cross

The marker parse never writes: `marked_decisions` reads the record, and the refusal is
INCOMPLETE with nothing written. The loop bound never stops a person: the ceiling is
"write the page and hand it over", and a revision that changes the digest reopens the
count. The parallel policy never forces concurrency: verify+security may pair only when
the host can run both and review is green, and the sequence is the default.

## Tasks

1. [x] <!--t:317f0c415588--> **Red fixture: the marker parser and the refusal** —
   **file** `tests/test_spec_marker.py` (new): `marked_decisions` recognises
   `- [X] **D-NNN-NN — the decision**` under `## Decisions`, ignores unmarked entries and
   entries under other headings, and returns nothing for a text with no section or no
   marks; `ai-eng decide "<title>"` against a spec whose Decisions carry no such mark
   returns INCOMPLETE naming the marker, writing nothing.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_spec_marker.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture is red before `spec.py` and `decide.py` ship the behaviour,
   and green after — an unmarked title is refused, never promoted.

2. [x] <!--t:b9e176d79681--> **The `[X]` marker in `spec.py`: parser and template (B-041-1)** —
   **file** `src/ai_engineering/spec.py` (add `marked_decisions(text)` and its section
   anchor; document the `- [X]` marker in the `## Decisions` template comment and in the
   Decision-section TODO, keeping the `ai-eng decide "<title>"` sentence), plus the green
   half of `tests/test_spec_marker.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_spec_marker.py -k marker`
   **rollback**: `git revert <commit>`.
   **done when**: marked entries parse as `(id, title)`; unmarked and foreign-heading
   entries do not; the template tells the author how to mark.

3. [x] <!--t:4360372d5b2f--> **`decide.py` filters by `[X]` (B-041-1)** —
   **file** `src/ai_engineering/decide.py` (after resolving the target spec, refuse a
   title not marked `[X]` under its `## Decisions`: INCOMPLETE `[DECISION_UNMARKED]`,
   nothing written) + the decide fixtures in `tests/test_madr.py`
   (`_repository_with_spec` gains a Decisions section carrying the titles those tests
   promote), `tests/test_mut_spec.py` (`_fixture_spec` gains a `marked` parameter and its
   call sites pass their titles), `tests/test_cli_migration.py` (the 010 spec in the
   decide test gains the three marked titles), plus the green half of
   `tests/test_spec_marker.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_spec_marker.py -k decide && uv run --with pytest==9.1.1 pytest -q tests/test_madr.py tests/test_mut_spec.py tests/test_cli_migration.py`
   **rollback**: `git revert <commit>`.
   **done when**: an unmarked title is refused with nothing written; every existing
   decide call that expects PASS, or INCOMPLETE for a graph/write reason, still promotes
   because its fixture marks the title.

4. [x] <!--t:ac26fe9f29e8--> **The criteria in ai-spec paso 10 (B-041-1)** —
   **file** `.agents/skills/ai-spec/SKILL.md` (paso 10: when a decision constrains specs
   that do not exist yet — architectural and cross-cutting — record it under
   `## Decisions` marked `- [X]` and promote with `ai-eng decide "<title>"`; proposal is
   not approval; an unmarked decision stays inside its spec; drop the stale `--madr`
   spelling).
   **check**: `uv run python tests/skill_eval.py`
   **rollback**: `git revert <commit>`.
   **done when**: paso 10 states the marking criteria, no skill names `--madr`, and the
   routing baseline does not move.

5. [x] <!--t:f7216d0df6c7--> **The two-round cap in challenge and council (B-041-2)** —
   **file** `.agents/skills/ai-challenge/SKILL.md` + `.agents/skills/ai-council/SKILL.md`
   (each: at most two rounds against the same spec digest; a revision reopens the count;
   at the ceiling write the outstanding findings worst first and hand the page to the
   person; loopgate is the orchestrator's instrument) +
   `tests/test_skill_bounds.py` (new: both critic skills carry the cap).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_skill_bounds.py && uv run python tests/skill_eval.py`
   **rollback**: `git revert <commit>`.
   **done when**: both skills declare the bound, the bound test passes, and the routing
   baseline does not move.

6. [x] <!--t:2e65b5e11204--> **The `[parallel] policy` records review-first (B-041-3)** —
   **file** `policy/skill-sequence.toml` (policy: fork contexts only; ai-review runs
   before ai-verify and ai-security; verify+security may pair as fork contexts when
   review is green and the host can run both; task-level parallelism inside ai-build per
   the approved plan).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_skill_sequence.py && uv run python tests/skill_eval.py`
   **rollback**: `git revert <commit>`.
   **done when**: the policy names review before verify and security, and the cycle and
   routing tests still pass.

7. [x] <!--t:2ba32c856c97--> **The gate** —
   **file** none (verification).
   **check**: `just check`
   **rollback**: `git revert <commit>`.
   **done when**: `just check` reports exactly the same pre-existing failures as before
   this block — 4 `test_madr.py` + 1 `test_intent.py` (the ADR 0025 inherited red), no
   new failure — the new suites pass with their clean controls, `just council` agrees
   with 041's counts, and the spec, plan and approval of 041 are committed at their exact
   digests.
