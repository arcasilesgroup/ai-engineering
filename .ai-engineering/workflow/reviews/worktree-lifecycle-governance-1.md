# Checkpoint goal
Remove `.ai-eng-worktrees.json` reads and writes and the optional file arguments from worktree creation, while preserving configured roots, slug validation, Git inventory, branch creation from local `main`, merged-branch protection and safe removal.

## Acceptance criteria
- `ai-eng worktree new <slug>` rejects extra positionals before creating a directory or branch.
- `new` and `rm` neither read, create, update nor delete a legacy manifest, including malformed contents.
- Configured paths, slug validation, Git listing, branch creation from local `main`, merged-branch protection and safe removal remain covered.

## changed_files
- `src/shared-worktree.ts`
- `src/commands/worktree.ts`
- `tests/worktree-command.spec.ts`

## verify
- `bun test tests/worktree-command.spec.ts`
- `bun test tests/arch.spec.ts`
- `bun run typecheck`
- `bun run lint`

VERDICT: PASS
