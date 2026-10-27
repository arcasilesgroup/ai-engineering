# Review thread · floating-core #7 · Make the worktree optional and merge from any checkout

## Goal
`ai-eng worktree new|list|merge|request-changes|rm` work from a normal checkout or a worktree against the detected base, merge keeps the reviewed-SHA compare-and-swap, only colliding paths block, and `src/` has no `refs/heads/main` literal.

## Acceptance
- S3: merge works for a feature built in a normal checkout.
- S5: list shows only Git records and flags another active feature in this checkout.
- S8: resume with the feature's own dirty files continues without reset or stash.
- S9: foreign untracked files never block; a collision is refused with the path and next command.
- S10: a leftover unregistered folder is reported as not work.
- S11: base moved after review loses the CAS and invalidates the review.
- S17: new worktree with dirty design slots is created and warns.
- 0 `refs/heads/main` literals in `src/`; worktree verbs are exactly new, list, merge, request-changes, rm.

## changed_files
- tests/floor-gates.spec.ts
- tests/floor-hooks.spec.ts
- tests/ceremony-contract.spec.ts
- tests/worktree-command.spec.ts
- tests/worktree-lifecycle.spec.ts
- FILEMAP.md
- skills/ai-brainstorm/SKILL.md
- skills/ai-orchestrator/SKILL.md
- src/commands/worktree.ts
- src/floor/index.ts
- src/shared-worktree.ts
- src/workflow/checkpoint.ts
- src/git/merge.ts
- LEARNINGS.md

## Verify
- `bun test tests/worktree-command.spec.ts`
- `bun test tests/worktree-lifecycle.spec.ts`
- `bun test tests/floor-gates.spec.ts`
- `bun test tests/floor-hooks.spec.ts`
- `bun test tests/git-context.spec.ts`
- `bun test tests/workflow-checkpoint.spec.ts`
- `bun test tests/ceremony-contract.spec.ts`
- `sh -c '! grep -rn "refs/heads/main" src'`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`
- `bun test --parallel=1`

## Gate 1 command 4 · tests/floor-hooks.spec.ts:300
- **ROOT CAUSE:** The fixture had no `[git] base` or remote HEAD, so `resolveContext` classified the base as `ask` and `prePush` correctly skipped the protected-base guard before reaching Gitleaks. The fixture contains no secret, and `src/floor/index.ts` checks the detected base before scanning.
- **FIX:** Create a feature commit, configure `main` as the base, prove `refs/heads/main` physically points to that commit and `resolveContext` reports `baseSource: "config"`, then assert the exact detected-base rejection with Gitleaks absent from PATH. No production change.
- **LESSON:** Physical branch presence is not base/lifecycle certainty: prove the physical ref and its classification together, and test the exact guard reason; an unresolved base remains `ask`.

## Replanned CP7 review scope

Automatic replan split the previous CP7 into CP7 (detected-base merge/CAS/push) and CP8 (list/new/resume/rm and ceremony contracts). This review covers only the CP7 runtime merge and push slice.

### Goal
`ai-eng worktree merge` works from any checkout against the detected base, integrates only reviewed work, preserves exact parents and tree with a compare-and-swap, and pre-push protects the detected base.

### Acceptance
- S3: merge works for a feature built in a normal checkout.
- S9: foreign untracked files never block; a collision is refused with the path and next command.
- S11: base moved after review loses the CAS and invalidates the review.
- I30-I33: normal, linked and unrelated checkouts resolve the correct source; zero or multiple candidates are refused.
- I34-I36: CAS loss invalidates review, collisions refuse safely, and non-colliding foreign files remain unchanged.
- I37-I38: only allowed checkpoint commits are included; the base checkout advances only when clean on incoming paths.
- I46: pre-push protection follows the detected base.

### changed_files
- tests/floor-gates.spec.ts
- tests/floor-hooks.spec.ts
- tests/worktree-command.spec.ts
- FILEMAP.md
- skills/ai-orchestrator/SKILL.md
- skills/.chain-bundle/ai-eng-chain.ts
- src/commands/worktree.ts
- src/floor/index.ts
- src/shared-worktree.ts
- src/workflow/checkpoint.ts
- src/git/merge.ts
- LEARNINGS.md

### Verify
- `bun test tests/worktree-command.spec.ts`
- `bun test tests/floor-gates.spec.ts`
- `bun test tests/floor-hooks.spec.ts`
- `bun test ./tests/git-context.spec.ts`
- `bun test tests/workflow-checkpoint.spec.ts`
- `bun test tests/ceremony-contract.spec.ts`
- `sh -c '! grep -rn "refs/heads/main" src'`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`
- `bun test --parallel=1`

## F1 · MAJOR · open
**Where:** `src/git/merge.ts:626-630`
**Critic (r1):** The retry path finds a previously published merge but refreshes base checkouts from that historical merge even when `currentBase` has since advanced. A clean checkout at the newer tip can have incoming paths reset to the old tree, leaving newer committed content overwritten in the worktree. Refresh from the current base tip and verify it is still the target; otherwise leave the checkout untouched and report it.

## F2 · MAJOR · open
**Where:** `src/git/merge.ts:501-509`
**Critic (r1):** `initialStatuses` is captured before the temporary merge/commit, then trusted during checkout refresh. If an incoming path becomes dirty during that transaction (including from a hook), the stale clean snapshot authorizes `git restore --worktree` to overwrite it. Revalidate incoming index/worktree state against the reviewed base immediately before restoring; preserve and report any changed path.

## F3 · MAJOR · open
**Where:** `src/floor/index.ts:177-178`
**Critic (r1):** Any `resolveContext` failure is swallowed and treated as no protected base, so malformed or unreadable base configuration allows pre-push to continue without this guard. Fail closed on resolution errors and give the caller a concrete base-resolution step.
