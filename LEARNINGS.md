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
- R9: Define remote commands with a closed allowlist; inspect complete command examples before acceptance, reject shell composition and unsafe forms, and accept only bare allowlisted executable names. A static Markdown allowlist cannot secure executable resolution from `PATH`. (from L37–L42, L44–L45)
- R10: Use the already-authenticated Azure CLI and its Azure DevOps extension for Azure DevOps access; never write tokens or credentials. (from L57)
- R11: Scope each contract assertion to the specific command it governs; a neighboring command or generic assertion cannot stand in for it. (from L34–L36)
- R12: Narrow optional and indexed values before typed use, and fail closed when a required value is absent. (from L46, L50–L51)
- R13: Validate untrusted output values at the output boundary; HTML-escape text, validate raw and decoded URL values separately, and do not reprocess inserted content. (from L52–L55)
- R14: Redact credential assignments at the shared output boundary by semantic key families, including nested assignments, while preserving safe near-matches. (from L58–L62)
- R15: Keep executable `.mjs` APIs explicitly declared, and embed script/declaration payloads as text when they are data rather than host modules. (from L47, L64)
- R16: Route repository-owned artifacts through their repository procedure and test the caller-to-procedure handoff; a same-named installed copy may have a conflicting contract. (from L66)
- R17: For runtime p95 checks under parallel test load, use enough samples for nearest-rank p95 to tolerate scheduler outliers without loosening the budget. (from L65, L67)
- R18: Normalize Markdown formatting without altering identifiers; preserve underscores, case, and other contract-significant characters before matching. (from L82, L89, L97)
- R19: Carry destructive-cleanup warnings and accurately describe the irreversible action and remaining state through every outcome and caller. (from L105, L107)
- R20: Gate 1 CLI acceptance must assert physical total and unknown classification together; physical presence is not lifecycle certainty. (from L126)

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

### L62 · 2026-10-07 · ai-triage #6 · review
- **Failure:** A nested credential assignment escaped the full report when enclosed by safe outer metadata.
- **Root cause:** The sanitizer consumed the quoted outer value before scanning nested assignments.
- **Fix:** Scan and redact embedded assignments while preserving safe surrounding text.
- **Lesson:** Scan nested credential assignments at the shared output boundary while retaining safe enclosing text.
- **Tags:** review, auth, redaction, metadata, tests

### L63 · 2026-10-07 · ai-triage #7 · review
- **Failure:** A substituted same-path temporary file could be deleted during cleanup or published instead of the report.
- **Root cause:** Cleanup and replacement trusted a pathname after closing the staged file, without binding that path to the opened file's identity.
- **Fix:** Stage in a private unique directory, retain the opened file through atomic rename, validate device/inode before replacement, and unlink only the matching staged file.
- **Lesson:** Bind filesystem cleanup and publication to the identity of the file opened, not just its temporary pathname.
- **Tags:** review, atomic-write, filesystem, ownership, tests

### L64 · 2026-10-07 · ai-triage #8 · behavior
- **Failure:** `bun run typecheck` reported TS1192/TS2846 because generated `src/assets.ts` imported `.d.mts` declaration files as runtime assets.
- **Root cause:** `.mjs` runtime imports resolved sibling `.d.mts` declarations as host modules.
- **Fix:** Embedded scripts and declaration files through `.txt` copies and tested the exact payloads.
- **Lesson:** Keep runtime script assets separate from host-module resolution.
- **Tags:** behavior, assets, typecheck

### L65 · 2026-10-07 · ai-triage #8 · behavior
- **Failure:** The chain full-suite p95 budget failed sporadically although the isolated test passed.
- **Root cause:** `tests/adversarial/chain.test.ts` used `floor(n*0.95)`, which selected the maximum of 20 observations.
- **Fix:** Use `ceil(0.95*n)-1` and pin the one-outlier regression while preserving the 50ms threshold.
- **Lesson:** The nearest-rank p95 index is `ceil(p*n)-1`.
- **Tags:** behavior, tests, performance

### L66 · 2026-10-07 · ai-triage · human
- **Failure:** The approved app review could not finish because a generic recap-skill invocation selected an installed procedure with a different publishing contract from the repository's HTML artifact.
- **Root cause:** The orchestrator named a skill without pinning the repository-owned procedure, and the installed copy disagreed with the local workflow.
- **Fix:** Bind the close procedure to the repository skill path, make that skill describe the local HTML artifact, synchronize the active installed copies, and test the handoff.
- **Lesson:** Route repository-owned artifacts through their repository procedure and test the caller-to-procedure handoff.
- **Gate that should have caught it:** `tests/skills.spec.ts` had no assertion for the app-review recap route.
- **Tags:** human, workflow, recap

### L67 · 2026-10-07 · ai-triage #8 · behavior
- **Failure:** The nearest-rank chain p95 test intermittently failed with 20 samples under the test runner.
- **Root cause:** At 20 samples, the 19th ordered value defines p95, so two scheduler stalls push the estimate over the budget.
- **Fix:** Measure 100 calls and retain the 50ms threshold plus a deterministic outlier check.
- **Lesson:** Use enough samples for nearest-rank p95 to tolerate expected scheduler outliers without changing the budget.
- **Tags:** behavior, tests, performance

### L68 · 2026-10-08 · ai-triage-azure-signals #1 · behavior
- **Failure:** A6 expected enriched UNASSESSED items in priority order rather than their original inventory order.
- **Root cause:** The compatibility test applied assessed-item sorting to UNASSESSED items, contrary to the unchanged renderer and approved preservation contract.
- **Fix:** Pin the fixture's inventory order and assert that every enriched UNASSESSED item renders once in that same order; leave the renderer unchanged.
- **Lesson:** Verify legacy behavior and assessment status before setting compatibility expectations; correct a faulty test instead of changing the product baseline to satisfy it.
- **Tags:** behavior, tests, azure, compatibility, unassessed

### L69 · 2026-10-08 · ai-triage-azure-signals #1 · review
- **Failure:** Valid comment continuations using Azure's canonical project GUID stopped pagination when the request used the project name.
- **Root cause:** Continuation validation compared literal paths rather than the already verified selected-project identity.
- **Fix:** Reuse the scoped project lookup or read it once; validate GUID aliases against that identity, organization and item, then reconstruct the original endpoint using only the opaque token.
- **Lesson:** Validate documented identifier aliases against established identity without trusting or executing server-supplied continuation URLs.
- **Tags:** review, azure, pagination, scope, validation, tests

### L70 · 2026-10-08 · ai-triage-azure-signals #1 · review
- **Failure:** Inaccessible or partial field metadata erased already-returned custom-date context and its revision-linked sources.
- **Root cause:** Context candidates came only from successful dateTime metadata, so an unavailable definition also removed the underlying returned evidence.
- **Fix:** Preserve custom fields without verified definitions as raw reference names, values and sources with unrecognized context and explicit metadata gaps; never infer their field types or delivery meaning.
- **Lesson:** Missing definitions limit interpretation, not retention of already-returned scoped evidence.
- **Tags:** review, azure, metadata, coverage, sources, tests

### L71 · 2026-10-08 · ai-triage-azure-signals #1 · review
- **Failure:** Missing, unset or malformed parent Priority/Severity was labeled complete and could make overall evidence sufficient.
- **Root cause:** Parent normalization validated the item container but blindly copied importance and never included its field coverage in sufficiency.
- **Fix:** Validate each importance field against integer/string metadata, expose per-field gaps and linked raw sources, publish only validated importance, and retain known parent dates while limiting coverage.
- **Lesson:** A successful optional item read does not prove every requested field is available and valid; track those field gaps independently.
- **Tags:** review, azure, parent, validation, coverage, sources, tests

### L72 · 2026-10-08 · ai-triage-azure-signals #2 · tests
- **Failure:** New unit fixtures used `item.azureSignals` while the shipped collector and integration fixtures used `item.signals`; a provenance case also nested its link under `codeEvidence.url` instead of the integration claim's `url`.
- **Root cause:** Parallel test contracts invented different names for the same evidence without checking the existing collector declaration and each other's claim shapes.
- **Fix:** Align only checkpoint-2 unit fixtures and assertions with `signals` and claim `url`; retain the missing recommendation APIs as intentional red tests.
- **Lesson:** Derive new fixtures from the authoritative shipped contract and align shared claim names before implementation; never add product aliases to satisfy test drift.
- **Tags:** tests, azure, contract, provenance

### L73 · 2026-10-08 · ai-triage-azure-signals #2 · behavior
- **Failure:** Independent reproduction confirmed 13 unit and 2 API failures after recommendation implementation.
- **Root cause:** The unit recommendation fixture combines Priority 3 with Medium severity, whose stronger native band is P2 in the unchanged baseline, but asserted P3; omitted delivery fields also made its asserted sufficient coverage false. Bun's asymmetric `toMatchObject` replaced A6's live `signals` object with its matcher before publication. A8 expected item #202 ahead of #204 although both have native P3 and #204 occurs first in inventory.
- **Fix:** Correct only the proven native-band, coverage and stable-order premises; run the asymmetric assertion on a clone and verify publication leaves inventory unchanged. Add exact critical/blocker/overdue/today/seven-day/eight-day ordering, native/stable ties, legacy-versus-enriched fallback, and sufficient-versus-limited coverage checks. Production ranking, source fixtures, cases and latency thresholds remain unchanged.
- **Lesson:** Prove a fixture's strongest native signal, coverage gaps and unchanged evidence before asserting advice; a matcher that mutates its input can invalidate the very publication path it is meant to test.
- **Tags:** behavior, tests, azure, fixtures, compatibility, coverage, ordering

### L74 · 2026-10-08 · ai-triage-azure-signals #2 · behavior
- **Failure:** The synthetic preview showed zero sufficient and three limited assessed items in both complete and limited states, instead of three sufficient and two sufficient respectively.
- **Root cause:** Complete read envelopes did not supply every field the normalizer requires: items #201 and #203 omitted both delivery dates, #202 omitted TargetDate, and parent #901 omitted Severity, creation/change timestamps and DueDate. Metadata and supplied values, not the read envelope alone, determine evidence coverage.
- **Fix:** Complete the synthetic date metadata and actual item/parent fields; put unrelated delivery dates outside the near window, retain #202's outstanding commitment tomorrow, and add revision/comment evidence labels backed by the supplied records. Leave production sufficiency, native urgency, incomplete reads, UNASSESSED retention, tests and prototype unchanged.
- **Lesson:** Run a preview fixture through the normal writer and inspect each normalized coverage gap before capture; complete synthetic evidence honestly rather than force sufficient labels or loosen coverage rules.
- **Tags:** behavior, azure, fixtures, preview, metadata, parent, coverage, sources

### L75 · 2026-10-08 · ai-triage-azure-signals #2 · validation
- **Failure:** A full-suite retry with project-local scratch created installation commits and deleted tracked governance artifacts from the working feature tree.
- **Root cause:** The existing integration harness assumes its temporary homes and repositories are outside the governed repository. Moving its temporary root inside the feature tree made `home()` reject those `AI_ENG_HOME` overrides and made `repoRoot()` discover the real worktree through fixture ancestry; installation and removal no longer stayed isolated.
- **Fix:** Recover the 84 missing tracked files from the test-created snapshot, prove all 19 feature/task changed files match that snapshot, restore the original feature tip and empty index, and remove owned scratch artifacts. Stop that retry configuration; unrelated harness and machine-side governance checks remain for the coordinator.
- **Lesson:** A project-local temporary root is not isolation for tests that discover repositories through ancestors or deliberately reject repository-contained home overrides. Validate those boundaries before running installation/removal integration tests.
- **Tags:** validation, tests, fixtures, isolation, governance, recovery

### L76 · 2026-10-08 · ai-triage-azure-signals #2 · review
- **Failure:** Edited older resolution/completion comments were ignored, and a later withdrawn child dependency still promoted its parent's commitment; actual reports ranked the child above native-priority-one work.
- **Root cause:** Opposing claims were filtered by creation time before considering modification time. Parent admission accepted any historical positive dependency sharing a parent field, without reconciling false/unknown updates or preserving its supporting comment sources. Same-date commitments also lacked issue-identity pairing.
- **Fix:** Reconcile source-backed claims with creation/modification intervals and issue identity. Unambiguous later withdrawals remove dependency admission; edited or unknown counterclaims retain both references and request clarification in native order. Separate-comment parent support needs matching delivery identities, and promoted commitments include their dependency evidence. Preserve conservative legacy handling without prose keywords or changing native urgency.
- **Lesson:** A current comment version does not timestamp its asserted event. Reconcile positive, negative and unknown evidence before declaring work current; shared fields establish context, not identity or current dependency.
- **Proof:** Eighteen added regressions cover chronology, identity, dependency withdrawal/uncertainty and actual writer ordering. Checkpoint non-UI gates: 138 unit, 150 API and 72 static pass; lint/typecheck exit 0. Normal full suite with unchanged OS scratch: 1249 pass, 0 fail, 5503 assertions. No performance budget changes.
- **Tags:** review, azure, chronology, claims, identity, dependency, provenance, ordering, tests

### L77 · 2026-10-08 · ai-triage-azure-signals #2 · review
- **Failure:** Historical dependency uncertainty overrode a later explicit confirmation only when an obsolete positive dependency preceded that uncertainty; the actual writer retained native order instead of promoting the currently supported commitment.
- **Root cause:** Unknown claims collected through superseded positive/unknown pairs bypassed the later-confirmation filter. That same mixed collection also described uncertainty as an explicit withdrawal.
- **Fix:** Reconcile unknown dependency claims against current confirmations through the shared creation/modification chronology. Keep overlapping edited uncertainty conservative, and derive withdrawal context only from explicit false claims. Add four-comment and three-comment controls to unit and actual-writer tests, including edited uncertainty in both configurations.
- **Lesson:** Historical evidence must not alter current status after an unambiguous confirmation. Reconcile every path that collects uncertainty through the same chronology, and distinguish unknown status from an explicit withdrawal.
- **Proof:** Before the fix, both historical-dependency regressions failed while their controls passed. All eight new regressions now pass with 86 assertions. Non-UI gates: 142 unit, 154 API and 72 static pass (2291 assertions); lint/typecheck exit 0 with existing warnings; all four canonical payload pairs match. Two unchanged normal full-suite runs each yielded 1256 pass, 1 fail and 5589 assertions: only the existing chain p95 latency test failed (128.30ms and 166.81ms against 50ms). That unchanged isolated test passes (1 pass, 2 assertions). No TMPDIR overrides or performance-budget changes.
- **Tags:** review, azure, chronology, dependency, uncertainty, claims, ordering, tests, validation

### L78 · 2026-10-08 · ai-triage-azure-signals #2 · review
- **Failure:** An unknown dependency edited before a renewed confirmation still forced native-order clarification when an obsolete positive report preceded it. Overlapping-edit advice also cited that obsolete positive.
- **Root cause:** Historical conflict pairs bypassed current-status reconciliation; collecting every dependency for clarification reintroduced superseded evidence into Why now.
- **Fix:** At the shared chronology boundary, retire matching historical reports when an unedited same-identity renewal starts after their last modification. Derive clarification references from unresolved evidence, retaining prior supporting reports only for still-unresolved unknown status. Preserve overlapping edits and conservative handling when identity is missing.
- **Lesson:** Reconcile the whole status timeline before classifying conflict pairs. A historical edit can make its contemporary evidence ambiguous without making a later explicit confirmation ambiguous; compare that confirmation with the earlier evidence's last modification.
- **Proof:** Twelve memory-only unit and actual-writer renewal cases cover unedited, edited-before and edited-after uncertainty, with and without obsolete positive history. Before the fix, four failed on advice/order or stale references. Renewal and F1/F2 controls now pass: 29 tests, 259 assertions. Checkpoint lower gates: 144 unit, 156 API and 72 static pass; lint/typecheck exit 0 with existing warnings; all four canonical signal/writer script/declaration payload pairs match. Normal full-suite validation remains separate.
- **Tags:** review, azure, chronology, dependency, uncertainty, renewal, identity, provenance, ordering, tests

### L79 · 2026-10-08 · worktree-lifecycle-governance #2 · behavior
- **Failure:** `bun run typecheck` rejected the lifecycle test's nested array loop values with TS2769, although its runtime assertions passed.
- **Root cause:** TypeScript inferred optional tuple elements that did not satisfy the `toContain` overloads.
- **Fix:** Represented each test case with named object fields while keeping both lifecycle and Git assertions.
- **Lesson:** Use named fields when loop entries have distinct roles.
- **Tags:** behavior, tests, types

### L80 · 2026-10-08 · worktree-lifecycle-governance #2 · review
- **Failure:** Adversarial review found that incomplete prior checkpoints could pass, the plan slug was not bound to the checkpoint marker, and a blocked lifecycle could retain stale app approval.
- **Root cause:** The guard trusted summary status and lifecycle phase without checking prerequisite gates, plan identity, and the freshness of approval state.
- **Fix:** Require completed predecessor gates, exact marker-to-plan slug matching, and reset stale review state before a blocked plan can resume.
- **Lesson:** Approval metadata is a claim; verify underlying gates, identity, and review freshness at each guard.
- **Tags:** review, checkpoint-gate, lifecycle

### L81 · 2026-10-08 · worktree-lifecycle-governance #2 · review
- **Failure:** An adversarial test showed that checkpoint ID `1e999` parsed as infinity and could bypass predecessor ordering.
- **Root cause:** The gate compared checkpoint IDs before validating that they were finite positive integers.
- **Fix:** Validate checkpoint ID type, finiteness and sequence before lookup or gate comparison.
- **Lesson:** Validate ordering keys before comparing them.
- **Tags:** review, checkpoint-gate, validation

### L82 · 2026-10-08 · worktree-lifecycle-governance #3 · behavior
- **Failure:** U13's handoff assertion failed even though the skill contained the required same-slug resume behavior.
- **Root cause:** The test expected a phrase to remain contiguous across Markdown formatting.
- **Fix:** Normalize whitespace before matching the handoff condition.
- **Lesson:** Match handoff conditions independently of Markdown line wrapping.
- **Tags:** behavior, tests, workflow

### L83 · 2026-10-08 · worktree-lifecycle-governance #3 · review
- **Failure:** Adversarial review found no test that prevented Phase 0 from mutating dirty/unknown work or proved pending human approvals were surfaced before proceeding.
- **Root cause:** Tests pinned successful resume and overlap branches but omitted two safety states and their ordering.
- **Fix:** Added focused handoff assertions for dirty/unknown refusal and visible plan/app-review approvals before continuation.
- **Lesson:** Test status guards and approval reporting in order, not only successful paths.
- **Tags:** review, tests, worktree

### L84 · 2026-10-08 · worktree-lifecycle-governance #3 · review
- **Failure:** Review found that a dirty or unknown same-slug worktree might still be resumed, and generic approval wording did not guarantee the pending decision was visible.
- **Root cause:** The preflight contract did not make refusal-before-mutation or named human approval states explicit.
- **Fix:** Added a no-mutation Phase 0 stop for dirty/unknown state and explicit plan, app-review and merge-ready handoffs with focused ordering assertions.
- **Lesson:** Check status and approval gates before any continuation.
- **Tags:** review, workflow, worktree

### L85 · 2026-10-08 · worktree-lifecycle-governance #4 · behavior
- **Failure:** U19 expected the checkpoint gate to distinguish human authorship for a transition that U10 submitted with the same state.
- **Root cause:** The test treated a local JSON state validator as proof of who supplied a human approval.
- **Fix:** Assert pending-state and phase prerequisites in the gate, and keep the actual human approval ordered through the Phase 1 orchestrator handoff.
- **Lesson:** Test human approval as an ordered handoff; don't claim a local state file authenticates who approved.
- **Tags:** behavior, tests, approvals

### L86 · 2026-10-08 · worktree-lifecycle-governance #4 · review
- **Failure:** Adversarial review found a legacy checkpoint in the primary checkout could gain lifecycle state there.
- **Root cause:** The gate validated lifecycle content without binding first initialization to the matching Git-listed feature worktree.
- **Fix:** Require lifecycle initialization at the canonical checkpoint path in the matching `feat/<slug>` worktree while preserving legacy primary-checkout gate behavior.
- **Lesson:** Validate lifecycle initialization at the worktree boundary, not just by slug.
- **Tags:** review, checkpoint-gate, worktree

### L87 · 2026-10-08 · worktree-lifecycle-governance #4 · review
- **Failure:** Adversarial review found a symlink alias could resolve to the canonical lifecycle checkpoint path and pass initialization.
- **Root cause:** Resolving source and target paths erased the distinction between the intended path and a symlink alias.
- **Fix:** Require normalized target identity and reject symlinks in the target path or any component.
- **Lesson:** Verify path identity and each component, not only where a path resolves.
- **Tags:** review, checkpoint-gate, symlink

### L88 · 2026-10-08 · worktree-lifecycle-governance #4 · review
- **Failure:** Review found the path-boundary test symlinked the canonical target rather than passing a distinct alias path that resolves to it.
- **Root cause:** The fixture did not exercise the caller-supplied alias spelling checked by the hook.
- **Fix:** Add a separate symlink alias path and assert that initialization through it is rejected while canonical initialization succeeds.
- **Lesson:** Test path security with the alternate input path, not a symlinked target alone.
- **Tags:** review, checkpoint-gate, symlink, tests

### L89 · 2026-10-08 · worktree-lifecycle-governance #5 · behavior
- **Failure:** U23 could not find the exact `reviewed_main` handoff after the local-main read step.
- **Root cause:** Test whitespace normalization removed underscores from lifecycle field identifiers.
- **Fix:** Preserve identifier spelling in the test and state that the full local-main commit ID is recorded only after gates pass and before app review.
- **Lesson:** Normalize Markdown formatting without altering identifiers.
- **Tags:** behavior, tests, reviewed-main

### L90 · 2026-10-08 · worktree-lifecycle-governance #5 · behavior
- **Failure:** `bun run typecheck` rejected four rebase fixture assertions in `tests/worktree-lifecycle.spec.ts`.
- **Root cause:** The local lifecycle test type omitted fields that the fixture asserted with `toEqual`.
- **Fix:** Add the named fields to the test-case type while preserving the rebase, conflict and abort assertions.
- **Lesson:** Keep test-case types aligned with their distinct named fields.
- **Tags:** behavior, tests, types

### L91 · 2026-10-08 · worktree-lifecycle-governance #5 · review
- **Failure:** Review found an unresolved rebase could mutate checkpoint state before restoration, a fixture used `git reset --hard`, and gate ordering omitted conditional UI.
- **Root cause:** Failure handling and test cleanup did not prove the original state was restored before continuing.
- **Fix:** Abort and verify refs/tree/status/content before marking blocked, use `git rebase --abort` in the fixture, and test behavior/UI-if-applicable/review ordering.
- **Lesson:** Preserve state first; record failure only after restoration is proven.
- **Tags:** review, rebase, safety

### L92 · 2026-10-08 · worktree-lifecycle-governance #5 · review
- **Failure:** Review found dirty or unknown pre-rebase work could be marked blocked before restoration and the checkpoint could be mutated.
- **Root cause:** The workflow wrote lifecycle state while existing user work was still untrusted.
- **Fix:** Stop without writes on unsafe preconditions; after a started rebase, abort and verify restoration before recording blocked.
- **Lesson:** Preserve state first; record failure only after restoration is proven.
- **Tags:** review, rebase, checkpoint-state

### L93 · 2026-10-08 · worktree-lifecycle-governance #5 · review
- **Failure:** U22 proved no mutation for dirty work but omitted missing and malformed lifecycle checkpoint states at the sync boundary.
- **Root cause:** The test covered one refusal precondition instead of asserting the full state for every refusal.
- **Fix:** Add Git fixtures showing missing state remains absent and malformed state bytes, refs and worktree status remain unchanged.
- **Lesson:** Pin each refused precondition's full state, not just the dirty case.
- **Tags:** review, tests, unknown-state

### L94 · 2026-10-08 · worktree-lifecycle-governance #5 · behavior
- **Failure:** `bun run typecheck` rejected the lifecycle gate's indexed `checkpoint.gates` access with TS18046.
- **Root cause:** Validation of the parsed checkpoint object was not preserved through a callback's indexed access.
- **Fix:** Capture the validated gates object before indexing, without weakening the fail-closed checks.
- **Lesson:** Narrow indexed values before typed use.
- **Tags:** behavior, types, checkpoint-gate

### L95 · 2026-10-08 · worktree-lifecycle-governance #5 · behavior
- **Failure:** U20d expected the rebased feature's first parent to equal `mainBefore`, but the fixture also included a feature commit.
- **Root cause:** The test asserted direct-parent equality instead of the premise it needed, ancestry from the selected base.
- **Fix:** Assert `mainBefore` is an ancestor and `mainAfter` is not, while retaining the race SHA and preservation checks.
- **Lesson:** Assert the intended Git ancestry, not a stronger fixture-dependent relationship.
- **Tags:** behavior, tests, git-fixture

### L96 · 2026-10-08 · worktree-lifecycle-governance #5 · review
- **Failure:** Review found a local-main advance during rebase could leave the feature rewritten on an older tip without identifying the effective base or retry.
- **Root cause:** The rebase command did not compare and report the full main refs around its operation.
- **Fix:** Capture full pre/post main SHAs, verify post-main ancestry, and report both refs plus safe retry guidance without resetting feature state.
- **Lesson:** Race errors should identify the observed refs and safe recovery.
- **Tags:** review, rebase, concurrency

### L97 · 2026-10-08 · worktree-lifecycle-governance #6 · behavior
- **Failure:** U24-U27 failed because the skill-test normalizer removed underscores from `reviewed_main`.
- **Root cause:** Formatting normalization altered a lifecycle identifier before matching.
- **Fix:** Narrow normalization so identifier spelling remains exact.
- **Lesson:** Normalize Markdown formatting without altering identifiers.
- **Tags:** behavior, tests, lifecycle

### L98 · 2026-10-08 · worktree-lifecycle-governance #6 · behavior
- **Failure:** Merge transaction tests counted fixture hook files as product mutations, queried a canonical path after removal, and assumed the primary checkout would be empty despite a deliberate hook edit.
- **Root cause:** The assertions ignored fixture setup and the safe preservation/retry path after refresh refuses to overwrite user changes.
- **Fix:** Snapshot after hook setup, capture paths before deletion, and test that the primary edit is preserved until retry refreshes the published merge.
- **Lesson:** Baseline fixtures after setup; capture paths before removal; assert preservation and retry separately.
- **Tags:** behavior, tests, merge

### L99 · 2026-10-08 · worktree-lifecycle-governance #6 · behavior
- **Failure:** The full suite's orchestrator-close contract test still expected manual ancestry verification and `worktree rm` after replacing the merge sequence with the atomic `worktree merge` command.
- **Root cause:** The skill handoff test was not updated with the new command boundary.
- **Fix:** Assert the approval-to-`worktree merge` handoff and verify the CLI transaction's ancestry/removal behavior in its real-Git tests.
- **Lesson:** When a workflow moves into a command, update the caller handoff test and keep behavioral assertions at the command boundary.
- **Tags:** behavior, tests, lifecycle

### L100 · 2026-10-09 · worktree-lifecycle-governance #6 · behavior
- **Failure:** The updated close contract test showed the orchestrator still did not capture `reviewed_feature` or invoke the atomic `ai-eng worktree merge <slug>` command.
- **Root cause:** The merge command implementation landed without replacing the skill's previous manual merge/cleanup handoff.
- **Fix:** Bind human app-review approval to both reviewed refs and route the close through the single Git-native CAS command.
- **Lesson:** When a transaction becomes a command, update its caller handoff before documenting or reviewing the lifecycle.
- **Tags:** behavior, skills, merge

### L101 · 2026-10-09 · worktree-lifecycle-governance #6 · behavior
- **Failure:** The blueprint contract test found the rewritten worktree flow no longer stated that visual recap is optional for merge and cleanup.
- **Root cause:** The new CAS procedure replaced the existing close paragraph without carrying forward the unrelated recap boundary.
- **Fix:** Preserve the recap-optional statement beside the new atomic merge and removal contract.
- **Lesson:** When replacing a workflow paragraph, retain adjacent invariants that remain in scope.
- **Tags:** behavior, docs, recap

### L102 · 2026-10-09 · worktree-lifecycle-governance #6 · behavior
- **Failure:** The orchestrator contract test expected the old manual merge/removal wording after close moved into the CAS command.
- **Root cause:** A phase-order assertion matched retired command prose rather than the new sync, review and command handoff.
- **Fix:** Assert Phase 3 sync before app review, then reviewed SHA capture, human approval and the CAS command after approval.
- **Lesson:** Assert ordered behavior, not the mere presence of command strings.
- **Tags:** behavior, tests, workflow

### L103 · 2026-10-09 · worktree-lifecycle-governance #6 · behavior
- **Failure:** U28a could not find the `app_review` lifecycle field after a handoff-test normalizer removed underscores.
- **Root cause:** Formatting normalization changed a contract-significant identifier before matching.
- **Fix:** Preserve underscores in identifiers while normalizing Markdown whitespace.
- **Lesson:** Normalize Markdown formatting without altering identifiers.
- **Tags:** behavior, tests, lifecycle

### L104 · 2026-10-09 · worktree-lifecycle-governance #6 · behavior
- **Failure:** U30's two real-Git retry scenarios exceeded Bun's default five-second per-test timeout under suite load.
- **Root cause:** The integration test combined two full worktree merge/refresh/removal cycles with insufficient timeout headroom.
- **Fix:** Raise only U30's test-local timeout while preserving its assertions and global budget.
- **Lesson:** Give an expensive integration case measured headroom without relaxing unrelated test budgets.
- **Tags:** behavior, tests, timeout

### L105 · 2026-10-09 · worktree-lifecycle-governance #6 · review
- **Failure:** Approval-bound checkpoint-only commits could alter reviewed plan scope, and close hid ignored-file removal warnings.
- **Root cause:** Approval validation compared lifecycle metadata but not the immutable plan payload, while the close command dropped cleanup output.
- **Fix:** Compare the reviewed payload while excluding runtime gate metadata, and forward the removal result to the caller.
- **Lesson:** Bind approval to the unchanged plan and preserve destructive-cleanup warnings through every caller.
- **Tags:** review, checkpoint-gate, cleanup

### L106 · 2026-10-09 · worktree-lifecycle-governance #6 · behavior
- **Failure:** Attempt 29 failed U31 because the real CLI merge returned 1.
- **Root cause:** The U31 test fixture captured `reviewed_feature` at a commit that did not contain the checkpoint plan, so the real merge guard correctly refused.
- **Fix:** Commit the implementation-phase checkpoint in the fixture before recording `reviewed_feature`.
- **Lesson:** A test fixture must satisfy the real contract it exercises.
- **Tags:** behavior, tests, lifecycle, merge

### L107 · 2026-10-09 · worktree-lifecycle-governance #6 · review
- **Failure:** Ignored-content scan warnings disappeared on cleanup errors after removal or failed post-removal verification.
- **Root cause:** Warnings were formatted only on normal success, and the merge wrapper discarded removal output on error while claiming the feature worktree was preserved.
- **Fix:** Preserve warnings through every cleanup return and report whether removal occurred, failed uncertainly, or left the branch behind.
- **Lesson:** Carry destructive-cleanup warnings and the actual remaining state through every success and failure path.
- **Tags:** review, cleanup, worktree, merge

### L108 · 2026-10-09 · worktree-lifecycle-governance #8 · behavior
- **Failure:** Checkpoint 8 behavior attempt 1 failed because workspace CLI tests could not receive responses from their in-process health mock.
- **Root cause:** `runWorkspace()` used a synchronous subprocess, blocking the same event loop that served the mock HTTP requests.
- **Fix:** Run the real CLI subprocess asynchronously with `Bun.spawn` and await its output and exit status.
- **Lesson:** Keep an in-process HTTP mock responsive by running the client subprocess asynchronously.
- **Tags:** behavior, tests, subprocess, workspace

### L109 · 2026-10-09 · worktree-lifecycle-governance #8 · behavior
- **Failure:** Checkpoint 8 behavior attempt 2 failed because the traversal-path assertion accepted the workspace root.
- **Root cause:** `join()` normalized `missing/..` before validation, so the test submitted the valid canonical project path instead of traversal input.
- **Fix:** Construct the fixture by joining path components with the platform separator, preserving the literal `..` segment.
- **Lesson:** Preserve literal traversal segments in test inputs instead of passing them through a normalizing path join.
- **Tags:** behavior, tests, paths, workspace

### L110 · 2026-10-09 · worktree-lifecycle-governance #8 · behavior
- **Failure:** Checkpoint 8 behavior attempt 3 failed typecheck because Bun's server port is optional and its server type did not satisfy the test's stricter cleanup type.
- **Root cause:** The returned port and Bun server cleanup object were used under narrower assumptions than their types guarantee.
- **Fix:** Capture and narrow the port before constructing or registering the workspace server, stop the server if no port is reported, and type test cleanup by its required `stop` method.
- **Lesson:** R12 applies: narrow optional Bun values before typed use, and fail closed when a required value is absent.
- **Tags:** behavior, typecheck, narrowing, workspace

### L111 · 2026-10-09 · worktree-lifecycle-governance #8 · behavior
- **Failure:** Checkpoint 8 behavior attempt 4 failed architecture tests because the new workspace source directory was not assigned to an architecture layer.
- **Root cause:** The code introduced a cohesive `src/workspace/**` layer without registering it in the architecture rules.
- **Fix:** Added the workspace source mapping to `.ai-engineering/arch.rules.json`; no forbidden dependency edge was found.
- **Lesson:** Register every new cohesive source layer in `.ai-engineering/arch.rules.json` in the same feature change.
- **Tags:** behavior, architecture, workspace

### L112 · 2026-10-09 · worktree-lifecycle-governance #8 · review
- **Failure:** The checkpoint 8 review found generic health responses could reuse unrelated services, stale roots blocked replacement, and interrupted writes could truncate settings.
- **Root cause:** Health identity was generic, writing validated old filesystem paths, and settings bytes were overwritten directly.
- **Fix:** Require the workspace service identity, validate old settings structure without old paths, and atomically rename a same-directory temporary file.
- **Lesson:** Identify reusable services specifically, make recovery validate the replacement state, and preserve persisted bytes until an atomic write succeeds.
- **Tags:** review, health, settings, atomic-write, tests

### L113 · 2026-10-09 · worktree-lifecycle-governance #8 · behavior
- **Failure:** Checkpoint 8 behavior attempt 6 failed typecheck because the healthy workspace response mock included `service`, which its callback parameter type rejected.
- **Root cause:** The default generic listener fixture inferred a shape that did not include the workspace health identity.
- **Fix:** Typed the callback body as a union of the workspace health response and the unrelated generic listener response.
- **Lesson:** Type mock response variants against each distinct contract instead of letting the default fixture narrow the accepted shape.
- **Tags:** behavior, typecheck, tests, workspace

### L114 · 2026-10-09 · worktree-lifecycle-governance #9 · review
- **Failure:** CP9 review found discovery paths could be swapped after canonicalization, stale or incomplete app-review evidence remained active, detached worktrees and misplaced checkpoints could be overridden by Closed history, and refresh omitted project errors.
- **Root cause:** Path reads trusted a prior realpath check, review state checked ancestry without the reviewed commit chain and payload, and history/API checks dropped path identity and per-project error details.
- **Fix:** Revalidate directory identity around path reads; require both review SHAs and the checkpoint-only reviewed chain; block Closed on registered slug/path evidence; accept only one canonical checkpoint path; include project errors in refresh responses.
- **Lesson:** Revalidate path identity without claiming race elimination; when review ancestry, payload, registration, or canonical placement is uncertain, report Unknown and preserve the error.
- **Tags:** review, workspace, lifecycle, filesystem, checkpoints, errors

### L115 · 2026-10-09 · worktree-lifecycle-governance #9 · review
- **Failure:** Closed history accepted a local-main checkpoint whose plan changed after the recorded review.
- **Root cause:** The history guard checked reviewed-SHA ancestry but never loaded the plan at `reviewed_feature`.
- **Fix:** Compare selected immutable plan fields from the local reviewed commit and current local-main checkpoint; missing, malformed, or changed reviewed payload remains Unknown.
- **Lesson:** Bind closure to the exact reviewed plan while excluding lifecycle, gate, and other runtime metadata.
- **Tags:** review, checkpoint-gate, workspace, lifecycle

### L116 · 2026-10-09 · worktree-lifecycle-governance #9 · behavior
- **Failure:** Checkpoint 9 behavior attempt 3 failed because closed history's `reviewed_feature` commit had no matching checkpoint plan payload.
- **Root cause:** The temporary Git fixture captured the feature commit before creating and committing the closed checkpoint plan.
- **Fix:** Commit the matching implementation-phase checkpoint before recording the feature SHA, then preserve the complete phase and passed gates on local main.
- **Lesson:** R5 applies: a reviewed-commit fixture must contain the checkpoint payload its validator requires.
- **Tags:** behavior, tests, git-fixture, checkpoint-gate, workspace

### L117 · 2026-10-09 · worktree-lifecycle-governance #9 · review
- **Failure:** Closed history accepted a local-main plan whose durable notes changed after review.
- **Root cause:** The immutable plan comparison included assumptions but omitted top-level `notes`.
- **Fix:** Compare top-level notes and verify changed local-main notes remain Unknown; lifecycle and gate/runtime fields stay excluded.
- **Lesson:** Bind closure to every plan-defining field, not just scope and task arrays; keep runtime state outside the immutable fingerprint.
- **Tags:** review, checkpoint-gate, workspace, lifecycle

### L118 · 2026-10-09 · worktree-lifecycle-governance #10 · behavior
- **Failure:** CP10 behavior attempt 2 showed ungoverned Git repositories in the workspace project list.
- **Root cause:** Discovery accepted every repository beneath configured search roots without applying the shared ai-eng governance predicate.
- **Fix:** Filter discovered repositories through `isGoverned(root)` and add governed, missing-config, corrupt-config, and declaration-less fixtures.
- **Lesson:** Configured roots scope discovery, but the shared governance gate decides which repositories the hub may present.
- **Tags:** behavior, tests, workspace, governance

### L119 · 2026-10-09 · worktree-lifecycle-governance #10 · behavior
- **Failure:** CP10 behavior attempt 3 classified a valid implementation checkpoint with status `in_progress` as Unknown.
- **Root cause:** The workspace checkpoint reader's status allowlist omitted a value emitted by the orchestrator.
- **Fix:** Accept `in_progress` and add it to the lifecycle classification fixture.
- **Lesson:** Keep checkpoint readers aligned with the writer's persisted enum and exercise every writer-produced state.
- **Tags:** behavior, tests, workspace, lifecycle

### L120 · 2026-10-09 · worktree-lifecycle-governance #10 · ui
- **Failure:** CP10 UI attempt 1 found inaccessible mobile explorer navigation, an unsupported resize-capture step, obscuring feedback, misleading filtered-empty text, lost focus, and missing ARIA state.
- **Root cause:** The live shell and capture scenarios did not fully preserve the prototype's navigation, feedback, and keyboard interaction contracts.
- **Fix:** Restore mobile return navigation and focus, add keyboard resize capture, keep feedback in flow, distinguish filtered emptiness, and add tab/validation semantics.
- **Lesson:** Exercise responsive UI transitions through supported capture actions and preserve focus and accessible state whenever content rerenders.
- **Tags:** ui, accessibility, workspace, tests

### L121 · 2026-10-09 · worktree-lifecycle-governance #10 · ui
- **Failure:** CP10 UI attempt 2 found the approved Settings prototype lacked the live Choose folder control and its third form column.
- **Root cause:** The live native-picker interaction was added without updating the feature prototype's Settings form.
- **Fix:** Add the Choose folder control, matching three-column layout, simulated selection state, and narrow-screen stacking to the prototype and capture map.
- **Lesson:** When a live form gains a control, update its approved prototype and state scenario in the same checkpoint; mark platform-only effects proto-only.
- **Tags:** ui, prototype, workspace, tests

### L122 · 2026-10-08 · worktree-lifecycle-awareness #1 · behavior
- **Failure:** The full-suite wall-clock p95 check (<50ms) intermittently measured 1,672.47ms and 161.718ms under load; the focused test was intermittent too (`tests/adversarial/chain.test.ts:247`).
- **Root cause:** Verification traced the timing to scheduler sensitivity under concurrent test load, not checkpoint code.
- **Fix:** No code change; subsequent isolated and full-suite runs passed.
- **Lesson:** Capture and isolate a timing failure before attributing it to a feature.
- **Tags:** behavior, tests, performance

### L123 · 2026-10-08 · worktree-lifecycle-awareness #1 · review
- **Failure:** Lifecycle state could be acted on for an unverified, out-of-root, or missing/prunable worktree, or from a stale concurrent update.
- **Root cause:** Evidence was not consistently tied to the exact managed worktree, configured root, live registration, and serialized lifecycle record.
- **Fix:** Verify exact slug/root/live worktree evidence, serialize writes, and treat missing, malformed, or stale evidence as unknown (`src/shared-worktree.ts`, `skills/ai-orchestrator/SKILL.md`, `tests/worktree-command.spec.ts`).
- **Lesson:** Lifecycle evidence must be exact, rooted, live, and serialized.
- **Tags:** worktree, lifecycle, review

### L124 · 2026-10-08 · worktree-lifecycle-awareness #1 · review
- **Failure:** A stale review approval could reopen implementation, while text-only checks could miss lifecycle command behavior.
- **Root cause:** Revision approval was not proved against the exact current review record through the command path.
- **Fix:** Bind approval to the current review record and cover current and stale revisions through the CLI (`src/shared-worktree.ts`, `skills/ai-orchestrator/SKILL.md`, `tests/worktree-command.spec.ts`).
- **Lesson:** Bind revisions to the exact reviewed record and test lifecycle behavior through the command.
- **Tags:** worktree, lifecycle, review

### L125 · 2026-10-08 · worktree-lifecycle-awareness #1 · review
- **Failure:** Concurrent callers could race while reclaiming a dead lifecycle lock.
- **Root cause:** Checking that the recorded owner was dead did not serialize stale-lock removal.
- **Fix:** Guard reclamation with its own recovery lock, reread and recheck the owner before unlinking, and exercise concurrent recovery (`src/shared-worktree.ts`, `tests/worktree-command.spec.ts`).
- **Lesson:** Stale-lock reclamation needs its own serialization, not just a liveness check.
- **Tags:** worktree, lifecycle, review

### L126 · 2026-10-08 · worktree-lifecycle-awareness #3 · human
- **Failure:** Existing AI Engineering and NN Skills worktrees across two local repositories appeared as `0 active · N unknown` despite live directories and branches.
- **Root cause:** Legacy worktrees without sibling `.ai-eng-lifecycle` records are intentionally unknown, while the statusline omitted the physical total; new `worktreeNew` also did not seed an initial approval-before-start record.
- **Fix:** Add a Gate 1 CLI acceptance requirement that reports physical total alongside unknown classification; no source change in this learning-only update.
- **Lesson:** Verify the user's real local inventory and distinguish physical totals from lifecycle certainty; missing records must remain unknown, never inferred active.
- **Gate that should have caught it:** Gate 1 CLI acceptance must assert physical total and unknown classification together.
- **Tags:** human, worktree, statusline, lifecycle

### L127 · 2026-10-08 · worktree-lifecycle-awareness #3 · behavior
- **Failure:** A prunable-worktree test expected no lifecycle record after a rejected active/review transition, but new worktrees now start with `approval-before-start`.
- **Root cause:** The test expected record absence instead of verifying that rejected transitions preserve the initial lifecycle state.
- **Fix:** Assert the original approval-before-start record remains unchanged while prunable and after pruning (`tests/worktree-command.spec.ts`).
- **Lesson:** Rejected promotion preserves creation evidence; assert the lifecycle state, not record absence.
- **Tags:** behavior, worktree, lifecycle, tests

### L128 · 2026-10-08 · worktree-lifecycle-awareness #3 · behavior
- **Failure:** The AI Engineering full suite before rebase reported 1012 pass, 3 fail, and 1 error, including missing `AGENTS.md` and architecture rules plus a p95 measurement of 166.36ms.
- **Root cause:** The feature branch's pre-existing governance 2.6.0 commit removed `AGENTS.md` and `.ai-engineering/arch.rules.json` while existing tests still require them; the p95 check is scheduler-sensitive.
- **Fix:** Rebase onto local main to separate branch drift from checkpoint regressions, then rerun the full suite without changing unrelated tests or thresholds.
- **Lesson:** Inspect branch file-removal history before attributing missing test prerequisites to merge-base drift.
- **Tags:** behavior, tests, baseline, branch

### L129 · 2026-10-08 · worktree-lifecycle-awareness #3 · behavior
- **Failure:** The post-rebase full suite reported 1252 pass, 3 fail, and 1 error; architecture checks still lacked their config and p95 measured 71.19ms against 50ms.
- **Root cause:** The same pre-existing governance commit still deletes the files required by the unrelated recap and architecture checks, while the full-suite p95 probe remains load-sensitive.
- **Fix:** Keep the checkpoint code unchanged; its focused lifecycle suite passes 47 tests and typecheck, lint, and build pass. Record the unrelated full-suite failures without restoring unrelated artifacts or loosening the timing budget.
- **Lesson:** Do not alter feature code or performance thresholds to mask pre-existing test-contract and repository-configuration failures.
- **Tags:** behavior, tests, baseline, performance

### L130 · 2026-10-09 · worktree-lifecycle-awareness #4 · behavior
- **Failure:** The AI Engineering full suite reported 1253 pass, 2 fail, and 1 error while the focused lifecycle suite passed 47 tests.
- **Root cause:** The existing governance 2.6.0 commit `9c37661d` deleted `AGENTS.md` and `.ai-engineering/arch.rules.json`; the unchanged recap and architecture checks still expect those files. Checkpoint 4 changes did not cause the failures.
- **Fix:** No in-scope change; preserve the existing tests and repository configuration state, and keep the failure separate from the passing lifecycle acceptance.
- **Lesson:** Keep branch-configuration failures distinct from lifecycle regressions.
- **Tags:** behavior, tests, baseline, lifecycle

### L131 · 2026-10-09 · worktree-lifecycle-awareness #4 · review
- **Failure:** `ai-eng worktree list` and successful removal could print terminal controls from local filesystem paths.
- **Root cause:** Both output paths interpolated Git-reported paths without using the shared printable sanitizer.
- **Fix:** Sanitize worktree-list paths and ignored filenames at the terminal output boundary; add regression tests for both commands.
- **Lesson:** Sanitize every untrusted local filesystem name at the output boundary.
- **Tags:** review, security, terminal, filesystem

### L132 · 2026-10-09 · worktree-lifecycle-awareness #4 · review
- **Failure:** Creating a worktree named `constructor` made a later ordinary worktree creation fail.
- **Root cause:** A declaration lookup read an inherited `Object.prototype.constructor` function as though it were an own list of files.
- **Fix:** Check that the declaration key is an own property before using its value; add a follow-up-creation regression.
- **Lesson:** Check own-property membership before indexing ordinary objects with user-controlled keys.
- **Tags:** review, security, prototype, worktree

### L133 · 2026-10-27 · floating-core #1 · review
- **Failure:** The daily receipts retention capped deletions but summarised and stat-ed every receipt, moving F7's cost into the PreToolUse hook.
- **Root cause:** The pass read the whole 40-day window before choosing what to delete.
- **Fix:** Pick stale receipts by filename timestamp; stat and tally only the batch being deleted.
- **Lesson:** A bounded pass must be bounded in reads as well as deletions; test it with a spy on file opens.
- **Tags:** review, receipts, performance

### L134 · 2026-10-27 · floating-core #1 · review
- **Failure:** At 500 deletions per day the receipts store still grew when the chain wrote more than 500 a day.
- **Root cause:** The day was stamped done even when a full batch left stale receipts behind.
- **Fix:** Release the day's claim while stale receipts remain, so later calls drain the backlog.
- **Lesson:** Test retention with a write rate above the batch size.
- **Tags:** review, receipts

### L135 · 2026-10-27 · floating-core #1 · review
- **Failure:** Four more suites deleted sandbox env vars instead of restoring them; the hygiene check covered one suite.
- **Root cause:** Each suite hand-rolled its sandbox and the checked list was written by hand.
- **Fix:** One shared snapshot/restore helper; the hygiene check discovers every suite that sets the vars.
- **Lesson:** Build the list of suites to check from the test tree, not by hand.
- **Tags:** review, tests, isolation

### L136 · 2026-10-27 · floating-core #1 · review
- **Failure:** Two chain calls could both run the day's retention pass, and summary.json could be torn.
- **Root cause:** The daily stamp was read then written; summary.json was written in place.
- **Fix:** Claim the day with an exclusive `wx` create; write summary.json via temp file and rename.
- **Lesson:** Claim shared work with one atomic create, not a read followed by a write.
- **Tags:** review, receipts, concurrency

### L137 · 2026-10-27 · floating-core #1 · behavior
- **Failure:** tests/uninstall-command.spec.ts:214 failed intermittently: "Nothing removed", all lock-listed files stayed.
- **Root cause:** Prompt tests typed answers on the runner's real stdin, so any stray byte answered the scope picker first.
- **Fix:** A private stdin fixture for the three suites that type keys, plus a test that injects a stray newline.
- **Lesson:** A test that types into prompts must give them input only the test writes to, never stdin it shares with the runner.
- **Tags:** behavior, tests, flake, stdin

### L138 · 2026-10-27 · floating-core #2 · review
- **Failure:** The ceremony contract test missed the nested viewer template, so removing it would stay green.
- **Root cause:** The template matcher only accepted `.ai-engineering/<name>.html` at the top level.
- **Fix:** Match any depth and require `viewer.html.tpl` in the minimum extraction; nested path in the negative fixture.
- **Lesson:** Test every path shape the skill text actually cites, including nested ones, before trusting a citation pattern.
- **Tags:** review, contract, tests

### L139 · 2026-10-27 · floating-core #3 · review
- **Failure:** An unparsable config.toml silently dropped `[git] base`; the resolver fell through to the remote default.
- **Root cause:** `loadConfig` treats an unreadable file as empty.
- **Fix:** The base reader throws on an unreadable or malformed config, naming the path and the fix.
- **Lesson:** A missing value is only "absent" when the source was actually readable; a read that fails must throw, not answer empty.
- **Tags:** review, git, config, fail-closed

### L140 · 2026-10-27 · floating-core #3 · review
- **Failure:** Isolated git reads followed an inherited `GIT_DIR` and mixed two repositories.
- **Root cause:** Isolation removed config injection but kept the repository-locating env vars git sets inside hooks.
- **Fix:** Clear every variable `git rev-parse --local-env-vars` lists; fail if that list can't be read.
- **Lesson:** Isolating a git read means clearing the repository-locating environment as well as config.
- **Tags:** review, git, isolation

### L141 · 2026-10-27 · floating-core #4 · review
- **Failure:** The legacy request-changes path re-emitted `reviewed_main` instead of normalized lifecycle fields.
- **Root cause:** That write path bypassed the shared checkpoint serializer.
- **Fix:** Serialize normalized checkpoint state through the shared codec.
- **Lesson:** Canonical writes must use the shared codec.
- **Tags:** review, lifecycle, serialization

### L142 · 2026-10-27 · floating-core #4 · review
- **Failure:** Legacy checkpoint translation could select `main` even when another base branch was detected.
- **Root cause:** The parser received a hard-coded branch instead of Git context.
- **Fix:** Resolve and pass the detected base; cover a diverged `develop` case.
- **Lesson:** Derive base context from Git.
- **Tags:** review, git, lifecycle

### L143 · 2026-10-27 · floating-core #4 · review
- **Failure:** The checkpoint transition tests had no successful plan-approval-to-implementation case.
- **Root cause:** Coverage asserted refusal without proving the corresponding allowed transition.
- **Fix:** Add the passing transition case alongside the existing refusal.
- **Lesson:** Test each transition's passing and refusing cases.
- **Tags:** review, lifecycle, tests

### L144 · 2026-10-27 · floating-core #4 · review
- **Failure:** Canonical `develop` checkpoints failed request-changes and ready-state listing.
- **Root cause:** Chain validation parsed checkpoints against hard-coded `main`.
- **Fix:** Pass the detected base through chain validation and checkpoint reads; cover a diverged `main` and `develop`.
- **Lesson:** Use the detected base for every checkpoint parse in a lifecycle operation.
- **Tags:** review, git, lifecycle

### L145 · 2026-10-27 · floating-core #5 · behavior
- **Failure:** The repository Copilot hook still invoked the Python checkpoint gate after carrier templates had migrated.
- **Root cause:** `.github/hooks/ai-eng.json` is a checked-in config, not generated from the templates.
- **Fix:** Remove only its obsolete Python hook while preserving chain and post-tool hooks.
- **Lesson:** Verify checked-in local configs separately; template updates do not migrate them.
- **Tags:** behavior, carriers, migration

### L146 · 2026-10-27 · floating-core #5 · behavior
- **Failure:** Generated-payload verification found the committed chain bundle differed from its source.
- **Root cause:** Chain source changed after the last bundle generation.
- **Fix:** Regenerate the bundle with `bun scripts/gen-assets.ts`.
- **Lesson:** Regenerate the committed bundle after chain-source changes.
- **Tags:** behavior, bundle, generated

### L147 · 2026-10-27 · floating-core #5 · review
- **Failure:** Git-prefixed compound Bash commands bypassed checkpoint-write detection.
- **Root cause:** The guard exempted the leading Git command and missed a later write segment.
- **Fix:** Inspect every compound command segment for writes to governed paths.
- **Lesson:** Check every command segment for writes to governed paths.
- **Tags:** review, guard, shell

### L148 · 2026-10-27 · floating-core #5 · review
- **Failure:** Migration could remove a user hook that merely mentioned `checkpoint-gate.py`.
- **Root cause:** The legacy marker matched a path substring rather than the managed command shape.
- **Fix:** Match only the exact standalone managed legacy hook forms.
- **Lesson:** Identify managed commands by their complete shape, not a path mention.
- **Tags:** review, install, migration

### L149 · 2026-10-27 · floating-core #5 · behavior
- **Failure:** `generated-payload.test.ts` found the chain bundle stale again after the guard fix.
- **Root cause:** A later chain-source edit was not followed by bundle regeneration.
- **Fix:** Regenerate after the final source edit and rerun the generated-payload check.
- **Lesson:** Run bundle generation after the last source change, not before a follow-up fix.
- **Tags:** behavior, bundle, generated

### L150 · 2026-10-27 · floating-core #6 · review
- **Failure:** Migration could remove a user wrapper that contained `ai-eng chain`.
- **Root cause:** The installer matched command fragments rather than complete managed hook commands.
- **Fix:** Match exact generated command shapes and test that wrappers survive update.
- **Lesson:** Remove a shared hook only when its complete command is managed.
- **Tags:** review, install, migration

### L151 · 2026-10-27 · floating-core #6 · review
- **Failure:** Cursor's Stop event had no carrier, leaving G8 unenforced for that harness.
- **Root cause:** The lowercase native event key and its follow-up response dialect were not declared.
- **Fix:** Add Cursor's `stop` carrier, response, and event-specific regression tests.
- **Lesson:** Declare native event keys and response dialects per host.
- **Tags:** review, carriers, dialect

### L152 · 2026-10-27 · floating-core #6 · behavior
- **Failure:** The hygiene check reported environment/cwd leakage after a nested carrier test failed.
- **Root cause:** The outer assertion collapsed the child's test failure into a misleading cleanup message.
- **Fix:** Correct the stale carrier wrapper expectation; no cleanup leak was present.
- **Lesson:** Check the nested suite's failure before changing cleanup.
- **Tags:** behavior, tests, diagnostics

### L153 · 2026-10-27 · floating-core #6 · behavior
- **Failure:** Update removed a whole hook group when it contained one managed command.
- **Root cause:** Recursive ownership matching classified the group instead of each command field.
- **Fix:** Match exact command fields, remove managed entries individually, preserve remaining user entries.
- **Lesson:** Remove a group only when no user hooks remain.
- **Tags:** behavior, install, migration

### L154 · 2026-10-27 · floating-core #6 · review
- **Failure:** Managed hook recognition could drift from carrier templates as command forms changed.
- **Root cause:** Installer maintained a duplicate hard-coded list of generated commands.
- **Fix:** Derive exact managed hook commands from embedded settings templates.
- **Lesson:** Derive managed entries from their canonical artifacts and remove only exact matches.
- **Tags:** review, install, templates

### L155 · 2026-10-27 · floating-core #6 · review
- **Failure:** `install.ts` importing `embed.ts` created an import cycle back into `install.ts`.
- **Root cause:** Template-derived managed commands added an edge to a module that already depended on `hashFile` from install.
- **Fix:** Extract shared hash logic and test cycles across the complete module graph.
- **Lesson:** Test declared architecture invariants against the module graph, not only layer boundaries.
- **Tags:** review, architecture, imports

### L156 · 2026-10-27 · floating-core #6 · review
- **Failure:** The new `src/shared-hash.ts` helper was absent from FILEMAP.
- **Root cause:** The source file was added without its repository map entry.
- **Fix:** Add a concise description to FILEMAP.
- **Lesson:** Update FILEMAP when adding source files.
- **Tags:** review, docs, filemap

### L157 · 2026-10-27 · floating-core #7 · behavior
- **Failure:** Four tests still expected brainstorm projections, and U30 checked a path absent from its refresh fixture.
- **Root cause:** Assertions were not updated with the approved Git-only listing/merge behavior, and the fixture premise was wrong.
- **Fix:** Align expectations to Git-only listing and conditional refresh paths; preserve unrelated edits.
- **Lesson:** Keep assertions aligned with approved behavior and verify each fixture's premise.
- **Tags:** behavior, worktree, tests

### L158 · 2026-10-27 · floating-core #7 · behavior
- **Failure:** The push test expected a base-branch refusal but received Gitleaks.
- **Root cause:** The fixture had no configured or remote base, so `resolveContext` correctly returned `ask`.
- **Fix:** Configure `develop`, prove the physical refs/base, then assert the exact push rejection.
- **Lesson:** Prove base context before asserting push protection.
- **Tags:** behavior, git, tests

### L159 · 2026-10-27 · floating-core #7 · behavior
- **Failure:** The skill-contract test found no Phase 3 rebase after CP7 removed the `worktree rebase` CLI verb.
- **Root cause:** Removing the CLI command was conflated with removing the approved native Git rebase step.
- **Fix:** Restore `git rebase <detected base>` and the post-rebase verification gates.
- **Lesson:** Removing a CLI verb must not remove an approved native-Git behavior.
- **Tags:** behavior, workflow, git

### L160 · 2026-10-27 · floating-core #7 · behavior
- **Failure:** Serial tests still expected mandatory managed worktrees, brainstorm projections, and legacy reviewed_main handoffs.
- **Root cause:** Contract assertions encoded the prior workflow instead of the approved optional-worktree/checkpoint contract.
- **Fix:** Update those assertions for optional worktrees, Git-only listing, reviewed_base and CAS behavior.
- **Lesson:** Tests should assert the approved contract, not stale prose or field names.
- **Tags:** behavior, contract, worktree

### L161 · 2026-10-27 · floating-core #7 · behavior
- **Failure:** `generated-payload.test.ts` found the chain bundle stale after the skill correction.
- **Root cause:** The embedded bundle was not regenerated after the final skill/source edit.
- **Fix:** Run `bun scripts/gen-assets.ts` after the last edit and verify generated-payload.
- **Lesson:** Regenerate embedded assets after final skill or source changes.
- **Tags:** behavior, bundle, generated

### L162 · 2026-10-27 · floating-core #7 · behavior
- **Failure:** Ceremony contract found a citation to the removed `ai-eng worktree rebase` command.
- **Root cause:** Phase 3 text still named the deleted CLI verb.
- **Fix:** Remove the stale command citation while retaining native `git rebase <detected base>` and the Phase 4 merge command.
- **Lesson:** Contract text should cite only current commands.
- **Tags:** behavior, workflow, docs
