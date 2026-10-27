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

## F1 · BLOCKER · open
**Where:** `src/shared-worktree.ts:813-824,1250-1255`; `skills/ai-orchestrator/SKILL.md:48,265`
**Critic (r1):** `request-changes` only selects a live managed `feat/<slug>` worktree, and `findManagedWorktree` explicitly excludes the primary checkout. That makes the approved default-current-checkout flow (D1; the worktree is optional) unable to handle Phase 4's unconditional request-changes action: it refuses and cannot return the checkpoint to implementation. Support the selected current checkout with the same checkpoint-only CAS safeguards, or provide a working current-checkout transition in the ceremony.

## F2 · MAJOR · open
**Where:** `src/shared-worktree.ts:293-382,1244-1256`
**Critic (r1):** `worktree new` accepts arbitrary slash-qualified branches (I42 creates `feature/pagos`), but `worktree rm` only finds `feat/<slug>` branches under the managed root. Thus a branch the CLI successfully creates cannot be removed through its lifecycle command, contrary to D1's “no feat/ required.” Make `rm` address the exact registered branch/path created by `new`, or constrain `new` consistently with the approved naming contract.

## F3 · MAJOR · open
**Where:** `src/shared-worktree.ts:343-382`
**Critic (r1):** When a remote or configured base exists, `new` passes that base ref to `git worktree add`, not the current `HEAD`, despite CP8's creation contract. From a non-base feature checkout this silently omits that checkout's committed work from the new branch. Start from the invoking checkout's exact `HEAD` (and test from a non-base branch), or explicitly revise the checkpoint contract and ceremony wording.

## F4 · BLOCKER · open
**Where:** `src/shared-worktree.ts:1338-1352,1389-1397`
**Critic (r1):** `rm` inventories ignored files but proceeds to `git worktree remove` without requiring an explicit destructive choice; ignored files such as local environment data are then irreversibly deleted, with the warning only printed afterward. This contradicts the safe-rm/no-data-loss focus and §6.6's ignored-file protection. Refuse when ignored content exists and preserve the worktree unless the person explicitly authorizes that deletion before it occurs.
