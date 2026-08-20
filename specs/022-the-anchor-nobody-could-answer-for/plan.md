# Plan: the anchor nobody could answer for — 022 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**. The standing authority for this work is `docs/adr/0016`; the approval of
these two files is recorded in its own record, at the digests below.

One repository writer, in a worktree of its own. Each Task is one atomic commit changing one
primary production, policy or skill file, plus only the test files that Task names. Rollback
for every Task and every repair is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit carries a run receipt written
by `just quick <module>` immediately before it, in the same chain, because the receipt is
keyed to the bytes being committed and an edit between the two loses it.

## The boundary this plan may not cross

`accept._anchored_bytes`, `accept._anchored_path`, `acceptance._anchored`,
`readiness._anchored`, the `anchor=` argument of `spec_transaction`, `uninstall.anchors` and
`decide._require_anchored_io` are a path-safety reader and are **not** part of this work. A
diff that touches any of them has deleted a security control by name collision. Task 8 proves
it did not happen rather than asserting it.

## The order, and why

The command surface goes before the code behind it, or the tests that call `--anchors` red on
a function that is still there. The commit hook goes early because it is what the owner sees.
The published promises go last, when they are false rather than before.

## Block A — the surface a person meets (Tasks 1–3)

1. **The commit footer stops being written and stops complaining** —
   **file** `git-hooks/commit-msg`.
   **check**: `uv run pytest -q tests/test_record.py -k commit_msg`.
   **rollback**: `git revert <commit>`.
   **done when**: a commit prints nothing about anchoring on stderr, and `ran_footer` and the
   subject-shape refusal both still work.

2. **The `--anchor` and `--anchors` arguments are refused as unknown** —
   **file** `src/ai_engineering/audit.py`.
   **check**: `uv run pytest -q tests/test_mut_accept.py tests/test_cli_migration.py -k anchor`.
   **rollback**: `git revert <commit>`.
   **done when**: `ai-eng audit --anchor` exits non-zero naming the unknown argument, and
   `verify` and `replay` still run without it.

3. **The generated workflow stops telling other repositories to pass it** —
   **file** `src/ai_engineering/skeletons.py`.
   **check**: `uv run pytest -q tests/test_install.py`.
   **rollback**: `git revert <commit>`.
   **done when**: the workflow `ai-eng init` writes calls `ai-eng audit verify` with no
   argument, and `anchor_commits` is gone from the configuration it seeds.

## Block B — the code behind it (Tasks 4–6)

4. **The three history verdicts and the pattern that fed them are deleted** —
   **file** `src/ai_engineering/audit.py`.
   **check**: `uv run pytest -q tests/test_record.py tests/test_mut_accept.py`.
   **rollback**: `git revert <commit>`.
   **done when**: `ANCHOR`, `HISTORY_INCOMPLETE_PREFIX`, `_history_findings`, `_anchor_line`
   and `anchor_line` are gone, and `audit verify` still refuses a link that arrived edited.

5. **The doctor loses one line and keeps twenty-five assertions** —
   **file** `src/ai_engineering/doctor.py`.
   **check**: `uv run pytest -q tests/test_doctor.py`.
   **rollback**: `git revert <commit>`.
   **done when**: the anchor line is gone from assertion 11, the count is still 25, and the
   branch that detects a hijacked git-hooks path still fires.

6. **The fixture that captured the deleted function stops capturing it** —
   **file** `tests/conftest.py`.
   **check**: `uv run pytest -q tests/test_record.py tests/test_doctor.py`.
   **rollback**: `git revert <commit>`.
   **done when**: collection succeeds; a half-done rename here reds the whole suite at import
   rather than one test, because the fixture takes the function at import time.

## Block C — the promises, and the proof of the boundary (Tasks 7–8)

7. **Two published sentences that are about to be false are rewritten** —
   **file** `README.md`.
   **check**: `uv run pytest -q tests/test_contracts.py -k readme`.
   **rollback**: `git revert <commit>`.
   **done when**: the README row no longer offers `--anchors` as the command behind
   "survives losing the laptop", and `CHANGELOG.md` carries the hard deletion under the
   existing `### Breaking changes` block.

8. **The boundary is proved rather than asserted** —
   **file** `tests/test_contracts.py`.
   **check**: `uv run pytest -q tests/test_contracts.py -k anchored`.
   **rollback**: `git revert <commit>`.
   **done when**: a test names every `_anchored` path-safety reader and fails if one of them
   stops existing — so the next person deleting something called "anchor" is stopped by a
   command rather than by this plan's prose.

## Block close

`just check` green with its output shown, `just guards` at 16 of 16 with no mutant left in
the tree, and the adversarial suite at 21 of 21 run the way the gate runs it. Then the
honest sentence: `ai-eng audit verify` still exits 1 on this machine, for 22 links this work
deliberately did not repair.
