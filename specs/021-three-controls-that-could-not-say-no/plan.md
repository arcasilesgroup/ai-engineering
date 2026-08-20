# Plan: three controls that could not say no — 021 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**. The authority for this block is recorded in `docs/adr/0016`, which names
the role, the date and the scope, and is written before any task runs.

One repository writer, in a worktree of its own. Each Task is one atomic commit changing one
primary production, policy or skill file, plus only the test files that Task names. Rollback
for every Task and every repair is `git revert <commit>`.

**This plan is not edited while it is executed.** What happened to each Task is recorded in
the commit messages, and the approved digest of this file stays valid because the file does
not move.

## The order, and why it is not negotiable

The tree sits at zero slack against the line ceiling: `repo_lines` is 82,400 and the ceiling
is 82,400. So any Task that adds a net line cannot land until the ceiling is gone. Tasks 1
to 8 subtract or are ceiling-exempt; Tasks 9 to 11 add. Running 9 before 8 means resealing a
number this block is deleting, which is the arithmetic the block exists to remove.

Tasks 2 to 8 are one deletion split by what breaks: the page, the assertions, the constant,
the doctrine, the filter, the ledger row, the changelog. Each is green on its own.

## What is counted today, so the numbers below can be checked rather than trusted

`contract.repo_lines(root)` returns 82,400. `contract.REPO_CEILING` is 82,400.
`policy/capabilities.toml` holds 15 `[[capabilities]]` rows. `hooks/` holds four guards.
`git grep -c REPO_CEILING` and the seal digest are the two numbers Task 4 and Task 1 move.

## Block A — the two controls that cannot fire (Tasks 1–8)

1. **The capability cap is removed, and the list a person signs is kept** —
   **file** `policy/capability-manifest.schema.json`.
   **check**: `uv run pytest -q tests/test_capabilities.py tests/test_contracts.py -k capability`.
   **rollback**: `git revert <commit>`.
   **done when**: the `maxItems` key is gone, `minItems` remains, `allowed_ids` is untouched,
   and the schema seal in `src/ai_engineering/capability.py` matches the new file.

2. **The ceiling card leaves the page that publishes it** —
   **file** `src/ai_engineering/solution_intent.py`.
   **check**: `uv run pytest -q tests/test_solution_intent.py`.
   **rollback**: `git revert <commit>`.
   **done when**: the page renders without a product-lines card and the module imports with
   no unused reader left behind.

3. **The assertions and receipts that read the ceiling are deleted** —
   **file** `tests/test_contracts.py`.
   **check**: `uv run pytest -q tests/test_contracts.py tests/test_readiness.py tests/test_record.py`.
   **rollback**: `git revert <commit>`.
   **done when**: no test imports `REPO_CEILING`, including the module-level alias, and the
   suite still collects.

4. **The constant, its sealer and its recipe are deleted** —
   **file** `src/ai_engineering/contract.py`.
   **check**: `git grep -n REPO_CEILING -- src tests hooks justfile`.
   **rollback**: `git revert <commit>`.
   **done when**: that command prints nothing, `tests/seal_ceiling.py` is gone, the `seal`
   recipe is gone, and `contract.tracked` and `contract.count` still resolve for their live
   readers.

5. **The doctrine stops naming a number that is not there** —
   **file** `AGENTS.md`.
   **check**: `uv run pytest -q tests/test_contracts.py -k doctrine`.
   **rollback**: `git revert <commit>`.
   **done when**: the "Working here" paragraph no longer names the ceiling as the home of a
   value, and `doctor.py` and `policy/pilot-register.toml` lose their matching sentences in
   the same commit.

6. **The filter that existed only for ceiling commits is deleted** —
   **file** `tests/red_then_green.py`.
   **check**: `uv run python tests/red_then_green.py`.
   **rollback**: `git revert <commit>`.
   **done when**: the bookkeeping special case is gone and the harness still runs.

7. **The requirement row is rewritten in place, not deleted** —
   **file** `docs/requirements.toml`.
   **check**: `uv run pytest -q tests/test_requirements_ledger.py`.
   **rollback**: `git revert <commit>`.
   **done when**: the row that named the ceiling command says what is true now, the total is
   still 385 and every identifier still resolves.

8. **The removal is written where a stranger reads it** —
   **file** `CHANGELOG.md`.
   **check**: `uv run pytest -q tests/docs`.
   **rollback**: `git revert <commit>`.
   **done when**: the existing `### Breaking changes` block under `[Unreleased]` names the
   three public names that disappeared, and no second breaking block was opened.

## Block B — the paths that read a crash as permission (Tasks 9–11)

9. **The dispatcher denies when it cannot decide** —
   **file** `hooks/chain.py`.
   **check**: `uv run pytest -q tests/test_hooks.py -k dispatcher`.
   **rollback**: `git revert <commit>`.
   **done when**: a non-text tool name exits 2 rather than 1, and a legitimate denial still
   exits once with one message — the `SystemExit` clause comes first or every real denial is
   swallowed and printed twice.

10. **A denial survives a broken standard output** —
    **file** `hooks/_wrap.py`.
    **check**: `uv run pytest -q tests/test_hooks.py -k stdout`.
    **rollback**: `git revert <commit>`.
    **done when**: with standard output closed the process exits 2 in both protocols, and
    the exit does not run the interpreter's flush, which is what rewrites the status to 120.

11. **The loop guard stops denying on whitespace** —
    **file** `hooks/loop_guard.py`.
    **check**: `uv run pytest -q tests/test_hooks.py -k whitespace`.
    **rollback**: `git revert <commit>`.
    **done when**: an argument made only of spaces produces no exception and no denial.

## Block close

`just check` green with its output shown, `python tests/adversarial/run.py` at 21 of 21, and
`just guards` at its floor. The block is closed by a hand-off that names what each Task
actually changed, not what it intended to change.
