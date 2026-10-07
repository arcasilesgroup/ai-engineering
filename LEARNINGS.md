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
- R9: Accept only bare allowlisted `gh`/`az` executable names; reject path prefixes, environment assignments and shell wrappers. A static Markdown allowlist is not a sandbox against an earlier malicious executable in `PATH`. (from L44)
- R10: Use the already-authenticated Azure CLI and its Azure DevOps extension for Azure DevOps access; never write tokens or credentials. (from L57)

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

### L31 · 2026-10-07 · ai-triage #1 · behavior
- **Failure:** The first GitHub regression test imported `skills/ai-triage/scripts/github.mjs`, which is not part of the approved Markdown skill design.
- **Root cause:** The test assumed the agent-executed procedure had an executable runtime helper, creating a scope mismatch.
- **Fix:** Converted the regression test to a static contract test; did not invent the missing runtime.
- **Lesson:** Test agent-executed Markdown procedures as static contracts; do not invent a runtime to satisfy an import.
- **Tags:** tests, skills, scope

### L32 · 2026-10-07 · ai-triage #1 · behavior
- **Failure:** `bun test tests/skills.spec.ts` detected the empty `skills/ai-github-triage/` directory left after the old skill file was renamed.
- **Root cause:** Renaming the old skill file left a stale directory entry on disk.
- **Fix:** Removed only the empty retired skill directory; the targeted test then passed (19 passed) with no tracked file changes.
- **Lesson:** Retirement checks include directory presence, not just `SKILL.md` files.
- **Tags:** tests, skills, filesystem

### L33 · 2026-10-07 · ai-triage #1 · behavior
- **Failure:** `bun run typecheck` exited 127 because `oxlint` was not found.
- **Root cause:** Dependencies had not been restored.
- **Fix:** Restored locked dependencies with `bun install --frozen-lockfile`; manifests and lockfile were unchanged. Confirmed `oxlint` 1.80.0 was available and `bun run typecheck` exited 0 with warnings.
- **Lesson:** Restore locked dependencies before the typecheck gate.
- **Tags:** typecheck, dependencies, bun

### L34 · 2026-10-07 · ai-triage #2 · review
- **Failure:** Round 1 findings F1–F3 identified contract-test gaps.
- **Root cause:** The tests did not link each requirement to its specific command.
- **Fix:** Link each contract-test requirement to its specific command.
- **Lesson:** Contract tests should link each requirement to its specific command.
- **Tags:** review, tests, contracts

### L35 · 2026-10-07 · ai-triage #2 · review
- **Failure:** Round 2 findings F1/F2 remained open after independent review.
- **Root cause:** Static contract checks did not link each requirement to the command it governs.
- **Fix:** Link each static contract requirement to the command it governs.
- **Lesson:** Static contract checks should link each requirement to the command it governs.
- **Tags:** review, tests, contracts

### L36 · 2026-10-07 · ai-triage #2 · review
- **Failure:** Round 3 identified mutation and pagination gaps.
- **Root cause:** Safety and completeness assertions were not scoped to the command they govern.
- **Fix:** Scope each safety and completeness assertion to its governing command.
- **Lesson:** Scope each safety and completeness assertion to the command it governs.
- **Tags:** review, tests, contracts

### L37 · 2026-10-07 · ai-triage #2 · review
- **Failure:** Retry round 1 found that the contract chased mutators rather than limiting permitted operations.
- **Root cause:** Mutator-by-mutator exclusions leave gaps when operations are missed.
- **Fix:** Allowlist permitted operations instead of chasing mutators.
- **Lesson:** Allowlist permitted operations instead of chasing mutators.
- **Tags:** review, command-safety, contracts

### L38 · 2026-10-07 · ai-triage #2 · review
- **Failure:** Retry round 2 found remote-capable commands and request-body options insufficiently constrained.
- **Root cause:** The contract did not reject all commands outside explicitly safe reads, independent of flag spacing.
- **Fix:** Restrict commands to explicitly safe reads and reject other remote-capable commands and request-body options regardless of flag spacing.
- **Lesson:** Allow only explicitly safe reads; reject other remote-capable commands and request-body options regardless of flag spacing.
- **Tags:** review, command-safety, contracts

### L39 · 2026-10-07 · ai-triage #2 · review
- **Failure:** Retry round 3 found shell syntax that could execute nested commands in the read-only command contract.
- **Root cause:** The contract did not reject shell syntax capable of nested command execution.
- **Fix:** Reject shell syntax that executes nested commands.
- **Lesson:** A read-only command contract must reject shell syntax that executes nested commands.
- **Tags:** review, command-safety, contracts

### L40 · 2026-10-07 · ai-triage #2 · review
- **Failure:** The retry review found that the shell boundary was not enforced before accepting commands.
- **Root cause:** Command acceptance preceded shell-boundary enforcement.
- **Fix:** Enforce the shell boundary before accepting commands.
- **Lesson:** Enforce the shell boundary before accepting commands.
- **Tags:** review, command-safety, shell

### L41 · 2026-10-07 · ai-triage #2 · review
- **Failure:** The retry review found that complete command examples were not extracted before read-only allowlist checks.
- **Root cause:** The allowlist was applied before complete command examples were extracted.
- **Fix:** Extract complete command examples before applying the read-only allowlist.
- **Lesson:** Extract complete command examples before applying the read-only allowlist.
- **Tags:** review, command-safety, contracts

### L42 · 2026-10-07 · ai-triage #2 · review
- **Failure:** The retry review found that fence labels and executable paths could bypass a closed read allowlist.
- **Root cause:** Fence labels and executable paths were not fully constrained by the closed read allowlist.
- **Fix:** Prevent fence labels and executable paths from bypassing the closed read allowlist.
- **Lesson:** Fence labels and executable paths must not bypass a closed read allowlist.
- **Tags:** review, command-safety, allowlist

### L43 · 2026-10-07 · ai-triage #2 · circuit-breaker
- **Failure:** After the automatic split, checkpoint 2 review reached three failed review attempts. F1–F10 were resolved, but F11/P1 remains because basename normalization allows path-qualified executables such as `./gh` or `~/bin/gh` to bypass the read allowlist.
- **Root cause:** Awaiting the user's decision.
- **Fix:** Awaiting the user's decision.
- **Attempts:** Explicit denylist; closed allowlist; shell operator, substitution and heredoc checks; all-fence parsing; basename normalization.
- **Lesson:** No Rule inferred; root cause and final fix await the user's decision.
- **Tags:** circuit-breaker, review, command-safety, allowlist

### L44 · 2026-10-07 · ai-triage #2 · circuit-breaker
- **Failure:** F11/P1 remained after three failed review attempts because basename normalization allowed path-qualified executables such as `./gh` or `~/bin/gh` to bypass the read allowlist.
- **Root cause:** Normalizing an executable to its basename erased whether the command used a path prefix.
- **Fix:** Require bare allowlisted `gh`/`az` executable names; reject executable path prefixes, environment assignments and shell wrappers. Accept that a static Markdown allowlist cannot sandbox a malicious earlier executable in `PATH`.
- **Lesson:** A static command allowlist must constrain command form and disclose that it cannot control executable resolution from `PATH`.
- **Tags:** circuit-breaker, review, command-safety, allowlist

### L45 · 2026-10-07 · ai-triage #2 · review
- **Failure:** F11 found that basename normalization let `./gh` or `~/bin/gh` evade command identity checks.
- **Root cause:** Markdown allowlists cannot attest the executable resolved from PATH.
- **Fix:** The human chose the trusted-PATH boundary: require bare allowlisted executable names and explicitly state that this is not a sandbox.
- **Lesson:** A command allowlist does not verify executable identity.
- **Tags:** review, command-safety, allowlist

### L46 · 2026-10-07 · ai-triage #3 · behavior
- **Failure:** TypeScript reported possibly-undefined indexed values and regex captures in `tests/triage-github.spec.ts`.
- **Root cause:** Indexed values and regex captures were used without narrowing their possible absence.
- **Fix:** Added explicit guards and safe narrowing without casts, preserving the assertions.
- **Lesson:** Narrow indexed values before use, and fail closed when a value is absent.
- **Tags:** typecheck, tests, narrowing

### L47 · 2026-10-07 · ai-triage #4 · behavior
- **Failure:** Typecheck couldn't resolve `resolveTarget`/`resolveTargetAndRead` because `.mjs` lacked named-export declarations.
- **Root cause:** A wildcard asset declaration masked the executable module's named exports.
- **Fix:** Added `resolve-target.d.mts`; tests now pass.
- **Lesson:** Give executable `.mjs` modules explicit declarations when a wildcard asset declaration masks their exports.
- **Tags:** typecheck, typescript, declarations

### L48 · 2026-10-07 · ai-triage #4 · review
- **Failure:** The CP4 review invocation could not resolve feature-worktree files and performed no code review; no source finding.
- **Root cause:** The reviewer used relative paths from the primary checkout instead of paths to the feature worktree.
- **Fix:** No source change; include absolute feature-worktree paths in the review prompt.
- **Lesson:** Review prompts for worktree files must include absolute worktree paths.
- **Tags:** review, worktree, orchestration

### L49 · 2026-10-07 · ai-triage #4 · behavior
- **Failure:** A generic path segment `t` was mistaken for the team marker, and Azure DevOps Services SSH remotes were missed.
- **Root cause:** Marker parsing was not anchored to the board route, and SSH parsing did not support strict `v3` remotes.
- **Fix:** Anchor parsing to the board route and support strict Azure DevOps Services SSH `v3` remotes.
- **Lesson:** Match route markers by position and test the resulting scope with synthetic inputs.
- **Tags:** url-routing, team-marker, azure-devops, ssh

### L50 · 2026-10-07 · ai-triage #5 · behavior
- **Failure:** The Azure unit test typecheck failed on indexed array values and fixture metadata.
- **Root cause:** Indexed arrays may yield `undefined`, and the fixture metadata union included a missing `stateCategory`.
- **Fix:** Added explicit guards and narrowing without casts; typecheck and targeted tests passed.
- **Lesson:** Narrow optional array values before passing them to typed assertions or functions.
- **Tags:** typecheck, tests, narrowing, azure

### L51 · 2026-10-07 · ai-triage #6 · behavior
- **Failure:** Typecheck reported TS2769 at `tests/triage-report.integration.spec.ts:160` because an optional array lookup yielded `string | undefined` for `writeFile`.
- **Root cause:** The recorded write was used without narrowing its possible absence.
- **Fix:** Narrowed the recorded write before calling `writeFile`, without an unsafe cast; typecheck and targeted integration test passed.
- **Lesson:** Narrow indexed values before using them in typed assertions.
- **Tags:** typecheck, tests, narrowing, integration

### L52 · 2026-10-07 · ai-triage #6 · review
- **Failure:** Percent-encoded credential-shaped values in Azure organization/project scope bypassed raw-only authentication redaction and appeared in rendered output.
- **Root cause:** Authentication redaction checked raw URL values but not their percent-decoded forms before rendering.
- **Fix:** Check raw and decoded URL values; omit links with unsafe scope values and render safe IDs/text instead.
- **Lesson:** Validate untrusted URL values before encoding or rendering them.
- **Tags:** review, auth, redaction, urls, azure

### L53 · 2026-10-07 · ai-triage #6 · review
- **Failure:** Rendered values could reach output without sanitization, and write/replace failure cases were not covered.
- **Root cause:** Output-boundary sanitization and stage-specific failure tests were incomplete.
- **Fix:** Sanitize values at each output boundary and test failures at write and replace stages.
- **Lesson:** Sanitize every rendered value at its output boundary; test failures at the write and replace stages.
- **Tags:** review, sanitization, output, tests

### L54 · 2026-10-07 · ai-triage #6 · review
- **Failure:** Escaped HTML did not prevent credentials in URLs from being rendered.
- **Root cause:** HTML escaping was treated as URL validation.
- **Fix:** Escape HTML and validate URL values independently.
- **Lesson:** Escape HTML and validate URLs independently; escaping does not remove credentials.
- **Tags:** review, html, urls, credentials

### L55 · 2026-10-07 · ai-triage #6 · review
- **Failure:** Decoded URL values were not validated, and inserted content could be processed again.
- **Root cause:** Validation and rendering did not account for decoded values and already-inserted content.
- **Fix:** Validate decoded URL values and do not reprocess inserted content.
- **Lesson:** Validate decoded URL values and never reprocess inserted content.
- **Tags:** review, urls, validation, rendering

### L56 · 2026-10-07 · ai-triage #6 · circuit-breaker
- **Failure:** After the split, review attempt 3 stopped on the round-4 open P1: synthetic `azure_devops_token=` and `bearer_token=` team metadata values still render.
- **Root cause:** Awaiting the user's decision.
- **Fix:** Awaiting the user's decision.
- **Attempts:** Review attempts 1–3; round 4 left the P1 open.
- **Lesson:** No Rule inferred; root cause and final fix await the user's decision.
- **Tags:** circuit-breaker, review, auth, redaction, metadata, azure

### L57 · 2026-10-07 · ai-triage #6 · human
- **Failure:** The checkpoint halted while deciding how Azure DevOps authentication should be handled.
- **Root cause:** “que usen el cli de az que debe estar auth y ahí existe la extensión de azure devops no? que no exista tokens ni credenciales escritos”
- **Fix:** Use the already-authenticated Azure CLI and its Azure DevOps extension; do not write tokens or credentials.
- **Lesson:** Use the existing Azure CLI authentication and Azure DevOps extension, never written tokens or credentials.
- **Tags:** human, circuit-breaker, auth, credentials, azure-devops

### L58 · 2026-10-07 · ai-triage #6 · review
- **Failure:** Synthetic `azure_devops_token=` and `bearer_token=` team metadata credentials still rendered.
- **Root cause:** The assignment redactor omitted Azure DevOps token and bearer-token key variants.
- **Fix:** Added both key variants to the redaction matcher and expanded full-report tests to verify secret removal while preserving safe lookalike fields.
- **Lesson:** Cover provider-specific credential assignment names in redaction tests, including safe fields with similar prefixes.
- **Tags:** review, auth, redaction, metadata, azure, bearer

### L59 · 2026-10-07 · ai-triage #6 · review
- **Failure:** Synthetic `azure_devops_pat=`, `github_token=`, and `system_access_token=` metadata values rendered in the full report.
- **Root cause:** The shared assignment redactor omitted these credential aliases.
- **Fix:** Added the three exact aliases at the shared redaction boundary and extended full-report regression coverage with benign owner-field near-matches.
- **Lesson:** Cover provider credential aliases at the shared output boundary while asserting that neighboring metadata remains visible.
- **Tags:** review, auth, redaction, metadata, tests

### L60 · 2026-10-07 · ai-triage #6 · review
- **Failure:** New provider-prefixed credential assignment aliases continued to leak after the finite alias list was extended.
- **Root cause:** Redaction depended on enumerating provider-specific assignment names instead of recognizing credential-bearing key families.
- **Fix:** Normalize assignment keys and redact credential suffix families while leaving owner/count and non-terminal near-matches unchanged.
- **Lesson:** Classify credential assignment keys by semantic suffix, not a growing provider alias list or arbitrary keyword containment.
- **Tags:** review, auth, redaction, metadata, tests

### L61 · 2026-10-07 · ai-triage #6 · review
- **Failure:** Synthetic `SYSTEM_ACCESSTOKEN=`, `private_key=`, `access_key=`, and `secret_access_key=` values remained in the full report.
- **Root cause:** Token matching required a separator before its suffix, and key assignment families were not recognized.
- **Fix:** Match normalized credential suffixes and common credential-key families at the shared report redaction boundary while preserving owner/count/policy fields.
- **Lesson:** Normalize credential assignment names before classifying semantic suffixes; avoid broad substring matching that hides benign metadata.
- **Tags:** review, auth, redaction, metadata, tests
