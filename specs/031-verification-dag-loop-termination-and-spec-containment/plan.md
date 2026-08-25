# Plan: verification DAG, loop termination and spec containment — 031 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**, recorded at their digests in their own record. One repository writer, on a
branch carrying the whole 031 change. Each task is one atomic commit touching one primary
production, policy or skill file plus only the files that task names. Rollback for every task
is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the whole gate in the same
chain as the commit itself. `ai-eng spec show 031 --task <n>` refuses any task whose digests
have moved.

## The order, and why

The DAG lands first (B-031-1) because it defines what a verified output is — the merge and
the node gate are the vocabulary the loop's passes will be measured against. Then the loop
termination (B-031-2), which terminates an orchestrator on the DAG's verdicts. Then the spec
self-containment contract (B-031-3), which makes the spec the only interface a DAG node
reads, closing the loop the first two half through. The final task proves the whole gate with
clean controls for each new behaviour.

Each task starts with its **red fixture** — the test that fails before the behaviour exists —
implemented in the same commit, exactly as specs 029 and 030 built theirs.

## What this plan is not doing, and why

- **No change to `.ai/intent.md`, `CONSTITUTION.md`, or the one-writer rule.** The three
  behaviours extend the *target*, not the authority model.
- **No change to `src/ai_engineering/dag.py` (spec 013).** That module orders *claims* for
  the one-writer rule; B-031-1 is a *verification* module with a distinct file and a
  docstring that says so.
- **No acceptance of ADR 0025 / no history rewrite of spec 026.** The inherited
  `madr.validate` red is recorded, not fixed here; the final task asserts no new MADR
  failure.
- **No new CLI verb.** The three runners are modules with tests; `audit`'s `--revalidate`
  already covers the finding path, and an orchestrator calls these as functions.
- **No new just recipe and no change to `justfile`/`test_quality_gate.py`** — those carry
  the repository owner's uncommitted work, and the new suites are picked up by the existing
  `test` recipe with no wiring.
- **No CI/CD box ticked.** Adds no service, endpoint or URL.

## The boundary this plan may not cross

The verification DAG (`lane_merge.py`) never *orders claims*: that stays in `dag.py`. Its
`gate_nodes` refuses any consumption of an unverified output (INCOMPLETE, never a pass). The
loop gate (`loopgate.py`) never approves or accepts: it only reports when an orchestrator is
allowed to stop, and the stop decision stays with the orchestrator's own authority model.
The spec contract (`self_contained` + `section`) refuses conversation leaks deterministically
and resolves sections by position without rewriting any existing spec.

## Tasks

## Block A — verification DAG and lane merge (B-031-1)

1. **Red fixture: unverified output cannot feed the next node** —
   **file** `tests/test_lane_merge.py` (new): a node whose verify command fails must leave
   its downstream input `INCOMPLETE`; a verified node's output may be consumed.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_lane_merge.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture is red before `src/ai_engineering/` ships the runner, and
   green after — a fail is INCOMPLETE, never silently forwarded.

2. **Lane gate and merge in the product** —
   **file** `src/ai_engineering/lane_merge.py` (new, stdlib-only): `gate_nodes` runs each
   node's `verify` before its output is consumed; `merge` dedupes by (file, line), re-ranks
   globally by consequence severity, and surfaces a lane conflict on the same (file, line),
   plus the green half of `tests/test_lane_merge.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_lane_merge.py`
   **rollback**: `git revert <commit>`.
   **done when**: `gate_nodes` refuses an unverified output INCOMPLETE; `merge` returns one
   deduped, re-ranked verdict with conflicts surfaced and no finding swallowed.

## Block B — loop termination (B-031-2)

3. **Red fixture: a single green or two differing greens is not done** —
   **file** `tests/test_loopgate.py` (new): one green run → not done; two greens with
   different outcome digests → not done; two identical greens → done; a failed pass resets.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_loopgate.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture is red before `loopgate.py` ships, and green after.

4. **Loop gate in the product** —
   **file** `src/ai_engineering/loopgate.py` (new, stdlib-only): `record(history, outcome,
   digest, changed)` appends; `done(history)` is True only when the last two runs are green
   with identical outcome digests; a no-op pass (changed=False) still records as a green;
   a diverging green restarts the identical run; a fail resets it; plus the green half of
   `tests/test_loopgate.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_loopgate.py`
   **rollback**: `git revert <commit>`.
   **done when**: `done` is the two-identical-green rule and the no-op pass counts toward it,
   never a single-green stop and never an invisible-progress loop.

## Block C — spec self-containment (B-031-3)

5. **Red fixture: a spec that says "as discussed" is refused** —
   **file** `tests/test_spec_containment.py` (new): conversation leaks are refused; a clean
   spec passes; `section(text, 2)` resolves the second ## heading.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_spec_containment.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture is red before `spec.py` ships the helpers, and green after.

6. **Self-containment and section helpers in `spec.py`, and the ai-spec corpus rule** —
   **file** `src/ai_engineering/spec.py` (add `self_contained(text)` and `section(text, n)`),
   `.agents/skills/ai-spec/corpus.md` (route: "the spec carries the whole job"; refusal: a
   spec that leans on the conversation), plus the green half of `tests/test_spec_containment.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_spec_containment.py && uv run python tests/skill_eval.py`
   **rollback**: `git revert <commit>`.
   **done when**: `self_contained` reports each conversation leak, `section` resolves by
   position, the corpus routes the self-containment case with no fork, and the skill-routing
   baseline moves only with the measured reason.

## Block E — prove the gate

7. **The full gate reads the three controls green with their clean controls** —
   **file** none (verification).
   **check**: `just check`
   **rollback**: `git revert <commit>`.
   **done when**: `just check` exits 0, the lane-merge/loopgate/spec-containment suites pass
   with their clean controls, and `tests/test_madr.py` reports exactly the same pre-existing
   failures as before this block (the ADR 0025 inherited red) — no fifth failure introduced;
   the spec, plan and approval of 031 are committed at their exact digests.