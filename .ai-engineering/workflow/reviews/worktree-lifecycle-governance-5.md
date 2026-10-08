# Checkpoint goal
Rebase a clean feature worktree only onto local `main` before final app review, resolve only clear conflicts in that worktree, and rerun affected gates before recording review state.

## Acceptance criteria
- Sync uses the current local `refs/heads/main` only; it does not fetch remote state or merge a sibling branch.
- Dirty or untrusted work is preserved. Clear conflicts are resolved only in the feature worktree; unclear conflicts/check failures abort and preserve it.
- Affected behavior/UI/review gates pass after sync and before app review.
- Record the exact full local-main `reviewed_main`, then set `awaiting-app-review` and app review pending.

## changed_files
- `skills/ai-orchestrator/SKILL.md`
- `tests/worktree-lifecycle.spec.ts`
- `tests/skills.spec.ts`
- `tests/workflow-handoff.spec.ts`
- `LEARNINGS.md`

## verify
- `bun test tests/worktree-lifecycle.spec.ts`
- `bun test tests/skills.spec.ts`
- `bun test tests/workflow-handoff.spec.ts`
- `python3 tests/test_checkpoint_gate.py`
- `bun scripts/gen-assets.ts`
- `bun test tests/embed-canon.spec.ts`
- `bun test tests/arch.spec.ts`
- `bun run typecheck`
- `bun run lint`

## Adversarial review — FAIL

### F1 · High · Phase 3 mutates work it says to preserve
`skills/ai-orchestrator/SKILL.md` Step 1 says that missing, dirty, unknown, or untrusted worktrees must be preserved, but then requires writing `phase: blocked` into their checkpoint. A missing worktree cannot be written; an untrusted or dirty checkpoint may be unsafe to touch, and writing it mutates the dirty state. This contradicts Phase 0's explicit no-mutation stop and defeats the dirty/unknown preservation gate. Stop and report without writing lifecycle state whenever the worktree is missing, dirty, unknown, or untrusted; add a regression asserting the checkpoint and whole worktree snapshot remain unchanged.

### F2 · Medium · Failed-gate fixture tests the forbidden rollback
`tests/worktree-lifecycle.spec.ts` U22 restores the rebased branch with `git reset --hard`, while the skill requires a clean-worktree/branch guard and `git reset --keep`. The fixture therefore passes even if the prescribed safe rollback is replaced by a destructive one, and never tests that dirty content blocks restoration. Exercise the stated guard and `--keep` behavior; assert the original branch/worktree state is preserved.

### F3 · Medium · UI gate rerun can disappear without failing tests
The skill correctly requires affected UI checks when applicable after rebase, but U20–U22 only assert behavior-to-review ordering, and the handoff test U23 also skips the UI-gate position. Removing or moving the UI rerun after review would leave these checks green. Assert UI reruns (when applicable) occur after rebase and before the review gate / app-review handoff.

## Assigned fix follow-up

### F1 · High · Failed rebase can write blocked state before preservation is proved
The abort path must complete first. The skill now verifies the original feature branch, commit, tree and clean status before writing `phase: blocked`; failed abort or any mismatch stops without checkpoint mutation or a clean-preservation claim.

### F2 · Medium · Conflict fixture used destructive rollback
The temporary Git fixture now leaves rebase active through the failing gate, uses `git rebase --abort`, and verifies exact refs, status, checkpoint bytes and feature content before changing lifecycle state.

### F3 · Medium · Gate order was not enforced
The post-conflict sequence is behavior, UI only when the checkpoint has a UI gate, then review, before Phase 4 app review; the skill and handoff assertions enforce that order, and U21 records it.

## Fix verification
- Passed: worktree lifecycle, skill contract and workflow handoff tests.
- Passed: asset generation and embedded-canon test.
- Passed: typecheck, lint and diff hygiene; lint/typecheck reported only existing warnings outside the changed files.
