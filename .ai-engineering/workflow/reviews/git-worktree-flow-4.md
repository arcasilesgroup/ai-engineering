# Review · git-worktree-flow #4 — one safe cleanup pass, and a delete that refuses

## Goal
`skills/ai-git-cleanup` is rewritten from scratch as a single automatic pass with no interactive question: dead worktrees go first (`git worktree remove`, then `git worktree prune`), then branches with `git branch --delete-merged refs/heads/main`, falling back to `git branch --merged main` plus `-d` for branches that do not carry that upstream. It never deletes an unmerged branch and never asks for a name. The old `analyze.mjs` and its three specs are gone, the Trail of Bits attribution goes with the code, and `ai-eng worktree rm` stops force-deleting: it deletes with the delete that refuses an unmerged branch, and only an explicit `--force` removes one.

## Acceptance
1. The one pass removes dead worktrees and merged branches with `git branch --delete-merged refs/heads/main`, falling back to `git branch --merged main` + `-d` for branches without that upstream.
2. An unmerged branch is never deleted, `-D` never appears, and no name is ever asked.
3. The old script and its three specs are gone; the Trail of Bits attribution is removed from `NOTICE.md` and `THIRD-PARTY-NOTICES.md`.
4. The skill keeps a valid Lifecycle block and the embedded assets are in sync.
5. `ai-eng worktree rm` never force-deletes: it uses the delete that refuses an unmerged branch (which then survives), and removes one only with an explicit `--force` whose message states the reason.
6. The orchestrator's close prose verifies where the merge landed (`git merge-base --is-ancestor feat/<slug> main`) before the cleanup, and a gate checks that prose so a future edit cannot drop it.
7. The orchestrator's close and the verb describe the same deletion behavior, and no sentence in the skill promises a `git branch -D` that no longer exists.

## changed_files
- `skills/ai-git-cleanup/SKILL.md`
- `tests/git-cleanup-pass.spec.ts`
- `NOTICE.md`, `THIRD-PARTY-NOTICES.md`
- `src/shared-worktree.ts`
- `tests/worktree-command.spec.ts`
- `skills/ai-orchestrator/SKILL.md`
- `src/assets.ts` (regenerated)

## Verify commands
- `test ! -f skills/ai-git-cleanup/scripts/analyze.mjs`
- `test ! -f tests/git-cleanup-flow.spec.ts && test ! -f tests/git-cleanup-analyze.spec.ts && test ! -f tests/git-cleanup-cli.spec.ts`
- `rg -q 'delete-merged refs/heads/main' skills/ai-git-cleanup/SKILL.md`
- `rg -q -- '--merged main' skills/ai-git-cleanup/SKILL.md`
- `! rg -q 'Trail of Bits' NOTICE.md THIRD-PARTY-NOTICES.md`
- `! rg -q -- '-D' skills/ai-git-cleanup/SKILL.md`
- `rg -q 'worktree prune' skills/ai-git-cleanup/SKILL.md`
- `bun test tests/git-cleanup-pass.spec.ts`
- `bun test tests/worktree-command.spec.ts`
- `rg -q 'merge-base --is-ancestor' skills/ai-orchestrator/SKILL.md`
- `! rg -q 'branch -D' skills/ai-orchestrator/SKILL.md`
- `bun test tests/embed-canon.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun run build`

## Context the reviewer should know
Checkpoints 1-3 passed: the contract, the verb, and the orchestrator that calls it. This checkpoint is where the framework's own doctrine bites hardest: a control that cannot decide must deny, and a delete that cannot prove a branch landed must not erase it. The behavior gate of checkpoint 2 already proved that `ai-eng worktree rm` force-deleted an unmerged branch; acceptance 5 exists to close that.

## F1 · BLOCKER · fixed
**Where:** skills/ai-git-cleanup/SKILL.md:25-27
**Critic (r1):** The pass removes "every worktree whose branch is already merged" but says nothing about a worktree with no branch (detached HEAD), and `git worktree remove` handles one silently: a clean detached worktree is removed with exit 0 and its unique commits become unreachable from every ref (proved: after `git worktree remove`, `git branch -a --contains <sha>` is empty and `git fsck` reports the commit dangling; only the reflog holds it). The verb refuses exactly this state with a reason (src/shared-worktree.ts:331-334), so the pass is the loose half of the pair — and this repo already carries an orphan worktree (`ai-engineering-v1-oracle`). The checkpoint doctrine is "a control that cannot decide must deny"; the pass cannot name a branch to prove and does not deny. → Add the rule to step 1: a worktree whose HEAD is not on a branch is never removed, it is reported as kept; add the matching Safety invariant. Check: `git worktree add --detach ../w && git -C ../w commit --allow-empty -m x`, then read step 1 against it.

**Fixer (r1):** fixed — step 1 now reads `git -C <path> symbolic-ref -q HEAD` and removes only a branch-backed worktree; a detached HEAD is skipped and reported kept as "detached, no branch to prove", with the matching Safety invariant (SKILL.md:25-42, 69-71) · verify: hand test A — detached worktree holding a unique commit survives and is reported.

## F2 · MAJOR · fixed
**Where:** skills/ai-git-cleanup/SKILL.md:26-27 and :41-43
**Critic (r1):** "A dirty worktree is left in place: the removal is never forced, so an uncommitted change keeps its worktree" is false for ignored files. `git worktree remove` refuses only on modified or untracked (non-ignored) files; a worktree whose only uncommitted content is gitignored — a `.env`, a local DB, screenshots under the ignored `.ai-engineering/workflow/playwright/` — is removed without force and the content is destroyed (proved: worktree holding only `local.env` returned exit 0 and the file was gone). The safety invariant that promises "an uncommitted change keeps its worktree" therefore overstates what the verb guarantees. → Say the exception in step 1 (ignored files are not protected) and require a `git status --porcelain --ignored` / `git clean -ndX` look before removing, reporting a worktree with ignored content as kept instead of removed. Check: create that worktree and diff the prose against the observed exit 0.

**Fixer (r1):** fixed — step 1 requires `git status --porcelain --ignored` to be empty before removal; any non-empty status, ignored files included (`.env`, ignored screenshots), keeps the worktree and reports what the status listed; the overreaching "an uncommitted change keeps its worktree" sentence is replaced, and the Safety invariant states tracked/untracked/ignored all keep it (SKILL.md:25-42, 72-73) · verify: hand test B — a worktree whose only dirt is gitignored `local.env` survives.

## F3 · MAJOR · fixed
**Where:** skills/ai-git-cleanup/SKILL.md:31
**Critic (r1):** `git branch --delete-merged` is brand new: `/opt/homebrew/share/doc/git-doc/RelNotes/2.56.0.adoc` — "The 'git branch' command has been taught the '--delete-merged' option", and it is absent from every earlier release note. The skill states it as the primary path with no version floor and no instruction for the "unknown option" failure, so on any git older than 2.56 (the overwhelming majority of installs) step 3 errors, and it errors *after* steps 1-2 have already removed worktrees; step 4 is only offered "for a merged branch without that upstream", not for a git that does not know the flag. → State the floor (git ≥ 2.56) and add the degradation: an "unknown option" from step 3 falls through to step 4 for every merged branch. Check: `git branch --delete-merged refs/heads/main` on a git < 2.56, or read the RelNotes file.

**Fixer (r1):** fixed — step 3 states the git ≥ 2.56.0 floor, and says an `unknown option` failure is reported and falls through to step 4 for every merged branch instead of aborting the pass after steps 1-2 (SKILL.md:45-52) · verify: `git --version` = 2.56.0; prose covers the older-git degradation path.

## F4 · MINOR · fixed
**Where:** skills/ai-git-cleanup/SKILL.md:34-35
**Critic (r1):** "then delete each listed branch with `git branch -d <branch>`" — the list is `git branch --merged main`, which also carries the current branch (`* main`) and branches checked out in other worktrees (`+ feat/x`), decoration and all. Git refuses both, so no loss, but the pass trips over its own current branch on every run and reports failures it could have skipped. → Exclude the current branch and branches checked out in another worktree before deleting, and strip the `*`/`+` prefixes. Check: `git branch --merged main` output on a repo with one open worktree.

**Fixer (r1):** fixed — step 4 drops the current branch and any branch checked out in another worktree (the `*`/`+` decorated lines) and reads each remaining name without its decoration before `git branch -d` (SKILL.md:53-56) · verify: raw `git branch --merged main` showed `* main` and `+ feat/open`; the filtered list kept only the deletable candidate.

## F5 · MINOR · fixed
**Where:** skills/ai-git-cleanup/SKILL.md:31 and :34-35
**Critic (r1):** The two paths disagree about the same finished branch. One whose upstream is not `refs/heads/main` (say `origin/main`, or any lagging ref) is skipped by step 3 (upstream mismatch) and listed by step 4, where `git branch -d` refuses because it checks that other upstream, not `main` (proved: a branch merged into `main` with upstream `refs/heads/behind` survives both paths — step 3 silent, `-d` prints "not yet merged to 'refs/heads/behind'"). Not destructive, but the pass leaves merged work behind while claiming it removes "branches already merged into the local `main`". → Say that a `-d` refusal is a keep, and name the upstream mismatch as its cause. Check: the reproduction above.

**Fixer (r1):** fixed — step 4 states a `-d` refusal is a keep and is never retried, and names the upstream mismatch (a lagging `origin/main`, `refs/heads/behind`) as the cause, so a branch merged into `main` whose upstream lacks it is reported kept (SKILL.md:56-59) · verify: hand test C — `git branch -d` printed "not yet merged to 'refs/heads/behind'", step 3 silent, the branch survived.

## F6 · MINOR · fixed
**Where:** tests/git-cleanup-pass.spec.ts (no line pins it) vs skills/ai-orchestrator/SKILL.md:177
**Critic (r1):** Acceptance 6 wants the gate to check the close prose "so a future edit cannot drop it", but nothing persistent does: `tests/git-cleanup-pass.spec.ts` reads only the cleanup skill, and `rg -q 'merge-base --is-ancestor' skills/ai-orchestrator/SKILL.md` is a one-shot verify line that disappears with this checkpoint (grep for `merge-base` across `tests/` returns nothing). The prose is there today; the drop-proof gate is not. → Add one assertion to `tests/git-cleanup-pass.spec.ts` (read the orchestrator file, expect `merge-base --is-ancestor feat/<slug> main`), beside the prose pins it already carries. Check: `grep -rn merge-base tests/`.

**Fixer (r1):** not mine to fix — the test author landed it separately (commit `88422b6c`): `tests/git-cleanup-pass.spec.ts` now reads the orchestrator's close block, requires the merge check to name `feat/<slug>` and `main`, requires it to come before the removal, and forbids a force-delete in that file.
