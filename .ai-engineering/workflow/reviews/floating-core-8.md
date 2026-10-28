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

## F1 · BLOCKER · resolved
**Where:** `src/shared-worktree.ts:813-824,1250-1255`; `skills/ai-orchestrator/SKILL.md:48,265`
**Critic (r1):** `request-changes` only selects a live managed `feat/<slug>` worktree, and `findManagedWorktree` explicitly excludes the primary checkout. That makes the approved default-current-checkout flow (D1; the worktree is optional) unable to handle Phase 4's unconditional request-changes action: it refuses and cannot return the checkpoint to implementation. Support the selected current checkout with the same checkpoint-only CAS safeguards, or provide a working current-checkout transition in the ceremony.

**Fixer (r2):** fixed — `worktreeRequestChanges` accepts the exact current checkout while retaining SHA validation and compare-and-swap; verify: `bun test tests/worktree-command.spec.ts tests/worktree-lifecycle.spec.ts`, `bun run typecheck`, `bun run lint`, `bun test tests/arch.spec.ts` ✓
**ROOT CAUSE:** The selector accepted only the managed sibling path, excluding the primary checkout even when it held the exact feature branch.
**FIX:** Accept the sole exact `feat/<slug>` entry when it is either the canonical current repository or the validated managed path; the existing checkpoint-only transaction and ref CAS remain unchanged.
**LESSON:** Optional worktrees require lifecycle transitions to recognize the current checkout without weakening feature identity or SHA guards.
**Critic (r2):** upheld — the added regression covers a current primary checkout on `feat/<slug>` only. The selector at `src/shared-worktree.ts:817` still infers `feat/${slug}`, so an allowed current checkout on an arbitrary branch such as `feature/pagos` still cannot request changes under D1. Resolve the checkpoint slug in the selected checkout without assuming a branch prefix, retaining the SHA and compare-and-swap guards.
**Fixer (r3):** fixed — resolve the exact checkpoint in the Git-listed current or managed checkout and use its registered branch ref for the preserved SHA/CAS guards; verify: `bun test tests/worktree-command.spec.ts tests/worktree-lifecycle.spec.ts tests/workflow-handoff.spec.ts tests/ceremony-contract.spec.ts`, `bun run typecheck`, `bun run lint`, `bun test tests/arch.spec.ts` ✓
**ROOT CAUSE:** The source selector and ref checks inferred `feat/<slug>` instead of using the branch attached to the checkout holding that slug's checkpoint.
**FIX:** Select the sole current or branch-derived managed checkout carrying the exact slug checkpoint, then use its Git-listed branch ref for all existing reviewed-SHA and compare-and-swap checks; a real Git worktree on `feature/<slug>` now transitions successfully.
**LESSON:** Resolve lifecycle ownership from the exact checkpoint and Git checkout identity, not from a branch naming convention.
**Critic (r2):** resolved — the selector uses the exact checkpoint path, accepts the primary checkout or exact managed path, then validates the Git-listed branch ref against the supplied full SHA; the arbitrary `feature/<slug>` test exercises the managed path.

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

## F5 · MAJOR · resolved
**Where:** `skills/ai-orchestrator/SKILL.md:48`
**Critic (r2):** The updated `worktree new` behavior starts from the current `HEAD`, as CP8 requires, but this ceremony line still says it creates from the detected base. That gives agents a materially incorrect source-ref expectation. Update it to say current `HEAD` is the start point and the detected base is retained for integration/upstream configuration.
**Fixer (r3):** fixed — corrected only the source sentence; Phase 3 rebase and Phase 4 merge handoff remain unchanged; verify: `bun test tests/worktree-command.spec.ts tests/worktree-lifecycle.spec.ts tests/workflow-handoff.spec.ts tests/ceremony-contract.spec.ts`, `bun run typecheck`, `bun run lint`, `bun test tests/arch.spec.ts` ✓
**ROOT CAUSE:** The ceremony sentence still described the pre-CP8 start ref after `worktree new` had changed to use current `HEAD`.
**FIX:** State that creation starts at current `HEAD` and warns dirty brainstorm/PRD files do not travel; leave the detected-base rebase and merge handoff intact.
**LESSON:** Keep source-ref documentation aligned with command behavior while distinguishing creation from integration.
**Critic (r2):** resolved — the skill now says `worktree new` starts from current `HEAD` and warns dirty brainstorm/PRD files do not travel; Phase 3 still uses native `git rebase <detected base>`.

## F6 · BLOCKER · resolved
**Where:** `src/shared-worktree.ts:359-386`
**Critic (r1):** `worktreeNew` resolves `repo` to the primary checkout, then reads its dirty design slots and `HEAD` even when invoked from another Git-listed checkout. From a linked feature worktree with unique commits or dirty brainstorm/PRD files, it starts the new worktree from the wrong checkout and omits the required warning. Read source `HEAD` and dirty-slot status from the invoking checkout; keep the primary root only for registration and destination resolution, and test invocation from a diverged, dirty linked worktree.
**Fixer (r2):** fixed — `worktree new` reads branch, status, and HEAD from the invoking checkout while retaining the primary root for shared refs and worktree registration; a real linked-worktree regression covers caller HEAD, branch, and dirty design preservation · verify: targeted tests 133 pass/0 fail, typecheck, lint, arch 31 pass ✓
**ROOT CAUSE:** `worktreeNew` used the primary root for both shared Git metadata and checkout-specific branch/status/HEAD reads.
**FIX:** Separate the invoking checkout from the primary root; derive source branch, status, dirty-slot warnings, and start SHA from the caller, while retaining primary-root destination and registration behavior.
**LESSON:** Shared repository metadata may use the primary checkout, but source state must come from the checkout that invoked the command.
**Critic (r2):** resolved — source branch, status, and HEAD now come from the invoking linked checkout, and the added real-worktree regression verifies its diverged HEAD and dirty design slots are preserved and reported.

## F7 · MAJOR · resolved
**Where:** `skills/ai-orchestrator/SKILL.md:46,265-268,285`
**Critic (r1):** The ceremony still says changes are committed on `feat/<slug>`, tells Phase 4 request-changes to run from the primary checkout, and claims the command accepts only a managed `feat/<slug>` worktree. The implementation now resolves the exact checkpoint and Git-listed branch ref, including the current checkout and arbitrary branch names; this stale guidance contradicts D1 and can route request-changes to a rejected checkout. Describe exact-checkpoint/current-or-managed checkout selection without assuming `feat/`, and align the branch wording.
**Fixer (r2):** fixed — updated the request-changes procedure to resolve the exact Git-listed checkpoint checkout and actual branch ref, and made branch wording convention-neutral · verify: targeted tests 133 pass/0 fail ✓
**ROOT CAUSE:** The ceremony retained managed-`feat/<slug>` and primary-checkout assumptions after lifecycle selection became checkpoint- and ref-based.
**FIX:** Document the exact current-or-managed checkout, pending checkpoint SHA, and actual branch-ref checks; describe commits and stop behavior on the selected branch without a naming convention.
**LESSON:** Ceremony guidance must name the same exact checkout and ref that the command validates, not infer either from a branch prefix.
**Critic (r2):** resolved — the skill now records the exact checkpoint-bearing checkout and its actual branch ref, allows any branch name, and no longer requires `feat/<slug>` or a primary-checkout-only invocation.

## F8 · MAJOR · resolved
**Where:** `skills/ai-orchestrator/SKILL.md:278-283`
**Critic (r1):** After app approval, Phase 4 unconditionally invokes local `ai-eng worktree merge <slug>`; it offers neither `/ai-pr` nor keeping the branch, and never gives the D9 recommendation (PR with a forge remote, local merge otherwise). Preserve the `worktree merge` handoff for the local-merge choice, but expose the approved closure choices and recommendation.
**Fixer (r2):** fixed — Phase 4 recommends PR with a forge remote and local merge otherwise, then offers PR, local merge, or keep-branch choices; the local merge transaction remains `ai-eng worktree merge <slug>` · verify: targeted tests 133 pass/0 fail ✓
**ROOT CAUSE:** App-review approval was treated as unconditional consent to the local merge transaction.
**FIX:** Expose the D9 route recommendation and human choice; reserve the existing merge handoff for the explicit local-merge choice and leave PR/keep-branch routes unmerged locally.
**LESSON:** App approval and integration route are separate decisions; preserve the human's choice after approval.
**Critic (r2):** resolved — Phase 4 now recommends PR with a forge remote and local merge otherwise, offers PR/local-merge/keep-branch, and retains `ai-eng worktree merge <slug>` only for the local-merge choice.

## F9 · MAJOR · fixed (r3)
**Where:** `src/shared-worktree.ts:819-828,1252-1266`
**Critic (r2):** `request-changes` still rejects a Git-listed native-harness worktree outside the configured managed root: it accepts the primary path, then requires every other candidate to satisfy `findManagedWorktree`. D1 prefers native harness worktrees, and the updated Phase 4 guidance says to resolve the current checkout. Allow the unique exact-checkpoint Git-listed checkout (retaining branch-ref, SHA, and CAS checks), and cover a native worktree outside the managed root.
**Fixer (r3):** fixed — `worktreeRequestChanges` now selects the sole branch-bearing Git-listed checkout carrying the slug checkpoint, independent of its path or branch prefix; the branch-ref, full-SHA, CAS, and lifecycle checks remain; a real-Git regression uses `native/<slug>` outside the managed root; verify: targeted tests 122 pass/16 skip, typecheck, lint, arch 31 pass ✓
**ROOT CAUSE:** The selector rejected non-primary checkouts unless their paths matched the configured managed-root layout, before the existing SHA and lifecycle checks could run.
**FIX:** Select the unique Git-listed checkout with the exact checkpoint path and branch, then retain all existing branch-ref, full-SHA, CAS, and lifecycle validation.
**LESSON:** Resolve lifecycle ownership from Git registration and checkpoint identity; managed-directory layout is not checkout identity.

## F10 · MINOR · fixed (r3)
**Where:** `src/shared-worktree.ts:296,360-376`
**Critic (r2):** `source` is `process.cwd()`, not the caller checkout's root. When `worktree new` runs from a nested directory such as `src/`, Git status is scoped there and does not report root-level `.ai-engineering/brainstorm.html` or `PRD.html`; the path matcher therefore misses those dirty slots and omits the required warning. Resolve the invoking checkout root before scanning and test from a nested directory.
**Fixer (r3):** fixed — `worktreeNew` resolves the invoking checkout with `git rev-parse --show-toplevel` before scanning status; a nested-directory regression verifies brainstorm/PRD warnings, unchanged status, and preserved source bytes; verify: targeted tests 122 pass/16 skip, typecheck, lint, arch 31 pass ✓
**ROOT CAUSE:** `git status` ran from the nested process directory, so root-level design-slot paths were outside its reported scope.
**FIX:** Resolve the invoking checkout root first and run the existing root-relative dirty-slot scan there; leave the files unstaged and unmoved.
**LESSON:** Normalize Git status to the checkout root before applying repository-root path rules.

## F11 · MAJOR · fixed (r2)
**Where:** `src/shared-worktree.ts:584-606,623-646`
**Critic (r1):** `worktree new` accepts arbitrary branch names and D1 says `feat/` is not required, but `list`/resume still recognizes features only from `feat/` and derives the requested slug from the branch name. A Git-listed `feature/pagos` or native `native/pagos` checkout carrying `checkpoints/pagos.json` is therefore unclassified; `list pagos` cannot find it or report feature-owned dirty files as continuable versus foreign files left alone. Resolve feature identity from the exact checkpoint slug in registered checkouts (refusing ambiguity) and add a resume regression for an arbitrary/native branch with both own and foreign dirty files.
**Fixer (r2):** fixed — `worktree list` now resolves exact checkpoint identities from Git-listed checkout paths, selects only the requested slug, and refuses duplicate checkpoint ownership; real-Git regressions cover native branches, unrelated checkpoints, unregistered folders, dirty-file safety, and ambiguity · verify: targeted 124 pass/16 skip, typecheck, lint, arch 31 pass ✓
**ROOT CAUSE:** Listing inferred identity from `feat/<slug>` and branch-derived slugs, so registered arbitrary-branch checkouts never reached exact checkpoint or dirty-file handling.
**FIX:** Validate checkpoint slugs within Git-registered worktree paths, use that identity for list/resume and dirty-file ownership, filter unrelated checkpoints, and return an ambiguity refusal for duplicate registered identities; preserve legacy branch/path handling.
**LESSON:** Resume ownership comes from a validated checkpoint in a real Git registration, not a branch prefix or directory name.
**Critic (r2):** resolved — the targeted real-Git test confirms `list <slug>` finds the exact checkpoint on an arbitrary `native/topic` worktree, excludes an unregistered copy and an unrelated checkpoint, distinguishes owned from foreign dirty files without changing the worktree, and refuses duplicate ownership.

## F12 · MAJOR · open (r2)
**Where:** `src/shared-worktree.ts:514-539,592-605,652-658,723-745`
**Critic (r2):** Unfiltered `list` treats every valid checkpoint file in each registered worktree as an owner; stale checkpoints still get `identity: true` at lines 517-539. Checkpoint files committed to a base are inherited by later worktrees, so those historical copies are counted as duplicate ownership and can make ordinary `worktree list` exit 2 even when no feature is active in those checkouts. Resolve ownership using active lifecycle/ref evidence rather than file presence alone, and add a real-Git case where a base checkpoint is inherited by multiple worktrees; normal listing must remain usable while a genuinely duplicated active checkpoint is refused.
