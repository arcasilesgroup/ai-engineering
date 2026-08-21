# Plan: seven decisions the owner handed back — 023 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**. That approval is the whole of the human step: the owner's instruction on
2026-08-21 is that a person approves a specification and the agent decides and builds
everything after it. `docs/adr/0021` records the grant before any task runs.

One repository writer, in a worktree of its own. Each Task is one atomic commit changing one
primary file plus only the tests that Task names. Rollback for every Task is
`git revert <commit>`.

**This plan is not edited while it is executed.**

## The boundary this plan may not cross

`docs/adr/0013` and `docs/adr/0017` are somebody else's signatures. No task edits an existing
record's approval table. A later record supersedes an earlier row; it never rewrites it.

## The order, and why

The authority record goes first, because every task after it runs under it. The reader repair
goes before the waiver is removed, or the gate is red between two commits. The renames go
after both, because they are the only tasks that can trip an unknown path pin, and a failure
there should not be tangled up with a gate that was already moving.

## Block A — the record of what may be done (Tasks 1–3)

1. [ ] **The widened grant is written down before it is used** —
   **file** `docs/adr/0021-the-owner-approves-specifications-and-nothing-else.md`.
   **check**: `uv run pytest -q tests/test_record.py -k madr`.
   **rollback**: `git revert <commit>`.
   **done when**: the record is born `proposed`, names the date, quotes the instruction, and
   states the four things still refused — push to the default branch is not among the grants
   this plan uses.

2. [ ] **An approval reader that lets a later record supersede an earlier row** —
   **file** `tests/test_record.py`.
   **check**: `uv run pytest -q tests/test_record.py -k approval`.
   **rollback**: `git revert <commit>`.
   **done when**: rows are keyed by file and the newest record wins, the hand-written waiver
   set is gone, and a file whose newest approval does not match its bytes still turns it red.

3. [ ] **Specifications 016 and 018 are approved at the bytes they have** —
   **file** `docs/adr/0022-specifications-016-and-018-are-re-approved-at-exact-digests.md`.
   **check**: `uv run pytest -q tests/test_record.py -k approval`.
   **rollback**: `git revert <commit>`.
   **done when**: the record carries both rows in the table shape the reader parses, names what
   changed in each file since the earlier signature, and the reader is green with no waiver.

## Block B — two documents that disagreed (Tasks 4–5)

4. [ ] **Task 8 of specification 022 gets a check that can pass** —
   **file** `tests/test_contracts.py`.
   **check**: `uv run pytest -q tests/test_contracts.py -k anchored`.
   **rollback**: `git revert <commit>`.
   **done when**: the selector in the approved plan selects exactly the test that proves it,
   the test's meaning is unchanged, and no file under `specs/` is touched.

5. [ ] **The `test_mut_` prefix stops claiming an apparatus that was deleted** —
   **file** the twenty-three `tests/test_mut_*.py`.
   **check**: `uv run pytest -q tests/ -x -q` and `python tests/mutation.py`.
   **rollback**: `git revert <commit>`.
   **done when**: every file is renamed with `git mv`, no test body changes, the collected test
   count is identical before and after, and the mutation score is unchanged.

## Block C — the promises the package makes (Tasks 6–7)

6. [ ] **A test stops pinning argparse's line wrapping** —
   **file** the test that asserts usage text, named by the failing run.
   **check**: `uv run --python 3.14 pytest -q <that test>` and the same on 3.12.
   **rollback**: `git revert <commit>`.
   **done when**: the test asserts what the command says rather than how argparse wrapped it,
   and passes on both interpreters, so `requires-python = ">=3.11"` stops being a claim the
   package does not keep.

7. [ ] **Wave 3 is refused in writing, and the constitutional misreading is withdrawn** —
   **file** `docs/adr/0023-the-record-is-not-context-and-archiving-it-buys-nothing.md`.
   **check**: `grep -rn 'specs/' hooks/*.py` prints nothing, and
   `uv run pytest -q tests/test_record.py -k madr`.
   **rollback**: `git revert <commit>`.
   **done when**: the record states both halves — that `CONSTITUTION.md` binds a user's tree
   and not this one, and that the archive buys nothing measurable — and gives the command that
   would overturn it.

## Block D — the margin on the lane (Task 8)

8. [ ] **The nine surviving generated mutants are killed** —
   **file** the test files each survivor's module is proved by.
   **check**: `python tests/mutation.py`.
   **rollback**: `git revert <commit>`.
   **done when**: the printed score is above the floor by more than one survivor, every new
   test fails when its mutant is applied and passes when it is not, and any survivor left is
   named in the commit message with why it cannot be killed.

## Block E — the close (Task 9)

9. [ ] **The changelog says what changed, and the gate is shown green** —
   **file** `CHANGELOG.md`.
   **check**: `just check`.
   **rollback**: `git revert <commit>`.
   **done when**: the entry names the renames as a hard rename with no shim, the two
   re-approvals, and the two refusals, and the full gate output is in the pull request.
