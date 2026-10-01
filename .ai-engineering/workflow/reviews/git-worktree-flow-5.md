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

## F1 · BLOCKER · fixed
**Where:** skills/ai-pr/SKILL.md:133-137 vs :156-160
**Critic (r1):** Phase 6 arms `gh pr merge --auto` whenever the checks are green, while the never-bent rules say "A green pull request is not a request to merge one" and the triggers that fire this skill are "open a PR", "make the pull request", "push this" — none of which asks to merge. The skill cannot satisfy both; an agent reading Phase 6 as the default merges a pull request the human only asked to open, which is the one thing the checkpoint says must never happen. → Gate Phase 6 on an explicit merge request (say what wording counts), and make clear which wins when the ask was "open". Check: run the "open a PR" trigger on a repo without branch protection and see whether it merges without a further human go.

**Fixer (r1):** fixed — the contradiction is gone and one rule wins: running this skill **is** the human's request to finish the pull request (SKILL.md:29), stated as the first line the run prints (SKILL.md:30-31). The old "a green pull request is not a request to merge" rule is replaced by "never merge outside the ask" (SKILL.md:224-226), and the open-only ask is now an explicit mode: "open the pull request only" opens, states it stops before merging, and never merges (SKILL.md:33-35, Phase 6 skip at :184). `bun test tests/ai-pr.spec.ts` ✓ (U-PR-b).

**Fixer (r2):** fixed — the verb the human uses now decides the run, and the plain phrase stops at the pull request. The line that routed it in is gone: SKILL.md:21-23 no longer says "when the human says open the pull request, run the phases", it now says the verb decides how far the run goes — open stops after Phase 3, finish/land/merge it continues through Phase 6. The ask section (SKILL.md:28-49) names the two shapes, makes plain "open" and any ambiguous ask open-only with no Phase 6, and states a green pull request is never the merge trigger; the frontmatter description carries the same rule. verify: `bun test tests/ai-pr.spec.ts` ✓ (15 pass, U-PR-b).

## F2 · MAJOR · fixed
**Where:** skills/ai-pr/SKILL.md:137
**Critic (r1):** `gh pr merge <number> --auto` names no strategy (`-s`/`-m`/`-r`); with more than one merge method enabled on the repo gh prompts interactively and, in a non-tty agent context, fails, and "Pick the merge strategy the repository allows" gives no command to determine which one it allows. → State the command that reads the allowed methods and pass the flag explicitly. Check: `gh pr merge --help` semantics for a repo with two methods enabled (the help text names the merge-queue case as the only exception).

**Fixer (r1):** fixed — the merge now names its strategy: `gh pr merge <number> --squash --auto` (SKILL.md:194), chosen by a stated rule ("`main` history decides — no merge commits on `main` means `--squash`", SKILL.md:186-187), with the allowed set read from `gh api repos/{owner}/{repo} --jq '{squash:.allow_squash_merge,…}'` (SKILL.md:192-193). `gh pr merge --help` ✓ (flags `-s/--squash`, `--auto`, `--disable-auto`, `-d/--delete-branch` all exist as written).

## F3 · MAJOR · fixed
**Where:** skills/ai-pr/SKILL.md:54, :40-42, :57-61
**Critic (r1):** The "origin/main is behind it" precondition is asserted, never verified: no `git fetch` runs before Phase 1/3 (it appears only after a rejected push), so `git log --merges origin/main..HEAD` reads a possibly stale ref. If local `main` is behind or has diverged, nothing detects it and the PR body misstates what the branch carries. → Fetch before Phase 1 and check `git rev-list --left-right --count origin/main...main`. Check: move `origin/main` ahead, then run Phases 1-3.

**Fixer (r1):** fixed — Preconditions now fetch before any range is read (`git fetch origin`, SKILL.md:52) and classify the ground with `git rev-list --left-right --count origin/main...main` (SKILL.md:53-64): left/right reads normal, behind, or diverged, and behind/diverged stop. The first `origin/main..HEAD` read is now behind that fetch (Phase 1, SKILL.md:97). `bun test tests/ai-pr.spec.ts` ✓ (U-PR-d).

## F4 · MAJOR · fixed
**Where:** skills/ai-pr/SKILL.md:100-104, :133
**Critic (r1):** "Distinguish the workflows that gate the merge from the ones that only inform" states no rule for telling them apart — the brainstorm lists the real gate as an open question over seven workflows — so the agent classifies by guess and can arm auto-merge while the real gate is red or pending. → Name the gating set (from `.github/workflows/` and branch protection) instead of leaving it to judgement. Check: which workflow blocks a PR to `main`? The skill cannot answer.

**Fixer (r1):** fixed — Phase 4 now reads the real set instead of guessing: `gh api repos/{owner}/{repo}/branches/main/protection --jq '.required_status_checks.contexts'` (SKILL.md:141), with `gh pr checks <number> --required` (SKILL.md:144) listing exactly those for this pull request. "The rest of the workflows only inform" states the advisory rule (SKILL.md:145-148); a running/queued gate is not passed. `bun test tests/ai-pr.spec.ts` ✓ (U-PR-f).

## F5 · MAJOR · fixed
**Where:** skills/ai-pr/SKILL.md:100-129
**Critic (r1):** The poll loop has no stuck bound — the deleted skill had "Max 3 polls before declaring CI stuck" plus `gh run list --branch ... --json status,conclusion`, and its diagnosis discipline (`gh run view <id> --log-failed`, "first actionable error, the rest are cascades", classify logic/infrastructure) is dropped; Phase 5 says only "read the failure ... the failed logs". A queued check polls forever and the loop falls back to guessing. → Carry the poll cap and the `--log-failed` first-error rule over. Check: diff `git show 17268d56^:skills/ai-pr-loop-fix/SKILL.md` steps 2-4 against Phase 4-5.

**Fixer (r1):** fixed — the stuck bound is back: "Poll at most 3 times while a check stays queued or in progress, then declare CI stuck and stop" (SKILL.md:150-151), with `gh run list --branch <branch> --limit 1 --json databaseId,status,conclusion` (SKILL.md:154). The diagnosis discipline is carried over: `gh run view <run-id> --log-failed`, "scan for the first actionable error, because the rest are usually cascades", classify obvious/logic/infrastructure (SKILL.md:167-172). `bun test tests/ai-pr.spec.ts` ✓ (U-PR-e).

**Fixer (r2):** fixed — the wait interval is back: "Wait 30 seconds between polls and poll at most 3 times ... after the third poll, declare CI stuck and stop" (SKILL.md:165-169), and a stuck check is now an end state in "Done when" (SKILL.md:271-272) that names the check still queued or in progress and the last run's state. verify: `bun test tests/ai-pr.spec.ts` ✓ (U-PR-e), `bun run typecheck` ✓.

## F6 · MINOR · fixed
**Where:** skills/ai-pr/SKILL.md:46-48
**Critic (r1):** `git switch main` then `git switch -c <branch> main` has no path for a branch that already exists (a re-run), a dirty primary checkout, or a local `main` that is behind; `git switch -c` fails with a raw error the skill never handles. → Check for the existing branch and refuse with a named reason. Check: run Phase 1 with `<branch>` already present.

**Fixer (r1):** fixed — Phase 1 names all three states before cutting (SKILL.md:86-95): an existing branch is reused with `git switch <branch>` (a re-run adds to the same pull request), a dirty primary tree refuses with the files named, and a behind/diverged local `main` is caught by the Preconditions.

## F7 · MAJOR · fixed
**Where:** tests/ai-pr.spec.ts:50-55, :57-61, :24-30
**Critic (r1):** The spec pins the current wording, not the behaviour: "never deletes a remote branch" asserts only the absence of `git push --delete` forms and never `--delete-branch` on `gh pr merge` — the exact flag SKILL.md:154 forbids — so acceptance criterion 2 is unpinned; "merges only when the human asked" is three loose regexes over "human", "ask", "merge" that also pass on "merge whenever it is green"; the body test accepts any of assemble/build/compose/derive. → Add `expect(skill).not.toMatch(/--delete-branch/)` and assert the actual gate, not word presence. Check: text that merges unasked passes today.

**Fixer (r1):** fixed — not by me: the test author (Cp5Tests) tightened the spec in the same working tree, and the new cases pin the behaviour the critic named: `U-PR-a` asserts the merge command carries no `--delete-branch`, `U-PR-b` asserts running the skill is the request to finish plus an explicit open-only mode, `U-PR-c..f` pin the strategy/gating/poll rules. `bun test tests/ai-pr.spec.ts` ✓ (15 pass).

## F8 · MINOR · fixed
**Where:** skills/ai-pr/SKILL.md:133-137
**Critic (r1):** Nothing syncs the local `main` with `origin/main` after the merge, so the next run's precondition ("origin/main is behind it") is false after the first PR, and local `main` is permanently behind the remote it just fed. → Add the post-merge fetch/sync step. Check: merge one PR, then compare `origin/main` with local `main`.

**Fixer (r1):** fixed — Phase 7 is the last step: `git fetch origin`, `git switch main`, `git reset --hard origin/main` (SKILL.md:208-210), with the reason stated — a squash merge makes the two diverge, and the next run's precondition only holds from a level base — and a guard (only after the merge is reported, and only when the local `main` is exactly the batch that landed; otherwise report and leave it). This is the step that makes Phase 0's "behind" case true again.

## Rulings — round 2 (verified against 99f05dd9 and 1141017d)

**F1 · upheld.** SKILL.md:29-35 defines running the skill as the request to finish and gates the open-only mode on the words "open the pull request only", but SKILL.md:22 still says "When the human says open the pull request, run the phases below in order" — the plain canonical phrase, without "only", enters the phase list that ends in Phase 6. The relabelling moved the hazard, it did not remove it: a run triggered by "open the pull request" still arms auto-merge. The counter-argument that "running is the request" cannot silence the skill's own line 22, which is what routes that phrase in. Check: invoke with the words "open the pull request" and observe whether Phase 6 runs.

**F2 · resolved.** `gh pr merge <number> --squash --auto` (SKILL.md:194) matches the stated rule (SKILL.md:187): `origin/main` carries 0 merge commits over 165 commits, so the rule selects squash, and `gh api .../repo` reports `squash:true, merge:true, rebase:true`, so `--squash` is allowed; the flag exists in gh 2.101.0. Rule and command agree on the observable target.

**F3 · resolved.** The fetch (SKILL.md:52) precedes every range: the classification at :53-64 and the body range at :97. Behind and diverged both stop.

**F4 · resolved for this repository.** `gh api repos/arcasilesgroup/ai-engineering/branches/main/protection --jq '.required_status_checks.contexts'` returns six contexts (check, security, the three init-doctor matrix legs, e2e) and `gh pr checks --required` exists in gh 2.101.0, so the gating set is read, not guessed. See F10 for the unprotected-repo case.

**F5 · upheld.** The cap returned (SKILL.md:150-151) but with no wait interval: the deleted skill said "wait 30s and poll again", while the new text gives no cadence, so three back-to-back polls can declare a healthy CI "stuck" and stop — the loop stopping where it should have continued — and declaring CI stuck is not one of the three conditions in "Done when".

**F6 · resolved.** Phase 1 (:86-95) names the existing branch, the dirty tree and the behind/diverged main.

**F7 · resolved.** U-PR-a (tests/ai-pr.spec.ts:66-72) pins the absence of `--delete-branch`, U-PR-b..f pin the ask, the strategy, the fetch, the caps and the required checks; 15 pass locally. See F11 for what is still loose.

**F8 · resolved.** Phase 7 (:206-219) levels the local main after the merge. See F9 for the guard it lacks.

## F9 · MAJOR · fixed
**Where:** skills/ai-pr/SKILL.md:210, :217
**Critic (r2):** `git reset --hard origin/main` destroys the local `main` — the shared trunk every closed session merges into — and its guard ("only when the local `main` is exactly the batch that just landed") is a judgement with no command behind it; nothing verifies that no other session merged a feature after the pull request was cut, and the guard's own failure mode says "report and leave the local `main` alone" without saying how to tell. → Replace the prose guard with the count that decides it, and stop on any other value. Check: merge a second feature into the local `main` after the PR is cut, then run Phase 7 and see whether the reset discards it.

**Fixer (r2):** fixed — the hard reset is gone. Phase 7 is a fast-forward-only update, `git merge --ff-only origin/main` (SKILL.md:227-231), which moves the local `main` only when it holds nothing `origin/main` lacks — so a feature a later session merged in is refused, never discarded. The refusal path is named: report `git log --oneline origin/main..main` and leave the local `main` alone for the human to level (SKILL.md:233-241), and "Done when" carries the refused case. verify: `bun test tests/ai-pr.spec.ts` ✓.

**Fixer (r3):** fixed — the merge method is now a **merge commit**, `gh pr merge <number> --merge --auto` (SKILL.md:206-217): the local `main` is the integration trunk and the merge commit is the only method that leaves it in `origin/main`'s ancestry, which is what lets Phase 7 fast-forward — a squash strands it. The selection rule now says exactly that, and if the repository disallows merge commits the skill stops and reports rather than choosing a second strategy (SKILL.md:209-212). Phase 7 verifies the landing first with `git merge-base --is-ancestor main origin/main` and stops on non-zero, then fast-forwards (SKILL.md:230-253). Hand-walked in a throwaway repo: `--merge` PR → ancestor exit 0, `--ff-only` advances, `origin/main...main` back to `0 0`; an extra session merge after the PR leaves the ancestor check exit 1 (refused). verify: `bun test tests/ai-pr.spec.ts` ✓.

## F10 · MINOR · fixed
**Where:** skills/ai-pr/SKILL.md:139-145
**Critic (r2):** Phase 4's gating set comes only from branch protection; an unprotected branch, a fork, or a token without admin makes that endpoint return 404 and the skill then has no rule at all — the agent falls back to guessing and may treat the real gate as advisory. → State the fallback (treat every check as gating, or stop and say the gate is unknown). Check: run the `gh api .../protection` call on an unprotected branch.

**Fixer (r2):** fixed — Phase 4 states the fallback: when the query fails (unprotected branch, fork, token without admin) nothing gating that the run can verify exists, so it arms no auto-merge and waits for the human's explicit word before Phase 6, saying the gating set could not be read (SKILL.md:155-160). Phase 6 repeats the rule (SKILL.md:200-204). verify: `bun test tests/ai-pr.spec.ts` ✓ (U-PR-f).

## F11 · MINOR · new (r2)
**Where:** tests/ai-pr.spec.ts:103, :120-124
**Critic (r2):** U-PR-e matches any digit within forty characters of the word "poll/attempt", and the unchanged "merges only when the human asked" test is still the three loose regexes that also pass on "merge whenever it is green". The suite pins wording there, not behaviour. → Assert the number (3 polls, 5 iterations) and drop or replace the vacuous ask test. Check: text saying the merge is unconditional passes both today.

## F12 · MINOR · fixed
**Where:** skills/ai-pr/SKILL.md:187
**Critic (r2):** the strategy rule names "`main`" without saying which ref; the local `main` gains a merge commit the first time a session closes with `git merge --no-ff` (AGENTS.md, Git workflow), after which the rule read against the local ref flips to merge-commit while the command at :194 stays `--squash`, and Phase 7's reset story assumes squash. → Say `origin/main` and make the API set authoritative. Check: add a `--no-ff` merge to the local main and re-run the rule.

**Fixer (r2):** fixed — the rule names the ref: "the history of the remote branch the pull request targets, `origin/main`", no merge commits on `origin/main` means `--squash` (SKILL.md:205-210), so the local `main`'s `--no-ff` merges no longer flip it; the API allowed-set remains the correction, and Phase 7 states it assumes the squash shape. The command stays `gh pr merge <number> --squash --auto`. verify: `bun test tests/ai-pr.spec.ts` ✓ (U-PR-c).

ROUND 2: resolved 6 · withdrawn 0 · upheld 2 · new 4

## Rulings — round 3 (verified against 92505046)

**F1 · resolved.** The verb decides (SKILL.md:30-46): "open"/"make the PR" runs Phases 1-3 and stops, "finish"/"land"/"merge it"/"get the PR merged"/"run the full PR loop" carries through Phase 6, and an ambiguous ask is the open one; Phase 6 (:198-202) skips on open or ambiguous. No sentence claims running the skill is itself the request to finish, and U-PR-b's last assertion fails any sentence that merges on "green" without a request verb. No verb reaches the merge without naming it.

**F5 · resolved** (with F14). The interval is back at 30 s with the 3-poll cap and "CI stuck" is now an end state in Done when (:165-168, :270-272).

**F10 · resolved.** When the protection query fails the run does not arm auto-merge and waits for the human's word (:158-161); Phase 6 repeats the ban (:199-201).

**F12 · resolved.** The rule now names the target ref, `origin/main` (:208).

**F11 · resolved.** U-PR-e now demands the interval and the cap's outcome, and U-PR-b's mergesOnGreen assertion fails a text that merges whenever the checks pass; 15 pass locally.

**F9 · upheld.** `git merge --ff-only origin/main` (:231) cannot succeed in the case the skill itself mandates: the rule picks `--squash` (:208), and a squash merge puts one new commit on `origin/main` whose history does not contain the batch the local `main` carries, so the local `main` is not an ancestor of `origin/main` and the fast-forward refuses — the refusal text at :238-239 concedes exactly this. Phase 7 only fast-forwards after a merge-commit merge, the one strategy the rule rejects. Check: merge a batch with `--squash`, then `git merge-base --is-ancestor main origin/main` → false.

## F13 · MAJOR · fixed
**Where:** skills/ai-pr/SKILL.md:73, :234-240, :268
**Critic (r3):** because Phase 7 cannot level a squash-merged `main`, every completed run leaves the local `main` and `origin/main` diverged (`origin/main...main` shows both sides non-zero), and the Preconditions then stop the next run at "the branches diverged" (:73) — the skill can publish once and never again, and Done when's first clause ("levelled with `origin/main`") is unreachable. → Either state the level that works with squash (a verified `reset --hard` bounded by a count) or make the divergence a recoverable state with a stated command. Check: run the skill twice in a row against a repo using squash.

**Fixer (r3):** fixed by the F9 change — the merge commit puts the local trunk in `origin/main`'s ancestry, so the `--ff-only` in Phase 7 actually advances and the divergence never forms. Hand-walked two full runs in a throwaway repo: run 1 ends `origin/main...main` = `0 0`; run 2's pre-publish count is `0 2` (local ahead — the Preconditions' normal case, not "diverged"), and it ends `0 0` again. Done when's "levelled" clause is reachable. verify: `bun test tests/ai-pr.spec.ts` ✓.

## F14 · MINOR · fixed
**Where:** skills/ai-pr/SKILL.md:165-168
**Critic (r3):** three polls 30 s apart is 90 s; a GitHub Actions queue plus an e2e run and a three-OS matrix routinely exceeds that, so a healthy, merely slow CI is declared "stuck" and the run ends there — a false stuck, which is the other half of the attack. → Back off or raise the total wait, and keep "stuck" for a check whose run state has not moved. Check: the workflow set's own queue and run time against 90 s.

**Fixer (r3):** fixed — the count is gone; Phase 4 polls every 30 seconds up to a total 30-minute budget, stated as a cap on how long the run waits for a stuck check, not on how many looks (SKILL.md:165-169), and Done when names that budget (SKILL.md:283-284). A check whose run state has not moved at budget end is stuck; the report names the check, its last run state and how long it was watched. verify: `bun test tests/ai-pr.spec.ts` ✓ (U-PR-e).

ROUND 3: resolved 5 · withdrawn 0 · upheld 1 · new 2

## Rulings — round 4 (verified against ff2b653d)

**F9 · resolved.** The merge is now a merge commit, `gh pr merge <number> --merge --auto` (SKILL.md:206-217), the repository allows it (`allow_merge_commit: true`; `required_linear_history: false`), and the rule, the command and Phase 7's rationale (:206-211, :244-247) all say the same thing. Reproduced: base → local `main` carrying two `--no-ff` feature merges → PR branch + `fix: ci` → origin gains the merge commit → `git merge-base --is-ancestor main origin/main` = YES, `git merge --ff-only` succeeds, `origin/main...main` = `0 0`.

**F13 · resolved.** The batch history survives the merge commit, so the level step completes and the next run starts from `0 N` (local ahead) instead of diverged; and when a session merged after the PR was cut the ancestry check returns non-zero and Phase 7 stops instead of overwriting (:238-243, reproduced: `is-ancestor` = NO after a later local merge).

**F14 · resolved.** The cap is now a 30-minute poll budget at 30 s intervals (:165-168), with the stuck end state in Done when (:272-274) — no false stuck at 90 s and no unbounded loop.

## F15 · MAJOR · fixed
**Where:** skills/ai-pr/SKILL.md:81-84 vs :124
**Critic (r4):** Phase 1 promises the re-run ("a second run adds to the same pull request instead of a second one"), but Phase 3 runs `gh pr create` unconditionally; on that re-run gh exits non-zero ("a pull request for branch X into branch main already exists") and no phase says what to do — and this is the skill's own recovery path, since a CI-stuck stop (:166-168) can only be resumed by running it again. → Say to skip Phase 3 and read the number with `gh pr view --json number` when the pull request already exists. Check: run the skill twice against the same branch.

**Fixer (r4):** fixed — Phase 3 now checks before it creates (SKILL.md:117-131): the run opens with one line, "A re-run continues the same pull request", then asks the branch whether it already has an open pull request — `gh pr view <branch> --json number,state` — and reuses it: a non-zero exit ("no pull requests found for branch") means none, so the create runs; an `<number>` with state `OPEN` skips the create and carries that number into Phases 4-6; any other state is reported with the run stopped because that pull request is already closed or merged. `gh pr view [<number> | <url> | <branch>]` is the documented usage in gh 2.101.0 (`gh pr view --help` ✓). Hand-walked in a throwaway repo (bare remote, private): push pr/walk twice — second `git push -u` exit 0 (up to date) — first create makes PR #1, then `gh pr view pr/walk --json number,state` = `1 OPEN` and the create is skipped, while the old unconditional `gh pr create` on that same re-run exits non-zero with `a pull request for branch "pr/walk" into branch "main" already exists: <url>`. verify: `bun test tests/ai-pr.spec.ts` ✓ (U-PR-g, 17 pass).

## F16 · MINOR · fixed
**Where:** skills/ai-pr/SKILL.md:213-217
**Critic (r4):** the merge command has no rejection branch: a conflict, a denied method at PR time, or a protection rule the API query does not surface makes `gh pr merge` exit non-zero and the run has no instruction (the r1 wording that read gh's rejection was dropped in the r3 rewrite). → State that a rejected merge is reported with gh's message and the pull request left open. Check: `gh pr merge --merge` on a conflicting pull request.

**Fixer (r4):** fixed — Phase 6 states the rejection branch right after the merge command (SKILL.md:234-238): when `gh pr merge` fails with a non-zero exit code — a conflict, a method the repository denies at merge time, or a protection rule the API query did not surface — report gh's message, leave the pull request open and stop; never retry the merge blindly, and never force it through. This is the same end state Done when already names (a non-obvious failure is reported with evidence and the pull request is left open). verify: `bun test tests/ai-pr.spec.ts` ✓ (U-PR-h, 17 pass).

ROUND 4: resolved 3 · withdrawn 0 · upheld 0 · new 2
ROUND 5: fixed 2 · disputed 0 (F15 MAJOR, F16 MINOR)
