# Learnings

Accumulated failures and lessons from building features, mostly written by `/ai-orchestrator`. Every planner, implementer, test writer and reviewer reads **Rules** before starting.

- **Log** is append-only: never edit or delete an entry.
- **Rules** is the distilled version. A lesson is promoted here once it has recurred (2 or more log entries) or caused a human-review rejection or a circuit-breaker stop. Each rule cites the entries it came from.

## Rules

- R1: Assert behaviour and exact contents, never a proxy such as source text or a bare type check. (from L2, L11)
- R2: Assert every field and linkage a consumer relies on, not only the one you happened to read. (from L13, L14)
- R3: Cover every acceptance branch, and test each guard in the exact configuration where it alone stands between the input and the harmful path. (from L7, L12)

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

<!--
### L<n> · YYYY-MM-DD · <feature-slug> #<checkpoint> · <gate: behavior|ui|review|human|circuit-breaker>
- **Failure:** what failed, as the gate reported it
- **Root cause:** why, not just what
- **Fix:** what changed
- **Lesson:** one reusable sentence for next time
- **Tags:** e.g. auth, db, migration, ui, tests, webhooks
-->
