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

## Round 2

**Critic (r2) · F1 → resolved.** Verified at SKILL.md:25-42 and :69-71: step 1 now gates on `git -C <path> symbolic-ref -q HEAD` naming a branch, a detached HEAD is skipped and reported kept, and the invariant exists. Re-ran the mechanics: `symbolic-ref -q HEAD` exits 1 on a detached worktree, 0 with `refs/heads/feat/x` on a branch — so the guard fires exactly where `git worktree remove` used to erase unreachable commits.

**Critic (r2) · F2 → resolved.** Verified: step 1 now requires `git -C <path> status --porcelain --ignored` to be empty, the false "an uncommitted change keeps its worktree" sentence is gone, and the invariant covers tracked/untracked/ignored. Proved the mechanism: in a worktree holding only an ignored `local.env`, `status --porcelain --ignored` prints `!! local.env` (non-empty → kept). (But see N1: this rule overshoots.)

**Critic (r2) · F3 → resolved.** Verified: step 3 states the `git ≥ 2.56.0` floor and the `unknown option` degradation to step 4. Floor is the real one — `/opt/homebrew/share/doc/git-doc/RelNotes/2.56.0.adoc`: "The 'git branch' command has been taught the '--delete-merged' option", absent from earlier RelNotes; local `git --version` is 2.56.0. Re-proved the degradation is safe: step 4's `-d` refuses an unmerged branch.

**Critic (r2) · F4 → resolved.** Verified: step 4 drops the `*`/`+` lines and reads names without decoration. Re-proved against raw output — `git branch --merged main` with one open worktree prints `+ feat/x` and `* main`, both now excluded before `-d`.

**Critic (r2) · F5 → resolved.** Verified: step 4 states a `-d` refusal is a keep, never retried, and names the upstream mismatch. Re-ran the reproduction (branch merged into `main`, upstream `refs/heads/behind`): step 3 silent, `-d` prints "not yet merged to 'refs/heads/behind'", branch survives — and now the skill says so.

**Critic (r2) · F6 → resolved.** Verified `88422b6c`: the new test reads the orchestrator's close block, requires `merge-base --is-ancestor` to name `feat/<slug>` and `main`, requires the last `worktree rm` to come after the check, and forbids `branch -D` in the file. All three specs green (38 pass). The gate is now persistent.

## N1 · MAJOR · fixed (r2)
**Where:** skills/ai-git-cleanup/SKILL.md:25-42 (with :72-73)
**Critic (r2):** F2's fix overshoots into acceptance 1. `git status --porcelain --ignored` is non-empty for anything gitignored, and this repo ignores the artifacts every session produces — `.ai-engineering/receipts/`, `.ai-engineering/cache/`, `.ai-engineering/workflow/playwright/`, `node_modules/` (`.gitignore`:1,8). A real checkout already reports `!! .ai-engineering/receipts/` and `!! .ai-engineering/cache/` with no work in it, so any worktree a session has ever touched is kept and step 1's `git worktree remove` becomes unreachable — the pass stops removing dead worktrees altogether, and the checkpoint's own complaint ("leftover copies pile up") stands. → Either state plainly that a worktree with ignored content is always kept and the pass removes only pristine worktrees (so the promise in the description is honest), or have step 1 list the ignored paths and keep the worktree only when they cannot be regenerated. Check: create a merged worktree, `mkdir -p .ai-engineering/receipts && touch .ai-engineering/receipts/r.json`, then read step 1 against it — it is kept forever.

**Fixer (r2):** fixed — step 1 now separates regenerable output from data: it removes a worktree whose ignored entries are entirely on the named list (`node_modules/`, `dist/`, `coverage/`, `.stryker-tmp/`, `reports/`, `.ai-engineering/receipts/`, `.ai-engineering/cache/`, `.ai-engineering/workflow/playwright/`) and keeps it when anything else is ignored, always naming the ignored paths found; the ceiling — "exactly what this framework regenerates, so anything else ignored is treated as data" — is stated in one line, and the "Uncommitted content keeps its worktree" invariant is updated (SKILL.md:25-50, 80-82) · verify: hand test A — a merged worktree whose only ignored content is `node_modules/` was removed without force and the report named it; `bun test tests/git-cleanup-pass.spec.ts` ✓.

## N2 · MINOR · fixed (r2)
**Where:** src/shared-worktree.ts:355-361 vs skills/ai-git-cleanup/SKILL.md:25-42
**Critic (r2):** The new rule puts the skill and the verb on opposite sides of the same worktree state. The skill keeps a worktree holding ignored content; `ai-eng worktree rm` has no status check at all and calls `git worktree remove` straight after the merge proof, so it removes that worktree and destroys the ignored files — proved for bare git, and the verb adds no guard (only `existsSync`, `worktree remove`, `branch -d`). The close calls the verb, so the flow's two halves disagree. → Say in the skill that the verb is the explicit-user path (it removes what the pass keeps), or add the same ignored-content check to `worktreeRm` with a `--force` to override. Check: `worktree new` + an ignored `local.env` + `worktree rm <slug>` → worktree gone, file gone.

## Round 3

**Critic (r3) · N1 → resolved.** Verified at SKILL.md:25-49 and :80-84: step 1 now allows a listed set of regenerable paths, keeps the worktree on anything else, and reports the ignored paths found. Re-proved the decision is reachable where it was not before: a worktree whose ignored entries are all listed is now removed, so acceptance 1 is live again — except for the gap in N4.

**Critic (r3) · N2 → resolved.** Verified at SKILL.md:85-90 and src/shared-worktree.ts:376-405: the invariant names the verb as the explicit human path, and `ignoredPaths` reads the worktree's ignored entries before the removal and prints them in the success message; the unmerged-branch refusal is untouched (tests re-run, 71 pass across the four suites). The claim "it prints the ignored paths it drops" is not yet true in every state — see N3.

## N3 · MAJOR · fixed (r3)
**Where:** src/shared-worktree.ts:197 (with skills/ai-git-cleanup/SKILL.md:25-31)
**Critic (r3):** `ignoredPaths` runs `git status --porcelain --ignored -z` without `--untracked-files=all`, so it inherits the repo's or the user's `status.showUntrackedFiles` config. With that set to `no` the command prints nothing at all — no `??`, no `!!` (proved: repo config and global config both yield an empty stdout). Consequence in the verb: a worktree holding only an ignored `local.env` is removed with exit 0, `local.env` is destroyed, and the success message names nothing, which is exactly the silent drop the N2 fix exists to prevent. Consequence in the pass: step 1's gate reads the same command, sees an empty status, concludes "every status entry is either absent or on the list", and removes it. The neighbouring slot guard in the same file already forces the option for this reason (`git(repo, ["status", "--porcelain", "-uall", "-z"])`, :230). → Add `--untracked-files=all` to the `ignoredPaths` call and to the command the skill prints. Check: `git config status.showUntrackedFiles no` + an ignored-only worktree → `worktree rm` prints no names and the file is gone; with the option the entry reappears.

**Fixer (r3):** fixed — `ignoredPaths` now runs `git status --porcelain --ignored -uall -z` (`src/shared-worktree.ts:200-201`), the same force the slot guard uses at :230, and the skill's step-1 read is `git -C <path> status --porcelain --ignored --untracked-files=all` with the reason stated inline (SKILL.md:28-32) · verify: hand test (a) — repo config `status.showUntrackedFiles no` + a worktree holding only ignored `local.env`: the old read (no `-uall`) printed nothing; the fixed read printed `!! local.env` and the verb printed `✓ removed worktree alpha — dropped ignored: local.env`; `bun test tests/worktree-command.spec.ts` ✓ (32 pass, includes U-CP4-d).

## N4 · MAJOR · fixed (r3)
**Where:** skills/ai-git-cleanup/SKILL.md:28-37
**Critic (r3):** The regenerable list omits `.DS_Store` and `.claude/reviews/`, both of which this repo ignores (`.gitignore:5` and `:8`), and `.DS_Store` is what macOS writes into every worktree a Finder window or any app touches. Under the new rule a worktree carrying only `!! .DS_Store` is "uncommitted content that is not regenerable" and is kept, so on this machine the pass is inert again — the same failure N1 was raised for, one gap over. Proved against this very checkout: `git status --porcelain --ignored` prints `!! .DS_Store` and `!! .ai-engineering/.DS_Store` with no work in progress. → Add the ignored, non-data entries the repo already declares (`.DS_Store`, `.claude/reviews/`, `*.bun-build`) to the list, or derive the list from the repo's ignore rules. Check: run step 1 against a merged worktree that has a `.DS_Store` → it is kept.

**Fixer (r3):** fixed — the regenerable bullet is now two named groups: the framework's rebuild output (unchanged) plus the system/editor noise this repository already ignores — `*.bun-build`, `.claude/reviews/`, `*.DS_Store` (SKILL.md:46-57); `*.DS_Store` is a one-segment glob, so a nested `.ai-engineering/.DS_Store` matches as `.DS_Store` does; the Safety invariant at :99-101 says the same · verify: hand test (b) — a merged worktree whose only ignored content is `.DS_Store`: the step-1 read printed `!! .DS_Store`, `git worktree remove` exited 0 and the pass names the dropped path; `bun test tests/worktree-command.spec.ts -t U-CP4-e` ✓ and `bun test tests/git-cleanup-pass.spec.ts -t U-CP4-f` ✓.

## N5 · MINOR · fixed (r3)
**Where:** skills/ai-git-cleanup/SKILL.md:28-37
**Critic (r3):** The list is written as bare names (`dist/`, `reports/`, `node_modules/`), not anchored to the worktree root, and `git status --ignored` collapses a fully ignored directory to one `!! dir/` line. So a nested or prefixed lookalike (`packages/x/dist/`, `reports-archive/`) can be read as "on the list", and a hand-written file inside an allowlisted directory is dropped while the report names only the directory — the report cannot show what it actually removed. → State that a match is the exact root-relative path, and say the report names directories, not their contents. Check: put a hand-written file in an ignored `dist/` → status prints `!! dist/` and step 1's list matches it.

**Fixer (r3):** fixed — the bullet now states the match is anchored, both sides worktree-root-relative: the printed path must be the entry itself or sit inside a listed root-relative directory, so a listed directory is taken whole; `packages/x/dist/out.js` is not `dist/` and `reports-archive/` is not `reports/` (SKILL.md:59-68); one line names the ceiling — a whole listed directory goes with it, so a hand-written file inside `dist/` is dropped with it. `-uall` also means the read prints each ignored file rather than collapsing a directory to one `!! dir/` line, so the report does name the paths it drops · verify: hand test (c) — an ignored `reports-archive/` and `packages/x/dist/` produced the entries `!! reports-archive/keep.txt` and `!! packages/x/dist/keep.txt`, neither of which is the listed `reports/` or `dist/`, so the worktree is kept as data; `bun test tests/git-cleanup-pass.spec.ts -t U-CP4-g` ✓.


**Fixer (r2):** fixed — the difference is now named, not hidden: the skill's Safety invariants say `ai-eng worktree rm` is the explicit human path (a person typed it, or the close ran it after the merge landed) and removes what the pass keeps, while the pass errs on keeping (SKILL.md:83-88); the verb reads the ignored paths before removing and prints them — `ignoredPaths` in `src/shared-worktree.ts:192-213`, used at :376-380, named in the success message at :399-405 — the merge refusal is untouched · verify: hand test C — `ai-eng worktree rm c` printed `✓ removed worktree c — dropped ignored: local.env` and the worktree was gone; `bun test tests/worktree-command.spec.ts` ✓.
