# Review thread · floating-core #9 · Make worktree creation and removal safe

## Goal
Worktree list/new/request-changes/rm honor arbitrary branch names, current-HEAD creation, design-file and ignored-file warnings, and safe deletion; the final ceremony contract excludes removed worktree commands.

## Acceptance
- I41: new creates from current HEAD, warns naming dirty brainstorm.html and PRD.html, and leaves both primary files unchanged.
- I42: new accepts any branch name, uses the configured or proposed path, and refuses existing branch/path conflicts naming the owning worktree.
- I44: rm refuses unintegrated work with the exact force command, warns about ignored files, never deletes dirty work, and force-removes a clean unintegrated tree.
- C15: src/ contains no refs/heads/main literal.
- C16: the ceremony contract passes after removed worktree rebase and file-hint citations are removed; the approved PR/local-merge/keep-branch choices remain intact.

## changed_files
- tests/worktree-command.spec.ts
- tests/worktree-lifecycle.spec.ts
- tests/ceremony-contract.spec.ts
- tests/skills.spec.ts
- tests/workflow-handoff.spec.ts
- tests/git-cleanup-pass.spec.ts
- FILEMAP.md
- skills/ai-brainstorm/SKILL.md
- skills/ai-orchestrator/SKILL.md
- skills/.chain-bundle/ai-eng-chain.ts
- src/commands/worktree.ts
- src/shared-worktree.ts
- src/workflow/checkpoint.ts

## Verify
- `bun test tests/worktree-command.spec.ts`
- `bun test tests/worktree-lifecycle.spec.ts`
- `bun test tests/ceremony-contract.spec.ts`
- `bun test tests/skills.spec.ts`
- `bun test tests/workflow-handoff.spec.ts`
- `bun test tests/git-cleanup-pass.spec.ts`
- `bun test ./tests/git-context.spec.ts`
- `bun test tests/workflow-checkpoint.spec.ts`
- `sh -c '! grep -rn "refs/heads/main" src'`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`
- `bun test --parallel=1`

## F1 · MAJOR · open
**Where:** src/shared-worktree.ts:318,390-391
**Critic (r1):** The containment check is lexical, but `mkdirSync(dirname(target), { recursive: true })` follows an existing symlink inside the worktree root. With a branch like `feature/pagos` and `root/feature` symlinked outside the root, `worktree add` creates the checkout outside the configured root; `worktree rm feature/pagos` then cannot find it because `findManagedWorktree` requires the checkout to remain under that root. Resolve and verify the actual parent path remains inside the canonical root before adding, or refuse symlinked path components.
