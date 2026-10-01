# Review · git-worktree-flow #5 — the full pull-request loop

## Goal
A new `skills/ai-pr` walks the whole pull-request loop: cut the PR branch from the local `main` without a worktree, push, open the pull request against `main` with a body assembled from the merge commits the branch carries, watch CI and review comments, fix only what is obvious in bounded iterations, and merge with auto-merge on by default and a stated way to switch it off. `skills/ai-pr-loop-fix` is deleted.

## Acceptance
1. `skills/ai-pr` exists, has a Lifecycle block, and documents the full loop: branch from local main without a worktree, push, PR against main, CI/review watch, bounded obvious fixes, merge.
2. Auto-merge is on by default and can be switched off; remote branch deletion never appears.
3. `skills/ai-pr-loop-fix` is gone and the embedded assets are in sync.

## changed_files
- `skills/ai-pr/SKILL.md` (new)
- `skills/ai-pr-loop-fix/` (deleted)
- `tests/ai-pr.spec.ts` (new)
- `src/assets.ts` (regenerated)

## Verify commands
- `test -f skills/ai-pr/SKILL.md && test ! -d skills/ai-pr-loop-fix`
- `rg -q 'gh pr create' skills/ai-pr/SKILL.md`
- `rg -q 'gh pr merge' skills/ai-pr/SKILL.md`
- `bun test tests/ai-pr.spec.ts`
- `bun test tests/embed-canon.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun run build`

## Context the reviewer should know
Checkpoints 1-4 passed: the contract, the verb, the orchestrator, the cleanup. This skill is the human's path from the local `main` to `origin`, so it is the one place in the framework where a push is legitimate — and the only place that must never act unless the human asked for it. Its predecessor (`ai-pr-loop-fix`) fixed CI and then stopped, which is why this one exists.
