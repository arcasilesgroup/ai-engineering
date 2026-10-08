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

## Round 2 follow-up review — FAIL
- F1 (requested abort-path criterion) — RESOLVED: Step 3 aborts first and forbids lifecycle writes if abort or restoration proof fails. U22 verifies the checkpoint remains unchanged during rebase, then checks abort success, original feature/main refs, branch, HEAD/tree, clean status, restored feature content and worktree registration before writing `blocked`.
- F2 — RESOLVED: The U22 fixture uses `git rebase --abort`, not `git reset --hard`; it verifies the saved refs, original tree/content, status and repository snapshot.
- F3 — RESOLVED: U21, the Phase 3 contract, and U20-U22/U23 ordering assertions place behavior, conditional UI, then review before Phase 4 app review.
- OPEN (original F1 pre-sync case): Phase 3 Step 1 still instructs writing `phase: blocked` for missing, dirty, unknown or untrusted worktrees. That contradicts preserving them; the dirty-precondition fixture does not assert checkpoint bytes remain unchanged. Stop without lifecycle writes in these cases and pin the unchanged snapshot.

## Round 3 finding resolution
- F1 pre-sync — RESOLVED: Phase 3 Step 1 now reports and stops without changing checkpoint or worktree files for missing, dirty, unknown or untrusted worktrees and missing/untrusted lifecycle state. U22 pins checkpoint bytes and the full Git snapshot for the dirty precondition; the focused lifecycle test passes.
- Abort-path criterion retained: an active unclear conflict is aborted first, and `blocked` is written only after original feature/main refs, tree and status are verified restored.

## Round 3 follow-up review — FAIL
- F4 · Medium · Phase 3 no-mutation coverage omits missing/unknown preconditions — OPEN: Step 1 correctly forbids writes for missing, dirty, unknown or untrusted pre-rebase state. U22 asserts checkpoint bytes and the full Git snapshot only for a dirty worktree; its abort fixture covers an active conflict, not missing/unknown Phase 3 preconditions. U16a checks those status words for Phase 0, not the Phase 3 sync boundary, while test-plan U22 claims missing/untrusted preconditions. Add a Phase 3 regression assertion for missing/unknown state preserving checkpoint bytes, refs, status and content.
- F1/F2 abort-path criteria — RESOLVED: the active conflict fixture uses `git rebase --abort` (no `git reset --hard`) and verifies original HEAD/tree/refs/status/content/checkpoint/worktree registration before writing `blocked`.
- F3 gate-order criterion — RESOLVED: workflow-handoff U23 orders behavior, conditional UI, review, then app-review handoff; the skill and U21 test-plan state the same sequence.

## Round 4 — FAIL

- **Counts:** resolved 3 (F1–F3); withdrawn 0; open 1 (F4).
- **F4 — U22 does not test the Phase 3 refusal (medium).** `tests/worktree-lifecycle.spec.ts:472` exercises only `runList` for missing, unreadable, and malformed lifecycle state. It does not test the Phase 3 decision to stop before rebase/checkpoint writes, so it would pass if the no-write guard were removed. Add a sync-refusal test for those states and assert the full snapshot remains unchanged.
- **Verified by reviewer:** conflict abort/original-state proof, gate ordering, and `reviewed_main` ordering passed; no `git reset --hard` in the fixture. Focused tests: 43 passed. Gate 1: nine verify commands passed after `8fca5927`.

## Round 5 — FAIL

- **Counts:** resolved 4 (F1–F4); withdrawn 0; open 1 (F5).
- **F1–F3 — RESOLVED:** the workflow now stops without mutation for untrusted pre-sync state, aborts and verifies restoration before recording `blocked`, and orders behavior, conditional UI, then review before app review.
- **F4 — RESOLVED:** U20b now drives the actual CLI sync boundary and proves no mutation for dirty, missing, malformed, legacy, unknown-phase, detached and mismatched-branch inputs using full repository snapshots.
- **F5 · Medium · local-main movement is detected only after an unrecovered rebase.** `src/shared-worktree.ts:707–725` runs `git rebase refs/heads/main`, then returns failure if `refs/heads/main` changed; it does not abort or restore the feature ref/tree, nor report which main SHA the completed rebase used. U20a tests a stationary main, and no CP5 test pins movement during the command. This leaves a rewritten feature worktree after a failed sync check, so Phase 3 cannot safely record or rely on the original target. Handle this path explicitly (preserve/restore after verifying the original state, or report a verified target and require gate reruns) and test movement plus preservation/recovery.
