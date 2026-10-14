# Review scope
Bounded review of the CP6 atomic merge transaction and its real-Git tests.

## Goal
Publish only a human-approved feature based on the exact reviewed local-main SHA, preserve work on any compare-and-swap loss, and remove the feature worktree only after exact merge parent and ancestry proof.

## Acceptance criteria
- Pending and approved lifecycle updates after `reviewed_feature` change only the feature checkpoint file.
- The temporary merge commit has first parent `reviewed_main` and second parent the approved feature branch tip; `reviewed_feature` is an ancestor and intervening commits are checkpoint-only.
- `git update-ref refs/heads/main <merge> <reviewed_main>` is the only publication path.
- CAS loss publishes no stale merge, retains the feature/checkpoint, removes only clean temp worktrees, and supports safe retry.
- CAS success safely refreshes primary, verifies exact parents/ancestry, and calls safe non-force feature removal.

## Files
- `src/shared-worktree.ts`
- `src/commands/worktree.ts`
- `scripts/checkpoint-gate.py`
- `tests/worktree-command.spec.ts`
- `tests/test_checkpoint_gate.py`

## Finding

- **CP6-CAS-1 · HIGH · fixed — `src/shared-worktree.ts`:** The transaction verifies the temporary commit's parents and cleanliness, but not that commit hooks preserved the reviewed merge tree. A normal `pre-commit` hook could stage content outside the reviewed result.

## Fix response

The merge index tree is now captured with `git write-tree` before `git commit`; after normal hooks run, the temporary commit tree must match that snapshot before CAS publication. A mismatch refuses publication and cleans only the temporary merge worktree. Real-Git regression U32a stages an extra file from `pre-commit` and verifies local main, feature worktree/tip, checkpoint bytes, and other worktree state remain unchanged. `bun test ./tests/worktree-command.spec.ts`: 63 passed, 0 failed.
