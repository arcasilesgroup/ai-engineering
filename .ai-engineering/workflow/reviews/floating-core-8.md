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

## F1 · BLOCKER · upheld
**Where:** `src/shared-worktree.ts:813-824,1250-1255`; `skills/ai-orchestrator/SKILL.md:48,265`
**Critic (r1):** `request-changes` only selects a live managed `feat/<slug>` worktree, and `findManagedWorktree` explicitly excludes the primary checkout. That makes the approved default-current-checkout flow (D1; the worktree is optional) unable to handle Phase 4's unconditional request-changes action: it refuses and cannot return the checkpoint to implementation. Support the selected current checkout with the same checkpoint-only CAS safeguards, or provide a working current-checkout transition in the ceremony.

**Fixer (r2):** fixed — `worktreeRequestChanges` accepts the exact current checkout while retaining SHA validation and compare-and-swap; verify: `bun test tests/worktree-command.spec.ts tests/worktree-lifecycle.spec.ts`, `bun run typecheck`, `bun run lint`, `bun test tests/arch.spec.ts` ✓
**ROOT CAUSE:** The selector accepted only the managed sibling path, excluding the primary checkout even when it held the exact feature branch.
**FIX:** Accept the sole exact `feat/<slug>` entry when it is either the canonical current repository or the validated managed path; the existing checkpoint-only transaction and ref CAS remain unchanged.
**LESSON:** Optional worktrees require lifecycle transitions to recognize the current checkout without weakening feature identity or SHA guards.
**Critic (r2):** upheld — the added regression covers a current primary checkout on `feat/<slug>` only. The selector at `src/shared-worktree.ts:817` still infers `feat/${slug}`, so an allowed current checkout on an arbitrary branch such as `feature/pagos` still cannot request changes under D1. Resolve the checkpoint slug in the selected checkout without assuming a branch prefix, retaining the SHA and compare-and-swap guards.

## F2 · MAJOR · resolved
**Where:** `src/shared-worktree.ts:293-382,1244-1256`
**Critic (r1):** `worktree new` accepts arbitrary slash-qualified branches (I42 creates `feature/pagos`), but `worktree rm` only finds `feat/<slug>` branches under the managed root. Thus a branch the CLI successfully creates cannot be removed through its lifecycle command, contrary to D1's “no feat/ required.” Make `rm` address the exact registered branch/path created by `new`, or constrain `new` consistently with the approved naming contract.

**Fixer (r2):** fixed — `findManagedWorktree` now validates either the exact typed branch or its `feat/` form against its derived managed path; verify: `bun test tests/worktree-command.spec.ts tests/worktree-lifecycle.spec.ts`, `bun run typecheck`, `bun run lint`, `bun test tests/arch.spec.ts` ✓
**ROOT CAUSE:** Removal inferred `feat/<slug>` even though creation preserves arbitrary branch names.
**FIX:** Search the raw branch and `feat/<slug>` candidates, accepting only the exact root-relative path each branch maps to; I42 now removes `feature/pagos` via `worktree rm feature/pagos`.
**LESSON:** Create and remove must share the same branch-to-path contract, not one command's naming convention.
**Critic (r2):** resolved — the arbitrary `feature/pagos` regression verifies the derived path and removes that exact registered branch; targeted lifecycle tests passed.

## F3 · MAJOR · resolved
**Where:** `src/shared-worktree.ts:343-382`
**Critic (r1):** When a remote or configured base exists, `new` passes that base ref to `git worktree add`, not the current `HEAD`, despite CP8's creation contract. From a non-base feature checkout this silently omits that checkout's committed work from the new branch. Start from the invoking checkout's exact `HEAD` (and test from a non-base branch), or explicitly revise the checkpoint contract and ceremony wording.

**Fixer (r2):** fixed — creation pins `fullHead(repo)` as its start commit while retaining detected-base upstream config and dirty-slot warnings; verify: `bun test tests/worktree-command.spec.ts tests/worktree-lifecycle.spec.ts`, `bun run typecheck`, `bun run lint`, `bun test tests/arch.spec.ts` ✓
**ROOT CAUSE:** Worktree creation used the detected base ref as its start point, silently dropping commits on the current feature branch.
**FIX:** Capture the current checkout's full `HEAD` SHA and pass that commit to `git worktree add`; a non-base real-Git regression proves ancestry and dirty brainstorm/PRD warnings remain.
**LESSON:** A detected integration base is not a substitute for the caller's current commit.
**Critic (r2):** resolved — the non-base checkout test verifies the new branch and worktree both start at the captured current `HEAD`; targeted lifecycle tests passed.

## F4 · BLOCKER · resolved
**Where:** `src/shared-worktree.ts:1338-1352,1389-1397`
**Critic (r1):** `rm` inventories ignored files but proceeds to `git worktree remove` without requiring an explicit destructive choice; ignored files such as local environment data are then irreversibly deleted, with the warning only printed afterward. This contradicts the safe-rm/no-data-loss focus and §6.6's ignored-file protection. Refuse when ignored content exists and preserve the worktree unless the person explicitly authorizes that deletion before it occurs.

**Fixer (r2):** fixed — ignored content is scanned before ancestry/removal, unknown scans and unforced data loss refuse; forced deletion warns before `git worktree remove`; verify: `bun test tests/worktree-command.spec.ts tests/worktree-lifecycle.spec.ts`, `bun run typecheck`, `bun run lint`, `bun test tests/arch.spec.ts` ✓
**ROOT CAUSE:** The scan only informed a post-removal report, so default removal silently destroyed ignored user files.
**FIX:** Refuse when ignored files exist without `--force` and list the exact paths; fail closed when inspection is unreadable, and print the exact irreversible deletion warning before executing forced removal.
**LESSON:** Inventory destructive data before every removal path and require an explicit, informed opt-in.
**Critic (r2):** resolved — `rm` refuses and preserves ignored files by default, refuses unreadable scans even with `--force`, and warns before an explicitly forced deletion; targeted tests passed.

## F5 · MAJOR · open (r2)
**Where:** `skills/ai-orchestrator/SKILL.md:48`
**Critic (r2):** The updated `worktree new` behavior starts from the current `HEAD`, as CP8 requires, but this ceremony line still says it creates from the detected base. That gives agents a materially incorrect source-ref expectation. Update it to say current `HEAD` is the start point and the detected base is retained for integration/upstream configuration.
