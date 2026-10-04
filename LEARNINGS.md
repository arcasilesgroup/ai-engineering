# Learnings

Accumulated failures and lessons from building features, mostly written by `/ai-orchestrator`. Every planner, implementer, test writer and reviewer reads **Rules** before starting.

- **Log** is append-only: never edit or delete an entry.
- **Rules** is the distilled version. A lesson is promoted here once it has recurred (2 or more log entries) or caused a human-review rejection or a circuit-breaker stop. Each rule cites the entries it came from.

## Rules

- R1: Assert behaviour and exact contents, never a proxy such as source text or a bare type check. (from L2, L11)
- R2: Assert every field and linkage a consumer relies on — in a test, and in a guard that reads output: every path a record can carry, not one string that happens to equal the value. (from L13, L14, L22)
- R3: Cover every acceptance branch, and test each guard in the exact configuration where it alone stands between the input and the harmful path. (from L7, L12, L18)
- R4: Emit only commands whose target is unambiguous — pin the ref or worktree a command mutates, and never anchor what a command targets (default-branch selection during analysis included) to mutable HEAD. (from L16, L17; the cp2 adversarial review and behavior spot-check both passed it — run emitted commands in the current≠default configuration)
- R5: A test fixture must hold its premise against the real git state it creates — prove the input (sha, HEAD, count) before asserting the classification the code derives from it, and never let a fixture sit on the guarded branch, or it pins the bug it claims to forbid. (from L19, L20)
- R6: Enforce protection at the one choke point every categorization funnels through, not per path — a guard placed only where a test pinned one configuration is forgotten by the next path — and let every destructive step assert its own safety first, with a command an agent can run, before it deletes. (from L18, L20, L30)
- R7: Derive every list, count and path from the thing that owns it — the command's own contract, re-derived at write time — never a neighbour command's sweep, a remembered list, or a number copied into prose, which is only a cache of the command that produces it. (from L15, L21, L27)
- R8: Pin the scope of every read and fail closed: ambient mutable state — HEAD, a user or global git config — must not decide what it sees, an exit code is never the result (only the message naming the expected absence may branch), and a guard that cannot decide denies. (from L16, L23)

## Log

### L1 · 2026-09-26 · viewer-audit #1 · review
- **Failure:** Checkpoint 1 commit also shipped later-checkpoint CSS and headings.
- **Root cause:** One HTML file held every audit fix before the gates split the work.
- **Fix:** Restored the baseline and left only load() and the tick.
- **Lesson:** One checkpoint commits only that checkpoint's tasks.
- **Tags:** review, viewer

### L2 · 2026-09-26 · viewer-audit #1 · review
- **Failure:** Tests searched the source for strings and never ran load().
- **Root cause:** A string match stays green when the function does the wrong thing.
- **Fix:** Fake DOM and a fetch stub run load() and servedInit.
- **Lesson:** Assert behaviour, not source text.
- **Tags:** review, tests

### L3 · 2026-09-26 · viewer-audit #1 · review
- **Failure:** A served page with no plan showed the empty drop while the badge still said static.
- **Root cause:** The early return never set the badge.
- **Fix:** Set the badge to offline before that return.
- **Lesson:** Every empty path must set the badge.
- **Tags:** review, viewer

### L4 · 2026-09-26 · viewer-audit #1 · review
- **Failure:** The tick toggled empty and app again after load() had already done it.
- **Root cause:** Two owners for the same visibility.
- **Fix:** Deleted the extra toggle.
- **Lesson:** One owner for whether the empty screen shows.
- **Tags:** review, viewer

### L5 · 2026-09-26 · viewer-audit #1 · review
- **Failure:** A file that parsed but was not an object made render() throw.
- **Root cause:** load() trusted any JSON value.
- **Fix:** Reject non-objects before render.
- **Lesson:** Validate the plan's shape before render.
- **Tags:** review, viewer

### L6 · 2026-09-26 · viewer-audit #1 · review
- **Failure:** The rewritten tests failed typecheck.
- **Root cause:** The fixer only ran bun test.
- **Fix:** Give the node map fixed keys.
- **Lesson:** Run every verify command, not only the unit test.
- **Tags:** review, tests

### L7 · 2026-09-26 · viewer-audit #1 · review
- **Failure:** No test served invalid JSON through the tick.
- **Root cause:** The offline branch after a failed parse was never executed.
- **Fix:** A case sends broken JSON through servedInit.
- **Lesson:** Cover each acceptance branch, including the tick's offline path.
- **Tags:** review, tests

### L8 · 2026-09-26 · viewer-audit #2 · ui
- **Failure:** The empty screen showed a feature picker the prototype does not have, then a heading that used the page-title size.
- **Root cause:** The picker was created from the folder listing, and the drop heading inherited the page h1.
- **Fix:** Create the picker only after a plan loads. Size the drop heading and body on .drop only. Default the badge to offline.
- **Lesson:** Match an empty prototype by omitting the element, and scope drop type so it does not inherit the page title.
- **Tags:** ui, viewer

### L9 · 2026-09-26 · viewer-audit #2 · review
- **Failure:** Rebuilding the feature picker every 3 seconds closed an open menu.
- **Root cause:** The poll tick rewrote the select's options.
- **Fix:** Build the options only when the picker is created.
- **Lesson:** Never rebuild a live select on a poll tick.
- **Tags:** review, viewer


### L10 · 2026-09-27 · ai-git-cleanup #1 · behavior
- **Failure:** Unit layer failed: the dirty-worktree case aborted in fixture setup with `fatal: 'feature/dirty-wt' is already used by worktree` (13 pass, 1 fail).
- **Root cause:** The fixture checked out `feature/dirty-wt` in the main worktree, so `git worktree add` for that same branch was always refused before analyze() ran.
- **Fix:** Created the branch with `git branch feature/dirty-wt` while main stayed checked out; assertions unchanged, 14/14 green.
- **Lesson:** When a fixture needs a branch held by a linked worktree, create it without checking it out in the main worktree — git never allows the same branch checked out in two worktrees.
- **Tags:** tests, git, worktree

### L11 · 2026-09-27 · ai-git-cleanup #1 · review
- **Failure:** The unanalyzed test asserted only `toBeArray()`, so a bucket silently filling with misclassified branches stayed green.
- **Root cause:** A type check passes regardless of contents (LEARNINGS L2 in action).
- **Fix:** Assert `toHaveLength(0)`; mutating isInventoryComplete now fails the test.
- **Lesson:** Assert a bucket's expected contents, never only its type — an array check passes while the bucket silently fills.
- **Tags:** review, tests

### L12 · 2026-09-27 · ai-git-cleanup #1 · review
- **Failure:** The current-branch test exercised the LOCAL_WORK path, leaving the CURRENT_BRANCH guard untested; a merged checked-out branch could have reached deleteCandidates.
- **Root cause:** The test did not put the input in the exact configuration where the guard alone stands between it and the harmful path.
- **Fix:** New case: branch merged into default, left checked out at unique===0, asserting keep reason CURRENT_BRANCH.
- **Lesson:** Test each guard in the exact configuration where it alone stands between the input and the harmful path.
- **Tags:** review, tests, git

### L13 · 2026-09-27 · ai-git-cleanup #1 · review
- **Failure:** SAFE_TO_DELETE tests checked verifyWith but not `command`, so a `-D` mutation or lost quoting passed.
- **Root cause:** Only the neighbouring field the author happened to read was asserted.
- **Fix:** Assert the command exactly: `git branch -d 'feature/merged'`.
- **Lesson:** Assert every field a consumer will execute, not just the neighbouring field you happened to read.
- **Tags:** review, tests, git

### L14 · 2026-09-27 · ai-git-cleanup #1 · review
- **Failure:** worktreePath was assigned in analyze.mjs but no test tied the delete candidate to the worktree entry.
- **Root cause:** Propagation between two sections of one report was never asserted.
- **Fix:** Assert the candidate's worktreePath equals the worktree entry's path (macOS /private/var symlink accounted for).
- **Lesson:** Propagation between two sections of one report is only covered by an assertion that ties them together.
- **Tags:** review, tests, worktree

### L15 · 2026-09-27 · ai-git-cleanup #1 · review
- **Failure:** SKILL.md's produced-fields list omitted the `cluster` field the script emits.
- **Root cause:** Docs listed the fields the author remembered, not the fields the script can emit.
- **Fix:** Step 1 now documents cluster as informational.
- **Lesson:** If the script can emit a field, the produced-fields list must name it, or readers treat it as unknown data.
- **Tags:** review, docs

### L16 · 2026-09-27 · ai-git-cleanup #1 · review
- **Failure:** With no origin and no known local default, defaultBranch fell back to currentBranch — a repo whose HEAD sat on feature/x emitted `git branch -d 'mainline'`, the true default as a delete candidate.
- **Root cause:** defaultBranch anchored to mutable state (HEAD) instead of evidence.
- **Fix:** Removed currentBranch from the anchor list; empty anchor fails closed to unanalyzed NO_DEFAULT_BRANCH, pinned by a new test.
- **Lesson:** Never anchor default to mutable state like HEAD — moving the checkout would turn the repository's real default branch into a delete candidate.
- **Tags:** review, git, safety

### L17 · 2026-09-27 · ai-git-cleanup-v2 (live run) · human
- **Failure:** postSync emitted `git pull --ff-only 'origin' 'main'` while HEAD sat on feat/ai-git-cleanup-v2 — the command would mutate the CURRENT branch, not main; the person chose skip-sync instead of running it.
- **Root cause:** `git pull <remote> <branch>` always merges into HEAD; the emitter pinned the source ref but not the destination worktree/branch.
- **Fix:** (deferred to follow-up) emit a destination-pinned form or withhold the pull when current ≠ default.
- **Lesson:** Emit only commands whose target is unambiguous — a pull applies to HEAD, so a default-branch sync must pin the branch or worktree it mutates.
- **Tags:** human, git, safety, sync

### L18 · 2026-09-27 · ai-git-cleanup-v2 (live run) · human
- **Failure:** The current branch (feat/ai-git-cleanup-v2, upstream [gone]) landed in needsReview instead of the PROTECTED keep bucket; the skill's text claims the analyzer excludes current-by-name before analysis.
- **Root cause:** protection-by-name does not short-circuit the remoteGone/ambiguous triage path; the CURRENT_BRANCH guard only covers the merged/unique===0 configuration (the config the cp1 test pinned).
- **Fix:** (deferred to follow-up) apply the current/default protection filter before triage categorization, and pin with a test in the remoteGone configuration.
- **Lesson:** A protection filter must run before every categorization path, not only inside the one configuration a test pinned.
- **Tags:** human, git, safety, tests

### L19 · 2026-09-28 · ai-git-cleanup-v3 #1 · behavior
- **Failure:** Behavior gate failed at unit: analyze 25/30, cli 16/19 — fixtures held none of their premises (identical-sha cherry-picks landed in --merged, HEAD never returned to main so CURRENT_BRANCH was correct, deepPairs double-counted string leaves, ahead truth was 4 not 2), plus two assertions still speaking v2 vocabulary (`deleteCandidates`, a nonexistent `classification` section).
- **Root cause:** The tests asserted the classification they imagined instead of proving the git state (sha, HEAD, count) the code derives it from; two names came from loose plan wording rather than the authoritative shape pin.
- **Fix:** Message-distinct cherry-picks, checkout main before analyze, deepPairs skips primitives, ahead asserted 4, batch key, mode tests rewritten against the pinned sections (ruling: batch/keep/unanalyzed ARE the classification).
- **Lesson:** A test fixture must hold its premise against the real git state it creates — prove the input (sha, HEAD, count) before asserting the classification the code derives from it.
- **Tags:** tests, git, fixtures

### L20 · 2026-09-28 · ai-git-cleanup-v3 #1 · review
- **Failure:** The EMPTY_DIFF classification path lacked the isCurrent guard — a checked-out tree-identical branch was batched as `git branch -D` against itself (high); no test covered that exact configuration, and one cli fixture sat ON the buggy branch pinning it.
- **Root cause:** Protection was enforced per-path in some branches and forgotten in others, instead of at the single choke every categorization funnels through.
- **Fix:** One guard inside classify() before the only batch.push; per-path guards removed; new exact-config test; cli fixture moved off the branch.
- **Lesson:** A protection rule belongs in the one choke point every categorization funnels through, and every fixture must prove where HEAD sits — a test left sitting on the guarded branch silently pins the bug it claims to forbid.
- **Tags:** review, safety, git, tests

### L21 · 2026-10-01 · git-worktree-flow #2 · review
- **Failure:** The pre-worktree guard refused over a dirty design slot by trusting `git status`, which collapses a wholly untracked `.ai-engineering/` into one line, so it never fired on that shape; it also borrowed `spec close`'s slot list, which includes `recap.html` — a file generated at the app review and arriving with the merge — so a session that had not started could be blocked.
- **Root cause:** The guard asked git for a coarser granularity than it reasoned about, and it took its concept list from a neighbouring command's sweep instead of its own contract.
- **Fix:** Ask for `-uall`; give the guard its own pre-worktree list (brainstorm, spec, plan) while `SLOT_FILES` stays the sweep's single definition; `list` stops printing the primary checkout as a session.
- **Lesson:** A guard must ask git for the exact granularity it reasons about, and its concept list must come from its own contract, never a neighbouring command's sweep.
- **Tags:** review, guard, git, worktree

### L22 · 2026-10-01 · git-worktree-flow #2 · review
- **Failure:** The guard compared each status line to the slot path as one string, so a slot turned into a directory, and a slot carried on both sides of a rename, both sailed through and a worktree was cut over a dirty design artifact.
- **Root cause:** A status record is not one string — it carries an XY code and up to two paths — so matching one representative string missed every shape that carries the path elsewhere.
- **Fix:** Read the XY code, take every path the line carries (both sides of a rename), match by equality or by nesting under the slot, and refuse when the status itself is unreadable instead of passing.
- **Lesson:** A guard that inspects output must match the structure of the output — every path a record can carry — not one string that happens to equal the value.
- **Tags:** review, guard, git, worktree

### L23 · 2026-10-01 · git-worktree-flow #4 · review
- **Failure:** The ignored-path read omitted `-uall`, so a repository configured to hide untracked files printed nothing and the removal dropped content in silence while the pass read every worktree as regenerable; a clean worktree on a detached HEAD was removable and its commits became unreachable from every ref; and on the pull-request side any non-zero read counted as "no pull request", so a token or network failure could create a second one.
- **Root cause:** Reads whose scope the environment could narrow were allowed to define their own scope, the pass had no rule for the case it could not decide, and a non-zero exit was read as a result instead of a failed read.
- **Fix:** Force the read (`-uall`), keep what has no branch and what holds ignored files, treat a refusal as a keep, and branch only on the message naming the expected absence — every other failure reports and stops.
- **Lesson:** A guard that cannot decide must deny; a read that user configuration can silence must force its own scope, and an exit code is not a result — only the message naming the expected absence may branch.
- **Tags:** review, guard, git, safety

### L24 · 2026-10-01 · git-worktree-flow #5 · review
- **Failure:** The pull-request skill left a default (running it means finish the loop) and a rule (never merge on your own initiative) as two unranked sentences, so an agent had to arbitrate which one won.
- **Root cause:** A default and a rule were stated side by side without naming which one outranks the other.
- **Fix:** Running the skill is stated to be the request to finish the pull request, with an explicit open-only ask that stops before the merge; the merge names its strategy and the query listing the allowed ones; the preconditions fetch and compare before any range is read; the required checks come from branch protection, not a guess.
- **Lesson:** A rule and a default must be reconciled by naming which one wins, rather than left as two sentences for an agent to arbitrate.
- **Tags:** review, docs, orchestration

### L25 · 2026-10-01 · git-worktree-flow #5 · review
- **Failure:** The loop merged with a squash and then levelled the local `main` with a fast-forward — mutually exclusive: the squash gives the remote a commit whose history lacks the local trunk, so the level could never run and every later run stopped on a divergence the loop had caused.
- **Root cause:** The two ends of one loop were written independently, each choosing a history shape, with no single statement of the shape the loop requires.
- **Fix:** The merge is a merge commit — the only method that leaves the local trunk in the remote's ancestry — a repository that disallows it stops and says so, the level verifies ancestry before it fast-forwards, and the watch loop's cap becomes a time budget.
- **Lesson:** The two ends of a loop must agree on one history shape: a squash merge and a fast-forward level are mutually exclusive.
- **Tags:** review, git, docs

### L26 · 2026-10-01 · git-worktree-flow #5 · review
- **Failure:** A re-run — the skill's own recovery route — re-entered an unconditional `gh pr create`; gh refuses when a pull request for the branch already exists, so the path meant to resume was the one that broke.
- **Root cause:** The create never asked whether its artefact already existed, though the skill promised re-running as the recovery.
- **Fix:** Phase 3 reads the pull request first, continues the one that is open, creates only when there is none, and reports any other state; the merge states what a refusal does.
- **Lesson:** A promised re-run route is a caller: any unconditional create must first ask whether its artefact exists.
- **Tags:** review, git, docs

### L27 · 2026-10-01 · git-worktree-flow #6 · review
- **Failure:** The front page counted 21 skills against 29 shipped and 18 in its own table, and its image alt text promised a check count no output prints; two enumerations listed paths that no longer exist, and a file count was wrong the day it was written.
- **Root cause:** A count or a path written into prose is a cache of the command that produces it — it drifts the moment that command's output changes.
- **Fix:** Re-derive the count from the binary in all three places, drop the numbers no output can contradict, and delete the stale enumerations rather than bumping them.
- **Lesson:** A count or a path written into prose is a cache of the command that produces it; re-derive it or drop the number.
- **Tags:** review, docs, drift

### L28 · 2026-10-01 · git-worktree-flow #6 · review
- **Failure:** The contract's shared-files bullet carried only the merge half — "the merge step is their single writer in the primary tree" — which reads as a denial of the other half, and the blueprint still sold the retired model in its own heading and in the plan a reader follows.
- **Root cause:** A shared-ownership claim has two halves, and stating one alone turns it into a prohibition of the other.
- **Fix:** Restore the qualifier that scopes the split — a session may edit the shared files on its branch, and the merge step is their single writer in the primary tree — in the contract and the pages that echo it, putting the correction where the claim is made.
- **Lesson:** A shared-ownership claim must keep both halves, or the half stated reads as a denial of the other.
- **Tags:** review, docs, orchestration

### L29 · 2026-10-01 · git-worktree-flow #7 · review
- **Failure:** Half the addition to `ai-audit-code` restated what the two files already enforced, and in a harder form, so the duplicates read as new law and cancelled the originals: a search was forbidden for a job the same page tells the agent to search for, a guard against deleting entry points contradicted the ladder's first rung, and every bullet of the new section repeated a rung.
- **Root cause:** An appendix that restates its host's rules in stronger words becomes new law that contradicts the host.
- **Fix:** Keep the delta only — search to locate and references to prove, a guard conditioned on callers, a citation unit that widens when a line is not the right size, a severity scope that leaves the no-path grade intact.
- **Lesson:** An appendix to a document must cite the rule the host already carries, never restate it harder.
- **Tags:** review, docs, skills

### L30 · 2026-10-01 · git-worktree-flow #3 · review
- **Failure:** With the primary tree parked on another branch, `git merge --no-ff` succeeds on that branch, `main` never receives the feature, and the close's removal step erased the branch anyway — the only guards were prose sentences.
- **Root cause:** A step that destroys a branch trusted prose instead of asserting, with a command, that the destruction was safe.
- **Fix:** The close asserts `git merge-base --is-ancestor feat/<slug> main` exits 0 and that the primary tree still has `main` checked out before removing anything; if either fails it stops, reports and removes nothing, and the same rule went into the verb.
- **Lesson:** Any step that destroys a branch must first assert, with a command an agent can run, that the destruction is safe.
- **Tags:** review, git, safety, orchestration

<!--
### L<n> · YYYY-MM-DD · <feature-slug> #<checkpoint> · <gate: behavior|ui|review|human|circuit-breaker>
- **Failure:** what failed, as the gate reported it
- **Root cause:** why, not just what
- **Fix:** what changed
- **Lesson:** one reusable sentence for next time
- **Tags:** e.g. auth, db, migration, ui, tests, webhooks
-->
