# Review thread · floating-core #8 · Complete worktree lifecycle commands and ceremony contracts

## Goal
`worktree list|new|request-changes|rm` and resume behavior match the approved contracts, obsolete rebase and file-hint usage is rejected, and the skill/ceremony contract no longer cites removed commands.

## Acceptance
- S5: list shows only Git records and flags another active feature in this checkout.
- S8: resume with the feature's own dirty files continues without reset or stash.
- S10: a leftover unregistered folder is reported as not work.
- S17: new worktree with dirty design slots is created and warns.
- No `refs/heads/main` literal remains in `src/`; worktree verbs are exactly new, list, merge, request-changes, rm.
- I39-I45: list, new, resume, rm and request-changes match observable contracts and reject removed usages.
- C15-C16: no main literal remains in src, and the ceremony contract has no removed worktree command citation.

## changed_files
- tests/ceremony-contract.spec.ts
- tests/worktree-command.spec.ts
- tests/worktree-lifecycle.spec.ts
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
