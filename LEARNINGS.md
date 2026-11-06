# Learnings

Accumulated failures and lessons from building features, mostly written by `/ai-orchestrator`. Every planner, implementer, test writer and reviewer reads **Rules** before starting.

- **Log** is append-only: never edit or delete an entry.
- **Rules** is the distilled version. A lesson is promoted here once it has recurred (2 or more log entries) or caused a human-review rejection or a circuit-breaker stop. Each rule cites the entries it came from.

## Rules

- R1: Assert the current approved behavior, ordering, and exact consumer-visible contents (exact bytes, not presence or `toContain`), not source text, stale prose or field names, or a bare type check; prove each test fails under the mutation it guards against, changing person-controlled state before a poll. (from L2, L11, L102, L160, L187, L207, L246, L247)
- R2: Assert every field and linkage a consumer relies on — in a test, and in a guard that reads output: every path a record can carry, not one string that happens to equal the value. (from L13, L14, L22, L207)
- R3: Check status and approval gates before continuation; cover every acceptance branch, test passing and refusing transitions, and place each guard in the exact configuration where it alone stands between input and harm. (from L7, L12, L18, L83, L84, L143)
- R4: Emit only commands whose target is unambiguous — pin the ref or worktree a command mutates, and never anchor what a command targets (default-branch selection during analysis included) to mutable HEAD. (from L16, L17; the cp2 adversarial review and behavior spot-check both passed it — run emitted commands in the current≠default configuration)
- R5: A fixture must hold its premise against real Git state — prove the relevant SHA, HEAD, base, and owner count before asserting a derived classification, and never let it sit on the guarded branch. (from L19, L20, L158, L182)
- R6: Enforce protection and normalize values at the one choke point every consumer funnels through, not per path — a guard placed only where a test pinned one configuration is forgotten by the next path — and exclude protected refs before presenting deletion candidates. (from L18, L20, L30, L188, L248)
- R7: Derive every list, count, path and precedence from the thing that owns it — the command's own contract or the tool itself (ask Git, do not re-implement it), re-derived at write time — never a neighbour command's sweep, a remembered list, or a number copied into prose, which is only a cache of the command that produces it. (from L15, L21, L27, L248)
- R8: Pin read scope and fail closed: HEAD, user/global config, or repository-locating environment must not decide what a read sees; a read failure is not absence, and a guard that cannot decide denies. Resolve a value only where it is used. (from L16, L23, L139, L140, L165, L248)
- R9: Define remote commands with a closed allowlist; inspect complete command examples before acceptance, reject shell composition and unsafe forms, and accept only bare allowlisted executable names. A static Markdown allowlist cannot secure executable resolution from `PATH`. (from L37–L42, L44–L45)
- R10: Use the already-authenticated Azure CLI and its Azure DevOps extension for Azure DevOps access; never write tokens or credentials. (from L57)
- R11: Scope each contract assertion to the specific command it governs; a neighboring command or generic assertion cannot stand in for it. (from L34–L36)
- R12: Narrow optional and indexed values where they are consumed, and fail closed when a required value is absent. (from L46, L50–L51, L94, L110, L186)
- R13: Sanitize untrusted values at the output boundary; HTML-escape text, validate raw and decoded URLs separately, and do not reprocess inserted content. (from L52–L55, L131)
- R14: Redact credential assignments at the shared output boundary by semantic key families, including nested assignments, while preserving safe near-matches. (from L58–L62)
- R15: Keep executable `.mjs` APIs explicitly declared, and embed script/declaration payloads as text when they are data rather than host modules. (from L47, L64)
- R16: Route repository-owned artifacts through their repository procedure and test the caller-to-procedure handoff; a same-named installed copy may have a conflicting contract. (from L66)
- R17: For runtime p95 checks under parallel test load, use enough samples for nearest-rank p95 to tolerate scheduler outliers without loosening the budget. (from L65, L67)
- R18: Normalize Markdown formatting without altering identifiers; preserve underscores, case, and other contract-significant characters before matching. (from L82, L89, L97, L103)
- R19: Treat ignored paths as user data: explain destructive loss before approval, then carry the irreversible action and actual remaining state through every outcome and caller. (from L105, L107, L169, L195)
- R20: Gate 1 CLI acceptance must assert physical total and unknown classification together; physical presence is not lifecycle certainty. (from L126)
- R21: Preserve state before recording a failure; report rollback only after restoration is proven. (from L91, L92)
- R22: When a workflow moves into a command, update and test the caller handoff before documenting or reviewing the lifecycle. (from L99, L100)
- R23: Bind approval and closure to every immutable plan field and the exact reviewed revision; keep runtime gate state outside that fingerprint. (from L115, L117, L124)
- R24: Regenerate embedded assets after the final source or skill edit, then verify the generated payload. (from L146, L149, L161)
- R25: Keep documentation aligned with current behavior, enforced scope, and supported commands; mark superseded behavior as historical. (from L162, L171, L209, L210)
- R26: Route artifacts and next-step handoffs from the selected lane, as declared by each skill's Lifecycle. (from L189, L193, L194)
- R27: Resolve worktree source and ownership from the invoking or Git-registered checkout, consistent branch-to-path mapping, and a fresh checkpoint—not branch prefixes or directory layout. Establish freshness and owner ambiguity before matching a supplied SHA; unknown ownership stays ambiguous. (from L86, L167, L170, L172, L175, L177–L182)
- R28: Ownership means exact bytes, a recorded hash, or the exact name-and-target link ai-eng wrote; install and cleanup share that one rule, and anything unproven is kept and named (labelled unproven, never the user's), never deleted. Test repair with missing files; when a finding names one write path, sweep its siblings. (from L203, L205, L236, L238, L241, L243, L244)
- R29: Apply defaults and explicit values in one render, and preserve the distinction between omitted and explicitly empty configuration. (from L198, L199, L201, L204)
- R30: Serialize shared claims at the claim boundary and hold the lock across the whole claim; a liveness check or read-then-write does not provide exclusive ownership. A lock records its owner and is reclaimed only when that owner is provably dead; when staleness cannot be proven, hold it. (from L125, L136, L238, L239, L241)
- R31: Merged into R38.
- R32: Reconcile evidence by chronology and direct identity before classifying status; a current comment or shared field does not prove event time or identity. (from L76, L77, L78)
- R33: A PR publishes the existing current branch and verifies publication before forge creation; opening a PR does not create or switch branches. (from L191, L211)
- R34: Derive managed hook commands from canonical artifacts and remove only exact owned entries, preserving user commands and groups. (from L148, L150, L153, L154)
- R35: Derive test-hygiene scope from the active test tree rather than a handwritten suite list. (from L135, L184)
- R36: Keep the invoking checkout's source HEAD separate from its integration base; never refresh from a historical base. (from L163, L168)
- R37: Separate baseline configuration/test-contract failures and pre-existing hygiene artifacts from feature regressions; do not change feature code or budgets to hide them. (from L129, L130, L230)
- R38: Verify path identity, canonical containment and every alias (symlink, hard link, unselected surface) at filesystem boundaries, and bind the check to the exact file and folder the mutation acts on, revalidating after directory creation; a path checked earlier does not establish the current inode. On mismatch abort and preserve the replacement; when the API cannot make that binding, refuse with a warning. (from L87, L88, L183, L220, L222–L224, L226, L228, L229, L234, L235)
- R39: Route every install and cleanup write through the one guarded helper; catch filesystem refusals there and return a named refusal that callers report as a warning while the rest (lock file included) completes. A failed cleanup never changes a file's ownership class. (from L237, L242, L243)
- R40: Edit a user's config by byte offset at the smallest unit requested; parse original and result and write only when the sole difference is the requested key, else refuse with the file byte-identical; run destructive steps only after that write succeeds. (from L218, L245, L246)
- R41: Run gate suites from a Git-backed clone at the exact HEAD, never an archive, with locked dependencies, test homes outside the clone, the default `TMPDIR`, and no injected global or system config. (from L197, L219, L221, L231)
- R42: A failed gate keeps its first failing test, assertion and environment; capture and reproduce that before changing code. (from L197, L215, L217)

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

### L163 · 2026-10-27 · floating-core #7 · review
- **Failure:** A retry could refresh a checkout from an older merge after the base had advanced.
- **Root cause:** Refresh used the historical merge tree without verifying it was still the base tip.
- **Fix:** Skip refresh when the base advanced and verify the target before restoring.
- **Lesson:** Never refresh from a historical base.
- **Tags:** review, git, merge

### L164 · 2026-10-27 · floating-core #7 · review
- **Failure:** Incoming edits made during merge could be overwritten by checkout refresh.
- **Root cause:** The operation reused a cached status snapshot from before the transaction.
- **Fix:** Recheck incoming index, worktree and untracked paths at the restore boundary.
- **Lesson:** Revalidate at the restore boundary.
- **Tags:** review, git, worktree

### L165 · 2026-10-27 · floating-core #7 · review
- **Failure:** A base-resolution error was swallowed, allowing a push without protection.
- **Root cause:** The push guard converted resolution failure into an implicit allow.
- **Fix:** Deny the push and return actionable base-resolution guidance.
- **Lesson:** Failed base resolution must fail closed.
- **Tags:** review, git, fail-closed

### L166 · 2026-10-27 · floating-core #8 · review
- **Failure:** `request-changes` refused a feature built in the current checkout.
- **Root cause:** Source resolution only considered Git-listed worktrees.
- **Fix:** Include the current checkout's exact feature branch while retaining reviewed-SHA/CAS checks.
- **Lesson:** Optional worktrees must not block lifecycle transitions.
- **Tags:** review, worktree, lifecycle

### L167 · 2026-10-27 · floating-core #8 · review
- **Failure:** `worktree rm <slug>` could not manage a worktree created on a branch without `feat/`.
- **Root cause:** Removal assumed branch names always had the `feat/` prefix.
- **Fix:** Resolve the exact branch and derived worktree path without prefix assumptions.
- **Lesson:** Create and remove must share the branch-to-path contract.
- **Tags:** review, git, worktree

### L168 · 2026-10-27 · floating-core #8 · review
- **Failure:** `worktree new` started from the detected integration base instead of current HEAD.
- **Root cause:** The integration destination was confused with the user's current commit.
- **Fix:** Pin new worktrees to current HEAD and warn dirty design files do not travel.
- **Lesson:** The integration base is not the current commit.
- **Tags:** review, git, worktree

### L169 · 2026-10-27 · floating-core #8 · review
- **Failure:** Worktree removal could delete ignored user data before explaining the loss.
- **Root cause:** Ignored files were reported only after removal.
- **Fix:** Refuse by default, fail closed on unreadable scans, and warn before forced deletion.
- **Lesson:** Inspect and explain loss before removal.
- **Tags:** review, data-loss, worktree

### L170 · 2026-10-27 · floating-core #8 · review
- **Failure:** `request-changes` could not transition a feature on an arbitrary branch name.
- **Root cause:** Source and ref resolution assumed the `feat/<slug>` naming convention.
- **Fix:** Resolve the exact checkpoint in the Git-listed/current checkout and use its registered branch ref.
- **Lesson:** Identify lifecycle ownership by checkpoint and checkout, not branch naming.
- **Tags:** review, git, lifecycle

### L171 · 2026-10-27 · floating-core #8 · review
- **Failure:** The worktree skill described creation from the detected integration base instead of current HEAD.
- **Root cause:** The documentation was not updated with the CP8 creation contract.
- **Fix:** Document current HEAD and the dirty brainstorm/PRD warning, preserving Phase 3 rebase and Phase 4 merge.
- **Lesson:** Keep command guidance aligned with behavior.
- **Tags:** review, docs, worktree

### L172 · 2026-10-27 · floating-core #8 · review
- **Failure:** `worktree new` read the primary checkout's branch, HEAD and dirty design files when invoked from a linked worktree.
- **Root cause:** Source state was derived from the primary checkout instead of the invoking checkout.
- **Fix:** Read the caller checkout for branch, HEAD and dirty files while keeping the common repository root for shared refs/registration.
- **Lesson:** Use the invoking checkout for source state; keep the primary root for shared refs and registration.
- **Tags:** review, git, worktree

### L173 · 2026-10-27 · floating-core #8 · review
- **Failure:** Request-changes guidance assumed `feat/<slug>` and a managed-worktree-only flow.
- **Root cause:** The prose inferred branch identity from a naming convention.
- **Fix:** Resolve the exact checkpoint checkout and actual branch ref.
- **Lesson:** Describe the checkout/ref the command validates, not one inferred from naming.
- **Tags:** review, docs, git

### L174 · 2026-10-27 · floating-core #8 · review
- **Failure:** App approval unconditionally triggered local merge.
- **Root cause:** The human approval step was coupled to one integration route.
- **Fix:** Recommend PR with a forge, local merge otherwise, and offer PR, local merge or keep-branch.
- **Lesson:** App approval and integration route are separate decisions.
- **Tags:** review, workflow, git

### L175 · 2026-10-27 · floating-core #8 · review
- **Failure:** `request-changes` rejected a Git-listed checkpoint checkout outside the managed root.
- **Root cause:** Source selection filtered candidates by directory layout instead of checkpoint ownership.
- **Fix:** Accept the unique checkpoint-bearing Git checkout while retaining branch-ref, SHA, CAS and lifecycle checks.
- **Lesson:** Identify lifecycle ownership by Git registration and checkpoint, not directory layout.
- **Tags:** review, git, lifecycle

### L176 · 2026-10-27 · floating-core #8 · review
- **Failure:** `worktree new` missed root-level dirty design files when invoked from a nested directory.
- **Root cause:** `git status` was scoped to the nested path rather than the checkout root.
- **Fix:** Resolve the checkout root before scanning and verify warnings leave files/status unchanged.
- **Lesson:** Normalize status to the checkout root before applying root-relative rules.
- **Tags:** review, git, paths

### L177 · 2026-10-27 · floating-core #8 · review
- **Failure:** List/resume did not recognize an arbitrary-branch worktree carrying the exact checkpoint slug.
- **Root cause:** Feature identity was inferred from branch names instead of checkpoint content in Git-registered checkouts.
- **Fix:** Resolve unique checkpoint ownership from Git registration and preserve dirty-file safety.
- **Lesson:** A checkpoint's registered checkout—not its branch prefix or directory name—defines resume ownership.
- **Tags:** review, git, lifecycle

### L178 · 2026-10-27 · floating-core #8 · review
- **Failure:** Inherited ready-to-merge pins with an old reviewed_base counted as active owners and made ordinary list ambiguous.
- **Root cause:** Checkpoint presence was treated as current ownership without comparing its reviewed base to the detected base.
- **Fix:** Mark stale app-review pins non-actionable and exclude them from active ambiguity; keep duplicate active implementation plans ambiguous.
- **Lesson:** A checkpoint's presence does not prove current ownership; its reviewed base must still match.
- **Tags:** review, lifecycle, git

### L179 · 2026-10-27 · floating-core #8 · review
- **Failure:** `request-changes` counted a stale inherited pin before finding the unique fresh checkpoint.
- **Root cause:** Candidate ambiguity was computed before checking reviewed-base freshness and exact branch refs.
- **Fix:** Filter stale pins and resolve the exact checkout/ref before counting active candidates.
- **Lesson:** Check freshness and exact Git refs before counting ambiguity.
- **Tags:** review, git, lifecycle

### L180 · 2026-10-27 · floating-core #8 · review
- **Failure:** `request-changes` selected one SHA-matching checkout despite multiple active owners of the same slug.
- **Root cause:** Ambiguity was checked after filtering by the supplied SHA.
- **Fix:** Filter stale pins, then refuse multiple active owners before matching the SHA.
- **Lesson:** Establish fresh ownership before matching a supplied SHA.
- **Tags:** review, git, lifecycle

### L181 · 2026-10-27 · floating-core #8 · review
- **Failure:** An unresolved base made active pins appear stale by comparing against the feature tip.
- **Root cause:** Feature-branch state was treated as evidence of the detected base.
- **Fix:** Unknown bases no longer prove staleness; list preserves ambiguity and request-changes fails closed.
- **Lesson:** Unknown freshness cannot prove staleness.
- **Tags:** review, git, fail-closed

### L182 · 2026-10-27 · floating-core #8 · behavior
- **Failure:** Three stale-pin/list regressions failed because their Git fixtures did not represent the intended active/stale owners.
- **Root cause:** Stale-pin fixtures ran on the configured base with unresolved base detection; I39 created two active owners.
- **Fix:** Put stale owners on feature branches with a detectable advanced base; register I39's worktree before committing its checkpoint and assert refs/inheritance.
- **Lesson:** Prove base detectability and owner count in real-Git fixtures; unknown bases remain ambiguous.
- **Tags:** behavior, git, tests

### L183 · 2026-10-27 · floating-core #9 · review
- **Failure:** A symlinked parent could redirect worktree creation outside the configured worktrees root.
- **Root cause:** Containment was lexical and did not resolve existing symlink components.
- **Fix:** Canonicalize root and parent, check containment before/after creating parents, and test the escaped target.
- **Lesson:** Verify canonical paths at filesystem boundaries with `relative` and platform `sep`, then revalidate after directory creation.
- **Tags:** review, filesystem, paths

### L184 · 2026-10-27 · floating-core #10 · behavior
- **Failure:** Test hygiene reported env/cwd leakage after CP10 removed `tests/spec-command.spec.ts`.
- **Root cause:** The hygiene check still enumerated a deleted test suite and failed before running child suites.
- **Fix:** Replace the obsolete suite entry with active `tests/update-command.spec.ts`; keep the restoration assertion intact.
- **Lesson:** Keep test-hygiene inputs aligned with the active suite set.
- **Tags:** behavior, tests, hygiene

### L185 · 2026-10-27 · floating-core #10 · review
- **Failure:** Removing a required git/workflow architecture rule did not fail `tests/arch.spec.ts`.
- **Root cause:** `requiredRestrictions` omitted those source-target fences.
- **Fix:** Assert each required git and workflow restriction explicitly.
- **Lesson:** Pin each required source-target fence so removing its config rule fails the test.
- **Tags:** review, architecture, tests

### L186 · 2026-10-27 · floating-core #11 · behavior
- **Failure:** Typecheck rejected optional regex capture groups in `tests/ai-pr.spec.ts`.
- **Root cause:** The test treated a possibly absent capture as a definite string.
- **Fix:** Narrow each capture at the point of use.
- **Lesson:** Narrow optional values where they are consumed.
- **Tags:** behavior, types, tests

### L187 · 2026-10-27 · floating-core #11 · behavior
- **Failure:** Git cleanup tests required a hard-coded main branch and force-deletion by default.
- **Root cause:** Assertions pinned the prior workflow rather than the approved detected-base/preview contract.
- **Fix:** Assert native preview, detected base and safe deletion defaults.
- **Lesson:** Tests must assert the current approved contract.
- **Tags:** behavior, git, tests

### L188 · 2026-10-27 · floating-core #11 · review
- **Failure:** Cleanup preview could list the selected base branch as a deletion candidate.
- **Root cause:** Candidate filtering did not exclude the protected base ref.
- **Fix:** Filter the selected base before showing deletion candidates.
- **Lesson:** Exclude protected refs before presenting deletion candidates.
- **Tags:** review, git, cleanup

### L189 · 2026-10-27 · floating-core #11 · review
- **Failure:** Brainstorm unconditionally wrote design slots and handed every path to the full orchestrator.
- **Root cause:** Slot/handoff actions were not scoped by work lane.
- **Fix:** Limit them to standard/full; light paths end at `ai-verify`.
- **Lesson:** Gate artifacts by lane.
- **Tags:** review, workflow, skills

### L190 · 2026-10-27 · floating-core #11 · review
- **Failure:** The brainstorm's broad creative-work trigger conflicted with Direct's no-brainstorm path.
- **Root cause:** Trigger wording ignored clear one-step work.
- **Fix:** Exclude clear Direct/light tasks and add cross-skill coverage.
- **Lesson:** Route clear work to its relevant skill.
- **Tags:** review, workflow, skills

### L191 · 2026-10-27 · floating-core #11 · review
- **Failure:** A requested PR for a local-only branch could be created without first publishing the branch.
- **Root cause:** The PR guidance skipped push/verification before forge creation.
- **Fix:** Push and verify the selected remote branch only when a PR is requested.
- **Lesson:** Verify publication before creation.
- **Tags:** review, git, pr

### L192 · 2026-10-27 · floating-core #11 · review
- **Failure:** Forge create commands could receive full remote-tracking refs as branch arguments.
- **Root cause:** Git refs and forge branch names were treated as the same value.
- **Fix:** Keep `$base_ref` for Git and use short `$base_branch` for forge calls.
- **Lesson:** Separate Git refs from forge branch names.
- **Tags:** review, git, pr

### L193 · 2026-10-27 · floating-core #11 · review
- **Failure:** Architectural brainstorm approval routed directly to the orchestrator despite Lifecycle naming `ai-architect` next.
- **Root cause:** The handoff ignored the selected work lane.
- **Fix:** Route architecture to `ai-architect`, standard to `ai-orchestrator`, and test route/Lifecycle consistency.
- **Lesson:** Keep approval handoffs lane-specific and verify them against Lifecycle.
- **Tags:** review, workflow, skills

### L194 · 2026-10-27 · floating-core #11 · review
- **Failure:** Architectural brainstorm Lifecycle still routed directly to the orchestrator.
- **Root cause:** The handoff did not distinguish architecture from standard work.
- **Fix:** Route architecture through ai-architect, standard through ai-orchestrator, and test both Lifecycle contracts.
- **Lesson:** Keep each lane's handoff aligned with Lifecycle.
- **Tags:** review, workflow, skills

### L195 · 2026-10-27 · floating-core #11 · review
- **Failure:** Cleanup preview omitted ignored files that deletion could remove.
- **Root cause:** Ignored files were treated as absent rather than user data.
- **Fix:** List paths and consequences before approval, require per-path consent, and fail closed if the list changes or cannot be verified.
- **Lesson:** Treat ignored paths as user data until their loss is visible and approved.
- **Tags:** review, data-loss, cleanup

### L196 · 2026-10-27 · floating-core #11 · review
- **Failure:** App-review transitions on arbitrary branches could not validate the reviewed feature SHA.
- **Root cause:** The guard inferred the feature ref from `feat/${slug}` and checked it only on review entry.
- **Fix:** Resolve HEAD's local branch ref dynamically and revalidate the tip at both review entry and approval.
- **Lesson:** Validate reviewed SHAs against the selected Git ref; do not infer branch identity from slugs.
- **Tags:** review, git, lifecycle

### L197 · 2026-10-28 · floating-core #12 · behavior
- **Failure:** The serial Gate 1 suite exited 1, but its runner summary omitted the failing test; the first diagnostic rerun could not reproduce it.
- **Root cause:** The diagnostic set `TMPDIR` inside the worktree, causing the environment guard to reject the repo-local `AI_ENG_HOME`; the original failure remains undiagnosed.
- **Fix:** No source change; reproduce with the default environment and capture the first failing test before choosing a fix.
- **Lesson:** Do not set `TMPDIR` inside the repository when diagnosing tests; the environment guard treats the resulting home path as repo-local.
- **Tags:** behavior, tests, bun, environment

### L198 · 2026-10-28 · floating-core #12 · behavior
- **Failure:** The serial suite failed at U9 because the rendered `config.toml` did not keep optional pack configuration valid and commented out.
- **Root cause:** `src/embed.ts` left the new `{{packs}}` template placeholder unresolved when the render caller omitted the optional value, so `loadConfig` returned an empty config.
- **Fix:** Default omitted packs to an empty list; the focused U9 test then passed.
- **Lesson:** Give optional template fields safe defaults at the rendering boundary.
- **Tags:** behavior, config, templates, tests

### L199 · 2026-10-28 · floating-core #12 · behavior
- **Failure:** A legacy update without `[canon] packs` expected all six packs to be adopted, but the update test received none.
- **Root cause:** The config template's empty default replaced the selected packs before the second render.
- **Fix:** Pass surfaces and packs directly to the template renderer; focused update, init, and config tests passed.
- **Lesson:** Apply defaults and explicit values in a single render.
- **Tags:** behavior, update, config, packs

### L200 · 2026-10-28 · floating-core #12 · behavior
- **Failure:** Bun stopped at the ceremony-contract command because it did not match the test file using a path without `./`.
- **Root cause:** Bun's file selector did not resolve this test from the bare relative path.
- **Fix:** Use `bun test ./tests/ceremony-contract.spec.ts`; the focused command passed all four tests.
- **Lesson:** Use explicit `./` relative paths when selecting Bun tests by file.
- **Tags:** behavior, tests, bun

### L201 · 2026-10-28 · floating-core #12 · behavior
- **Failure:** Dirty recovery for a legacy governed config without `[canon] packs` omitted the expected `stale` classification.
- **Root cause:** `doctor` treated an absent packs key as an explicit empty selection, classifying installed pack files as foreign.
- **Fix:** Use legacy packs only when the governed config omits the key; preserve an explicit empty selection.
- **Lesson:** Keep absent and explicitly empty configuration values distinct across readers.
- **Tags:** behavior, doctor, config, packs, recovery

### L202 · 2026-10-28 · floating-core #12 · review
- **Failure:** The verify setup guide still referenced `skills/ai-verify/tiers/` after those tools moved into the optional pack.
- **Root cause:** The guide hard-coded the retired core path instead of following the pack source and installed inventory.
- **Fix:** Update the source/install paths and assert the selected pack payload in `tests/embed-canon.spec.ts`.
- **Lesson:** Keep setup paths tied to the pack source and installed inventory.
- **Tags:** review, docs, packs, paths, tests

### L203 · 2026-10-28 · floating-core #13 · review
- **Failure:** Update canon repair could overwrite a selected skill changed on the machine.
- **Root cause:** The repair trusted installed canon files as disposable, but the repository lock does not record machine-side edits.
- **Fix:** Preserve and report differing canon skills during update repair; add regression coverage for edits and explicit pack selections.
- **Lesson:** Without a machine-side ownership hash, preserve differing canon files rather than treating them as disposable.
- **Tags:** review, update, canon, data-loss, packs

### L204 · 2026-10-28 · floating-core #14 · behavior
- **Failure:** The serial suite took 204.83 seconds against a 120-second target and failed four tests; the first doctor case expected zero missing files but found 36.
- **Root cause:** The doctor fixture omitted `canon.packs`, invoking legacy-pack expectations while installing only core; test hygiene also reran sandbox suites.
- **Fix:** Declare core-only fixture intent, test selected and legacy packs, replace nested suite reruns with preload guards, and reuse Git fixture templates.
- **Lesson:** Distinguish omitted packs (legacy) from explicit `[]` (core-only), and enforce suite hygiene during normal runs.
- **Tags:** behavior, tests, performance, config, packs

### L205 · 2026-10-28 · floating-core #14 · behavior
- **Failure:** The next full-suite run stopped at the global-canon recovery test, which expected update to overwrite a locally edited global skill.
- **Root cause:** The test's expected overwrite contradicted CP13's ownership rule: changed canon files have no machine-side ownership hash.
- **Fix:** Test repair of missing core files separately and preserve locally edited files; remove duplicate worktree setup and raw-Git cases.
- **Lesson:** Without a machine-side ownership hash, preserve changed canon files and test repair using missing files.
- **Tags:** behavior, tests, update, canon, performance

### L206 · 2026-10-28 · floating-core #14 · behavior
- **Failure:** The serial suite passed its tests but took 149.20 seconds against the 120-second target.
- **Root cause:** Worktree fixtures repeated Git queries and staging work; the focused-suite timing did not confirm a runtime improvement.
- **Fix:** Reuse worktree-list metadata and commit tracked fixture paths directly; 118 focused tests and 1,045 assertions passed.
- **Lesson:** Reuse Git state already fetched in integration fixtures, and measure the full suite before claiming a speedup.
- **Tags:** behavior, tests, performance, git

### L207 · 2026-10-28 · floating-core #14 · review
- **Failure:** Review found the brainstorm-to-orchestrator handoff assertion missing, and canon recovery asserted file existence without checking repaired content.
- **Root cause:** Consolidation removed a handoff check not covered elsewhere; the recovery test checked presence rather than payload integrity.
- **Fix:** Assert the standard-lane handoff boundary and compare repaired content to the shipped payload while preserving local edits.
- **Lesson:** Test workflow links at the handoff boundary and verify repaired payloads exactly.
- **Tags:** review, tests, workflow, canon, packs

### L208 · 2026-10-28 · floating-core #16 · review
- **Failure:** A successful `commit-msg` with an active override printed a notice despite the zero-line green-hook contract.
- **Root cause:** The shared hook writer emitted every result's lines without checking whether the hook had succeeded.
- **Fix:** Suppress output for successful hook results while retaining denial lines and exit behavior; cover the active-override hook path.
- **Lesson:** Gate shared hook output on result status, while keeping success metadata in the commit and denial reasons visible.
- **Proof:** `bun test ./tests/token-budget.spec.ts` — 6 pass, 0 fail, 37 assertions.
- **Tags:** review, hooks, overrides, output, tests

### L209 · 2026-10-28 · floating-core #17 · review
- **Failure:** Review found unsupported worktree file hints, stale worktree lifecycle claims, and incomplete comment-read scope in the docs.
- **Root cause:** The docs had drifted from the current CLI, worktree lifecycle, and comment-read contract.
- **Fix:** Remove unsupported hints, mark superseded lifecycle notes as historical, and document relation-target comment reads.
- **Lesson:** Verify documented behavior against the current CLI and adapter contract.
- **Tags:** review, docs, cli, lifecycle, permissions

### L210 · 2026-10-28 · floating-core #17 · review
- **Failure:** Review found that PERMISSIONS.md omitted hierarchy-only relation scope and the exact recent-comment query; blueprint used a nonexistent Git command and fixed base.
- **Root cause:** The docs described broader permission scope and stale command/base behavior than the implementation enforces.
- **Fix:** Document the precise relation/query limits and supported command with selected-base behavior.
- **Lesson:** Keep documentation aligned with enforced scope and actual commands.
- **Tags:** review, docs, permissions, git, cli

### L211 · 2026-10-28 · floating-core #17 · review
- **Failure:** The blueprint said ai-pr creates a branch from local main and targets main.
- **Root cause:** The prose conflated PR publishing with worktree branch creation and integration.
- **Fix:** Describe publishing the current checkout/worktree branch with the supported base selection and no branch creation or switching.
- **Lesson:** Keep PR publishing distinct from worktree branch creation and integration.
- **Tags:** review, docs, ai-pr, git, base-selection

### L212 · 2026-10-28 · floating-core #17 · behavior
- **Failure:** Phase 3 failed because the floor-gates test expected Git stderr newlines verbatim after the output cap flattened them.
- **Root cause:** The test asserted incidental formatting, although the hook preserves diagnostic content, exit status, and the three-line budget.
- **Fix:** Assert diagnostic content independently of line formatting.
- **Lesson:** Check preserved diagnostics, exit status, and output budget—not incidental formatting.
- **Tags:** behavior, tests, hooks, output

### L213 · 2026-10-29 · floating-core #18 · behavior
- **Failure:** `tests/init-command.spec.ts` expected init to write an empty `[canon].packs` list after the approved contract removed pack selection.
- **Root cause:** The test still asserted the old optional-pack config shape.
- **Fix:** Assert the key is absent and match the prompt on a stable short label that does not depend on terminal wrapping.
- **Lesson:** Assert the approved config contract, not obsolete serialization or wrapped terminal text.
- **Proof:** Focused `init-command` suite: 33 tests passed; typecheck passed.
- **Tags:** behavior, tests, config, skills

### L214 · 2026-10-29 · floating-core #18 · behavior
- **Failure:** `tests/embed-canon.spec.ts` treated the verification setup guide's generic `skills/<skill-name>/` example as a missing installed skill.
- **Root cause:** The test checked every displayed reference as a literal payload path, including a placeholder.
- **Fix:** Check concrete guide paths against the payload and ignore placeholder examples.
- **Lesson:** Validate concrete documented paths against the inventory, not generic template placeholders.
- **Proof:** `bun test tests/embed-canon.spec.ts` — 16 tests passed; `bun run typecheck` passed.
- **Tags:** behavior, tests, assets, skills

### L215 · 2026-10-29 · floating-core #18 · behavior
- **Failure:** Gate 1's full `bun test` exited 1 after 247 targeted tests and the build passed; the gate report omitted the failing test name and assertion.
- **Root cause:** Not established; the report retained the command exit but not the full failure details.
- **Fix:** Automatically split CP18 into focused source/asset and install-behavior checkpoints, then rerun their targeted commands before the next full suite.
- **Lesson:** A failed full-suite gate must preserve the first failing test and assertion before selecting a code fix.
- **Tags:** behavior, tests, reporting

### L216 · 2026-10-29 · floating-core #19 · behavior
- **Failure:** `tests/adversarial/init-recovery.test.ts` expected zero canon drift after update but observed one.
- **Root cause:** A previous test left a locally edited skill in shared test state; update correctly preserved that edit, so the later clean-canon assertion was invalid.
- **Fix:** Restore the shipped skill fixture before the clean-canon check.
- **Lesson:** Reset intentional shared-state mutations before tests that expect a clean baseline.
- **Proof:** Focused init-recovery suite: 13 tests passed; full serial suite: 1,556 passed, 16 skipped.
- **Tags:** behavior, tests, install, state

### L217 · 2026-10-29 · floating-core #19 · behavior
- **Failure:** One clean-clone Gate 1 run reported nine init-command failures; a focused rerun of the same suite passed all 33 tests.
- **Root cause:** Not established; the gate and focused rerun did not reproduce the same result.
- **Fix:** No code change; stop rather than guess after two diagnostic attempts.
- **Lesson:** Capture the failing assertion and matching test environment before changing code when a gate failure is not reproducible.
- **Proof:** Focused `tests/init-command.spec.ts` suite: 33 passed; typecheck passed.
- **Tags:** behavior, tests, reproducibility

### L217 · 2026-10-29 · floating-core #19 · behavior
- **Failure:** One clean-clone Gate 1 run reported nine init-command failures; a focused rerun of the same suite passed all 33 tests.
- **Root cause:** Not established; the gate and focused rerun did not reproduce the same result.
- **Fix:** No code change; stop rather than guess after two diagnostic attempts.
- **Lesson:** Capture the failing assertion and matching test environment before changing code when a gate failure is not reproducible.
- **Proof:** Focused `tests/init-command.spec.ts` suite: 33 passed; typecheck passed.
- **Tags:** behavior, tests, reproducibility

### L218 · 2026-10-30 · floating-core #19 · review
- **Failure:** Adversarial review found defects in config parsing, symlink containment, uninstall scope, and halted-viewer findings links.
- **Root cause:** The config, filesystem ownership, and viewer-state boundaries lacked complete behavior-level coverage.
- **Fix:** Corrected the four behaviors and added focused regression tests.
- **Lesson:** Treat configuration syntax, filesystem ownership, and every viewer state as explicit boundaries, and verify each with a behavior-level regression.
- **Tags:** review, config, filesystem, uninstall, viewer

### L219 · 2026-10-30 · floating-core #19 · behavior
- **Failure:** Two full-suite tests failed in the isolated CP19 gate copy at `git read-tree HEAD`.
- **Root cause:** The gate copy was created with `git archive`, which omits `.git` even though the tests require Git metadata.
- **Fix:** Rerun the gate from a local Git-backed clone at the exact selected HEAD, without fetching.
- **Lesson:** Do not run Git-dependent tests from an archive; use a local Git-backed checkout when repository metadata is part of the test precondition.
- **Tags:** behavior, tests, git, isolation

### L220 · 2026-10-30 · floating-core #19 · review
- **Failure:** Review found cleanup could follow a symlinked parent, misclassify `skills-backup/`, and prune a directory after another process created a file.
- **Root cause:** Containment, component identity, and deletion-time emptiness were not enforced at the filesystem operation boundary.
- **Fix:** Require canonical component-checked containment and use atomic empty-directory pruning.
- **Lesson:** Cleanup ownership requires canonical, component-checked containment, and directory pruning must use the filesystem's atomic empty-directory operation.
- **Tags:** review, filesystem, symlink, uninstall

### L221 · 2026-10-30 · floating-core #19 · behavior
- **Failure:** An initial post-fix carrier test run failed after the verification runner added a system-config override.
- **Root cause:** The runner altered the system-config contract while isolating the home directory.
- **Fix:** Remove the unrelated override and rerun Gate 1 with only the required isolated paths.
- **Lesson:** Isolate test homes without injecting unrelated global or system configuration.
- **Tags:** behavior, tests, configuration, isolation

### L222 · 2026-10-30 · floating-core #19 · review
- **Failure:** Review found path checks could be raced before `writeFileSync` or `unlinkSync` by replacing the checked parent with a symlink.
- **Root cause:** The path was checked, then reopened by absolute name for mutation, leaving a race where replacing its parent with a symlink redirected the operation.
- **Fix:** Pin mutations to the checked directory for unlink, write, and prune operations.
- **Lesson:** Bind mutations to the checked directory at the operation boundary instead of reusing a previously checked pathname.
- **Tags:** review, filesystem, race, symlink, uninstall

### L223 · 2026-10-30 · floating-core #19 · circuit-breaker
- **Failure:** Replanned CP19 review failed three rounds; F1 path-identity races remained and round 3 found a replaced-symlink cleanup case.
- **Root cause:** Not established; further changes could alter destructive behavior without a confirmed ownership invariant.
- **Fix:** Stop at the circuit breaker and request the intended behavior for concurrent file or symlink replacement.
- **Lesson:** Do not guess at destructive filesystem semantics after repeated review failures; confirm the ownership invariant before continuing.
- **Tags:** circuit-breaker, review, filesystem, race

### L224 · 2026-10-30 · floating-core #19 · review
- **Failure:** Review found ownership checks could authorize unlink or truncating writes after the file or symlink had been replaced.
- **Root cause:** Cleanup authorized later path operations from stale ownership checks, without verifying the same file identity/content or symlink target was still present.
- **Fix:** Snapshot file identity/version/bytes from no-follow descriptors and revalidate before unlink or truncating writes; pin mirror parents and recheck symlink identity, target text, and canonical target before unlink, aborting without retry on mismatch.
- **Lesson:** Cleanup must preserve any replacement whose file identity, content, or symlink target no longer matches the ownership snapshot.
- **Tags:** review, filesystem, race, symlink, ownership

### L225 · 2026-10-30 · floating-core #19 · review
- **Failure:** I73 showed a failed machine-carrier settings write could leave the user's original bytes partially overwritten.
- **Root cause:** `installMachineCarriers` and `removeMachineCarriers` wrote merged settings in place, so a failed write could truncate a user-owned file before I73 asserted its original bytes.
- **Fix:** Stage a complete sibling replacement and revalidate ownership snapshots before atomic replacement; preserve concurrent changes and clean only this attempt's staged inode.
- **Lesson:** Preserve user-owned settings by staging writes and revalidating the exact filesystem identity at the commit boundary.
- **Tags:** review, filesystem, write, atomic, ownership

### L226 · 2026-10-30 · floating-core #19 · review
- **Failure:** Review found the atomic staging fix could still overwrite or remove a replacement between snapshot validation and `renameSync`/`unlinkSync`.
- **Root cause:** The F5 snapshot checks still preceded path-based `renameSync`/`unlinkSync`; portable Node/Bun filesystem APIs provide no operation that conditionally mutates a pathname only while it names the validated inode.
- **Fix:** Machine-settings creation, replacement, and removal fail closed when pathname mutation is required; warnings explain the refusal, while other cleanup removes only temp files created by the current attempt.
- **Lesson:** A pathname check cannot bind a later syscall to an inode; when the portable filesystem API cannot make that binding, refuse the mutation instead of claiming the race is closed.
- **Tags:** review, filesystem, race, fail-closed, carriers

### L227 · 2026-10-30 · floating-core #19 · behavior
- **Failure:** Seven full-suite tests expected init, update, config, or uninstall to mutate machine settings after the fail-closed safety change.
- **Root cause:** Those tests treated machine-settings registration as required even when the path could not be safely mutated; they did not separate local canon behavior from host registration.
- **Fix:** Assert local skill installation/configuration and lock recovery independently, while expecting an explicit warning and unchanged machine settings when registration is refused.
- **Lesson:** Test local canon behavior separately from machine-settings registration and assert the warning on a safe refusal.
- **Proof:** Clean Git-backed full suite: 1,570 passed, 16 skipped, 0 failed.
- **Tags:** behavior, tests, carriers, fail-closed

### L228 · 2026-10-30 · floating-core #19 · review
- **Failure:** A user settings symlink or hard link could alias `machine.json`, allowing internal writes or deletion to affect user-owned data.
- **Root cause:** Refusal checked the requested settings pathname but did not check whether another user-owned name resolved to the same target or inode.
- **Fix:** Detect resolved-path and inode aliases; refuse the settings operation, warn, and skip machine-state mutation.
- **Lesson:** Refuse indirect aliases too; protecting only the requested pathname leaves user data exposed.
- **Proof:** Git-backed focused CP19 tests: 136 passed; typecheck and lint passed.
- **Tags:** review, filesystem, alias, ownership, fail-closed

### L229 · 2026-10-30 · floating-core #19 · review
- **Failure:** Review found unselected settings aliases and aliases changed after validation could still expose `machine.json` to writes or deletion.
- **Root cause:** Alias checks covered selected surfaces only and were not repeated at the mutation boundary.
- **Fix:** Check every settings surface, refuse mutation when aliases or snapshots changed, and add symlink/hard-link regressions.
- **Lesson:** Revalidate the complete alias set immediately before machine-state writes or deletion.
- **Tags:** review, data-loss, cleanup, machine-state, symlink

### L230 · 2026-10-30 · floating-core #19 · behavior
- **Failure:** The carrier-merge Gate 1 command failed its suite-level hygiene guard because temporary paths already existed under `tests/`.
- **Root cause:** Verification ran in the selected checkout with four pre-existing `.worktree-lifecycle-*` files, which the hygiene guard treats as contamination.
- **Fix:** Preserve those files and rerun verification in a clean Git-backed scratch clone; the isolated carrier-merge suite passed 13 tests.
- **Lesson:** Separate baseline hygiene artifacts from leaks created by the test run.
- **Tags:** behavior, tests, hygiene, cleanup

### L231 · 2026-10-30 · floating-core #19 · behavior
- **Failure:** The first isolated Gate 1 retry stopped at carrier-merge before the remaining commands ran.
- **Root cause:** The clone lacked installed dependencies, and its test-home path was inside the checkout, which `src/env.ts:18` rejects.
- **Fix:** Install locked dependencies in the clone and place isolated test homes outside it; carrier-merge then passed 13 tests.
- **Lesson:** Git-backed test clones need locked dependencies and test-home paths outside the checkout.
- **Tags:** behavior, tests, isolation, clone

### L232 · 2026-10-30 · floating-core #19 · behavior
- **Failure:** The lock-security verification failed a refusal-message membership assertion even though the expected string appeared in the array.
- **Root cause:** The test used Bun's `toInclude` matcher for array membership.
- **Fix:** Use `toContain`; the focused lock-security test passed 9 cases.
- **Lesson:** Use the matcher that fits the value's type.
- **Tags:** behavior, tests, security, assertion

### L233 · 2026-10-30 · floating-core #19 · circuit-breaker
- **Failure:** Replanned CP19 adversarial review attempt 3 returned with F8, F9, and F10 open.
- **Root cause:** Unresolved; detailed findings remain in `.ai-engineering/workflow/reviews/floating-core-19.md` and need human interpretation before further destructive changes.
- **Fix:** Halted at the review circuit breaker and preserved the selected checkout, baseline artifacts, and review thread.
- **Lesson:** After a split checkpoint exhausts three review attempts, stop and retain the exact findings rather than applying another unreviewed cleanup change.
- **Tags:** circuit-breaker, review, filesystem, data-loss, cleanup

### L234 · 2026-10-30 · floating-core #19 · review
- **Failure:** F8: `machine.json` could still be written or deleted by pathname after a separate alias scan, and writes followed a symlinked `machine.json`.
- **Root cause:** The alias check and the mutation were separate pathname operations.
- **Fix:** Never rewrite `machine.json` in place; refuse links, non-files and second names; move it to a private name, verify bytes and aliases, then replace without overwriting, restoring and warning on mismatch.
- **Lesson:** Bind the check to the exact file being changed; when that fails, refuse and keep the original.
- **Tags:** review, data-loss, machine-state, symlink, fail-closed

### L235 · 2026-10-30 · floating-core #19 · review
- **Failure:** F9: canon cleanup hashed and deleted files by pathname without rechecking the parent folder or the file.
- **Root cause:** Ownership was proven on a path, not on the file in the checked folder at deletion time.
- **Fix:** Delete and prune from inside the checked folder and recheck the file immediately before deletion.
- **Lesson:** A hash is not proof of ownership unless the deletion acts on the same file in the same folder.
- **Tags:** review, data-loss, cleanup, ownership

### L236 · 2026-10-30 · floating-core #19 · review
- **Failure:** F10: any mirror link pointing into the canon was treated as installer-owned and removed.
- **Root cause:** Ownership was inferred from the link target's location instead of the exact pair the installer writes.
- **Fix:** Remove only exact `name -> <home>/skills/name` links.
- **Lesson:** Ownership means the exact name and target pair we created, not "points somewhere ours".
- **Tags:** review, cleanup, symlink, ownership

### L237 · 2026-10-30 · floating-core #19 · review
- **Failure:** F11/F12: an unreadable or linked machine-settings path made carrier install/removal throw, and the moved-carrier sweep wrote through a symlink into the user's home settings.
- **Root cause:** Snapshot errors escaped the carrier loops, and the sweep used plain path reads and writes instead of the guarded no-follow helpers.
- **Fix:** Refuse unreadable settings as `settings-unreadable` and continue so `ai-eng.lock` is written; route every cleanup through the shared no-follow helpers in `src/embed.ts`.
- **Lesson:** Every cleanup path must use the same guarded file helpers, and every snapshot call must fail closed, not only the bulk scan.
- **Tags:** review, data-loss, symlink, fail-closed, carriers

### L238 · 2026-10-30 · floating-core #19 · review
- **Failure:** F13-F16: a concurrent run could overwrite `machine.json` mid-commit, and uninstall or update deleted user-edited commands, module carriers and user-added skill files.
- **Root cause:** The claim rename left `machine.json` absent without a lock, and ownership was guessed from names or substrings instead of recorded hashes or exact bytes.
- **Fix:** Hold a lock across the whole claim; remove only byte-identical installer files; record canon hashes in `canon-owned.json` and delete only on a hash match.
- **Lesson:** Ownership means exact bytes or a recorded hash; without one, keep the file.
- **Tags:** review, data-loss, cleanup, ownership, concurrency

### L239 · 2026-10-30 · floating-core #19 · review
- **Failure:** F18: a lock left by a crash blocked machine state forever, and an interrupted claim hid `machine.json`, so uninstall silently skipped restoring git `init.templateDir`.
- **Root cause:** The lock had no owner record and no recovery path; a missing `machine.json` read as "no state".
- **Fix:** Record pid, host and start time; reclaim atomically only when the owner is dead on this host; restore a lone claim copy under the lock; warn instead of skipping the restore.
- **Lesson:** A lock needs an owner record and a provable-stale recovery path.
- **Tags:** review, concurrency, lock, machine-state, fail-closed

### L240 · 2026-10-30 · floating-core #19 · review
- **Failure:** F19-F22: the ownership record truncated through a hard link, kept user files counted as stale forever, a repo settings file without ai-eng entries was warned about, and uninstall dropped the record while recorded files remained.
- **Root cause:** Shared names were truncated instead of replaced, and warnings counted states their fix could not clear.
- **Fix:** Replace the record by temp-file rename; classify unprovable extras as kept user files; warn only for files holding ai-eng entries; keep the record while recorded files exist.
- **Lesson:** A warning must only count what its fix can clear, and a proof stays while what it proves is still there.
- **Tags:** review, cleanup, ownership, doctor

### L241 · 2026-10-30 · floating-core #19 · review
- **Failure:** F23: outdated canon files from earlier releases were labelled "kept user file" because no release up to v2.6.0 recorded canon hashes; F24: lock staleness relied on host name and pid only.
- **Root cause:** There was no ownership proof to migrate, and a dead pid does not prove the owner is gone across boots or pid namespaces.
- **Fix:** Add an `unproven` class that is never deleted, carried in `canon-owned.json`, and shown in one doctor warn row; record boot ID and pid namespace on Linux and hold the lock when they cannot be read.
- **Lesson:** When no ownership proof ever existed, label the file unproven, never the user's, and keep it visible until a person clears it.
- **Tags:** review, ownership, migration, lock, doctor

### L242 · 2026-10-30 · floating-core #19 · review
- **Failure:** F25/F26: a refused canon delete or write made update and uninstall throw before writing `ai-eng.lock`, and a provably canon-owned stale page that could not be removed was reclassified as a user file and lost its hash.
- **Root cause:** The shared `withSafeProjectParent` helper had no refusal handling, and a failed deletion moved the file into the kept class.
- **Fix:** The helper returns a refusal for errno failures and callers warn with the path; refused stale pages keep their hash in a separate `refused` list and are retried; an unwritable lock exits 1 with a warning.
- **Lesson:** Catch filesystem refusals once at the shared helper, and never let a failed cleanup change a file's ownership class.
- **Tags:** review, fail-closed, cleanup, ownership

### L243 · 2026-10-30 · floating-core #19 · review
- **Failure:** F27-F30: a symlinked canon skill or folder crashed update/init/config before `ai-eng.lock`; install warnings were dropped or shown as ✓; the uninstall refusal had no regression; agent install overwrote same-named user files and repointed user links.
- **Root cause:** Deliberate symlink refusals threw a plain error that handlers treated as a bug; callers were not updated when install started returning warnings; install did not share cleanup's ownership rule.
- **Fix:** Symlink refusals return a named refusal and the rest installs; one shared row helper shows ⚠ warnings; agents install replaces only the exact installer link or prior install bytes.
- **Lesson:** A deliberate refusal must look like a refusal, and install needs the same ownership rule as cleanup: exact bytes or the exact link.
- **Tags:** review, symlink, ownership, fail-closed, carriers

### L244 · 2026-10-30 · floating-core #19 · review
- **Failure:** F31/F32: slash-command shims were written through user links and over edited files, and skill-mirror links owned by the user were repointed; a sweep found the same pattern for `version.json` and module carriers.
- **Root cause:** Install paths wrote by pathname without the ownership rule cleanup already used.
- **Fix:** Create missing files with `wx`, refresh only bytes ai-eng rendered (current or previous), replace only the exact link ai-eng writes, and keep and name everything else.
- **Lesson:** Install and cleanup must share one ownership rule; when a finding names one write path, sweep every sibling write in the same pass.
- **Tags:** review, ownership, symlink, install, carriers

### L245 · 2026-10-30 · floating-core #21 · review
- **Failure:** `ai-eng config` produced unparseable config.toml for multi-line lists, dotted keys, inline tables and `[ surfaces ]` headers, and `--remove` deleted carriers before the config write; the README claim about config bytes was false and omitted `adapt apply`.
- **Root cause:** The writer edited lines and wrote the result without parsing it, and destructive steps ran before the write succeeded.
- **Fix:** Parse original and result, write only when the sole difference is `surfaces.enabled`, otherwise refuse with the file byte-identical and exit 2; remove carriers only after a successful write; README names every command that rewrites config.toml.
- **Lesson:** Judge a text edit of a config file by parsing the result before writing, and run destructive steps only after that write succeeds.
- **Tags:** review, configuration, toml, fail-closed

### L246 · 2026-10-30 · floating-core #22 · review
- **Failure:** `ai-eng config` dropped `\r` on CRLF files, refused `[surfaces] # comment` under CRLF, dropped comments inside multi-line lists, and normalised spacing around `=`.
- **Root cause:** The writer split on `\n`, matched lines with `\r` attached, and replaced the whole `enabled = [...]` span.
- **Fix:** Splice only the changed items by byte offset, copy the neighbouring line ending, match headers with `\r` removed, and refuse layouts that cannot be edited in place.
- **Lesson:** Change the smallest unit the request names, by byte offset, and assert exact bytes rather than `toContain`.
- **Tags:** review, configuration, toml, crlf

### L247 · 2026-10-30 · floating-core #23 · review
- **Failure:** The CP23 viewer tests still passed when open-card state was rebuilt on every render, when the current card reopened on every poll, when other cards closed on advance, and when the banner-link click handler was removed.
- **Root cause:** No test changed the person-controlled open state before a poll, and the fake page never returned `[data-go]` links, so the click handler never ran.
- **Fix:** Tests open and close cards before polls and assert that state survives; the fake page wires banner links and the click test asserts the card opens and scrolls.
- **Lesson:** Before a poll, change the state the person controls, then assert it survives; prove each test with the mutation it guards against.
- **Tags:** review, tests, viewer, mutation

### L248 · 2026-10-30 · floating-core #24 · review
- **Failure:** `[git] base = "origin/main"` let pushes to `main` through; `rm --force` required a base it never used; a broken config was reported as "no base"; commit identity ignored `author.*`, `committer.*` and `EMAIL`.
- **Root cause:** The configured base was never normalised, the base was resolved before the branch that needs it, every read error collapsed into absence, and identity precedence was re-implemented instead of asked from Git.
- **Fix:** Normalise the base at the one function every consumer reads, resolve it only for the merged check, report the parse error with its file, and take identity from `git var GIT_AUTHOR_IDENT`/`GIT_COMMITTER_IDENT`.
- **Lesson:** Normalise a value where every consumer reads it, resolve it only where it is used, and let the tool decide its own precedence.
- **Tags:** review, git, push, identity, fail-closed

### L249 · 2026-10-30 · floating-core #24 · behavior
- **Failure:** Phase 3 security audit: automatic receipt retention followed a committed `.ai-engineering/receipts` symlink and could delete old files outside the repository, with a repo-supplied `0d` TTL widening it; the checkpoint write guard matched path text only.
- **Root cause:** Retention and receipt writes used plain paths and any file name, and the guard judged spelling instead of where a path lands.
- **Fix:** Refuse linked or escaping receipts folders, delete only writer-produced names bound to the checked folder, clamp TTL to one day, and deny checkpoint writes by resolved identity, including after `cd`.
- **Lesson:** An automatic cleanup on repo-supplied paths must prove the folder is the repo's own before it lists anything, and a write guard must judge where a path lands, not how it is spelled.
- **Tags:** behavior, security, symlink, cleanup, receipts, guard

### L250 · 2026-10-30 · floating-core #24 · review
- **Failure:** Receipt retention changed the host process's working directory on every tool call and could throw when that directory was deleted; the checkpoint guard blocked `json.tool <checkpoint> > /dev/null`.
- **Root cause:** Retention reused the directory-changing helper built for CLI commands, its daily claim sat outside the `try`, and the guard treated any `>` as a write.
- **Fix:** Retention uses a path-checked helper that never changes directory and returns "did nothing" on any error; the guard judges each command part and ignores output sent to `/dev/null` or another stream.
- **Lesson:** Code the chain runs inside a host must never change that host's working directory, and a write guard judges where output lands, not whether `>` appears.
- **Tags:** review, chain, host, guard, receipts

### L251 · 2026-10-30 · floating-core #24 · review
- **Failure:** The `python3 -m json.tool` read exception let `json.tool - <checkpoint>` through, which overwrote the checkpoint from stdin.
- **Root cause:** The exception treated every word starting with `-` as an option, so the stdin operand `-` was skipped and the real output operand looked like the only input.
- **Fix:** Count `-` as an operand, honour `--`, skip option values, and allow json.tool only with exactly one operand that is the checkpoint file.
- **Lesson:** An exception to a write guard must parse the tool's real argument syntax; `-` is an operand, not an option.
- **Tags:** review, guard, security, parsing

### L252 · 2026-11-06 · production-readiness #1 · review
- **Failure:** Launcher tests ran the checkout's own launcher, so after `bun run build` the missing-Bun refusal test got exit 0; staged coverage for dist preference and dev-checkout detection was lost.
- **Root cause:** The rewritten tests ran the checkout's own launcher, so the result depended on whether `dist/` existed rather than on what the launcher does.
- **Fix:** Each case stages its own launcher copy under `os.tmpdir()` with exactly the files it is about; the Windows smoke runs the real installed shims.
- **Lesson:** A launcher test must control everything next to the launcher, so stage it outside the repo instead of trusting the checkout's state.
- **Tags:** review, launcher, tests, isolation

### L253 · 2026-11-06 · production-readiness #1 · review
- **Failure:** Dev-checkout and dist-ordering launcher tests ran only under node, so mutating `isDevCheckout` or the dist-before-source order stayed green.
- **Root cause:** Under node the `scripts/build.ts` marker makes no difference; only the bun shebang path reaches that branch.
- **Fix:** An "under bun" group runs each staged launcher with a fake bun on PATH and a stand-in `src/cli.ts`, each case printing its own line; the manifest spec reuses the smoke's Windows-aware command runner.
- **Lesson:** Run a launcher test under the runtime its shebang names; a branch only that runtime reaches is untested otherwise.
- **Tags:** review, launcher, tests, mutation

### L254 · 2026-11-06 · production-readiness #2 · behavior
- **Failure:** The full suite failed `generated-payload`: the committed chain bundle no longer matched its source.
- **Root cause:** The retention change touched `src/receipts.ts` and `src/shared-project-fs.ts`, which the chain bundle embeds; the implementer ran only targeted suites.
- **Fix:** Regenerate with `bun scripts/gen-assets.ts`.
- **Lesson:** Regenerate the committed bundle after any change to code the chain imports, not only chain sources (repeats L146).
- **Tags:** behavior, bundle, generated

### L255 · 2026-11-06 · production-readiness #2 · behavior
- **Failure:** On ubuntu CI ~70 tests timed out at 5 s with "killed 1 dangling process"; the same SHA passed in another job.
- **Root cause:** On Linux, Bun before 1.4.4 can miss a `spawnSync` child's exit if garbage collection runs during the wait (oven-sh/bun#47257).
- **Fix:** Pin Bun 1.4.4 in every workflow and the CI template; the test preload refuses older Bun on Linux.
- **Lesson:** When dangling-process timeouts hit one OS and come and go on the same code, check the runtime's issue tracker before blaming the tests.
- **Tags:** behavior, ci, bun, linux

### L256 · 2026-11-06 · production-readiness #2 · behavior
- **Failure:** On Windows ~50 git-backed tests reported "not inside a git repository"; others compared `RUNNER~1` short names with git's long paths.
- **Root cause:** Isolated git calls pointed the global and system config at `os.devNull` (`\\.\nul`), which Git for Windows cannot open; Bun's `realpathSync` keeps 8.3 short names.
- **Fix:** Hand git the literal `/dev/null`; canonicalize with `realpathSync.native` wherever a path is compared with git output.
- **Lesson:** Hand git `/dev/null`, never `os.devNull`; compare paths with git only after native canonicalization.
- **Tags:** behavior, windows, git, paths

### L257 · 2026-11-06 · production-readiness #2 · behavior
- **Failure:** On Windows every chain hook allowed (exit 0) and self-protect let writes to governed files through.
- **Root cause:** `await Bun.stdin.text()` in a floating `main()` does not hold the event loop on Windows (oven-sh/bun#41850), so the chain exited before reading; self-protect matched governed names with `/`-only regexes against native `\` paths.
- **Fix:** Read stdin through the `process.stdin` stream; convert paths to `/` form before matching and split canonicalization on `sep`.
- **Lesson:** An early exit 0 in a hook is an allow — payload reads must hold the event loop, and every path match must be separator-agnostic.
- **Tags:** behavior, windows, security, fail-open, guards

### L258 · 2026-11-06 · production-readiness #2 · behavior
- **Failure:** Windows-only failures in wrap, npm helpers, notice/doctor/token-budget and lock-security tests.
- **Root cause:** Product code ran commands through `/bin/sh` and quoted a bare `"npm"`; tests used shell-script stand-ins, `:` PATH joins, `relative()` paths inside TOML keys (`\v` escape) and POSIX symlink text.
- **Fix:** Windows-aware fake commands, a compiled gitleaks shim and a git recorder; wrap uses `sh` from PATH with an honest 127; unquoted npm; explicit `/` in TOML and link text; POSIX-only properties skip on win32 with a reason.
- **Lesson:** A test must build its own premise with platform-neutral stand-ins; never rely on `/bin/sh`, `:` or the CI checkout's git state.
- **Tags:** behavior, windows, tests, fixtures

### L259 · 2026-11-06 · production-readiness #2 · behavior
- **Failure:** On Windows self-protect took 22 s on URLs in shell commands; two request-changes cases failed deterministically.
- **Root cause:** A `//host/...` fragment resolves to a network share on Windows, so canonicalisation opened a connection per URL (sending the machine's login credentials); the transaction folder repeated the slug and crossed the 260-character path limit.
- **Fix:** Judge network paths by their text and never open them; name the folder `.ai-eng-changes-<uuid>`.
- **Lesson:** Never let a guard touch a `//host` path on Windows, and keep scratch paths short.
- **Tags:** behavior, windows, security, paths

### L260 · 2026-11-06 · production-readiness #2 · behavior
- **Failure:** CI `doctor` failed "machine carrier ~/.claude/settings.json missing → ai-eng update"; `update --yes` and `init` left it missing ("unavailable on this platform") on every OS.
- **Root cause:** The fail-closed rule for machine settings (L226) refused every change, including creating a missing file, so no command could install the claude, codex or copilot carriers.
- **Fix:** Create a missing settings file with an exclusive, no-follow open inside the validated folder and record its identity; replacing or removing an existing file stays refused.
- **Lesson:** Fail closed on mutations you cannot bind to a file's identity; an exclusive create can be bound, and refusing it turns the remedy into a no-op.
- **Tags:** behavior, carriers, fail-closed

### L261 · 2026-11-06 · production-readiness #2 · behavior
- **Failure:** The mutation dry run failed `config-command` frame tests (no `┌`) and a `git add` in token-budget.
- **Root cause:** A doctor test replaced `src/ui.ts`'s frame function and never restored it, leaking into later files in one-process runs (Stryker, Linux file order); the Stryker sandbox is an ignored folder, so a plain `git add` is refused.
- **Fix:** Restore stand-ins in `finally`; `git add --force` into the test's private index.
- **Lesson:** A test that replaces a module function must restore it in `finally` — file order differs by OS and runner.
- **Tags:** behavior, tests, isolation, mutation

### L262 · 2026-11-06 · production-readiness #2 · review
- **Failure:** wrap reported a test run with more than ~1 MiB of output as "could not start" (127) and dropped its output, receipt and log.
- **Root cause:** The Windows fix treated every spawn error except a timeout as "never started"; ENOBUFS also stops a child that did run.
- **Fix:** Return 127 only when the spawn has no pid; on ENOBUFS print what was captured, record the receipt and log, exit 1.
- **Lesson:** A spawn error does not mean the command never ran — check the pid before throwing away a run's evidence.
- **Tags:** review, wrap, evidence

### L263 · 2026-11-06 · production-readiness #2 · review
- **Failure:** Mutation testing exposed four guard gaps: `git 2>/dev/null commit --no-verify` allowed; `echo x 2>/etc/foo` scored as a workspace write; a BigInt or cyclic payload crashed the chain instead of denying; a spoken-secret label quoted part of an earlier value.
- **Root cause:** Guards parsed command words, not what the shell does (redirect targets kept as arguments, `..` unresolved); fingerprinting ran `JSON.stringify` outside any try; the label reached back into value text.
- **Fix:** Drop redirect operators with their targets before parsing; one redirect parser for policy and `..` resolved against cwd; fingerprint failure denies with a receipt; key words matching a value are dropped from labels.
- **Lesson:** A surviving mutant in a guard is a question about a real input — answer it with that input before calling the mutant equivalent.
- **Tags:** review, guards, security, mutation

### L264 · 2026-11-06 · production-readiness #2 · behavior
- **Failure:** `chain-dispatch` "wrap rewrites a test command" flaked: deny instead of rewrite in some full runs.
- **Root cause:** The test never pointed `AI_ENG_HOME` at a scratch folder, so the loop guard kept history in the real `~/.ai-engineering/cache/loop/` under a fixed session id, across runs and concurrent suites.
- **Fix:** A per-file scratch machine home, restored and deleted in `afterAll`.
- **Lesson:** A test that runs the chain in-process must point `AI_ENG_HOME` at a scratch folder; the hygiene check only sees env and `tests/` folders, not writes into the real home.
- **Tags:** behavior, tests, isolation, flaky

### L265 · 2026-11-06 · production-readiness #2 · review
- **Failure:** The redirect fix let `git commit -m \> --no-verify` through; on Windows `echo x > ~/x/../.ssh/authorized_keys` escaped the protected-home rule.
- **Root cause:** A respelling pass over raw text spaced out an escaped `>` into a real operator; policy resolved `..` only against a home written with `/`, not the Windows home as Git Bash writes it.
- **Fix:** Redirect recognition lives inside the quote/escape-aware lexer; policy maps the Windows home to its Git Bash form before resolving `..`.
- **Lesson:** A respelling pass must follow the same quote and escape rules as the parser that reads its output, and path scoping must use the shell's own spelling of home.
- **Tags:** review, guards, security, windows

### L266 · 2026-11-06 · production-readiness #2 · review
- **Failure:** Round 3 found more parser escapes: ANSI-C quoting hid a clobber redirect onto a git hook; `${x:-> --no-verify}` and `-m {x,--no-verify}` hid skip flags; a quoted word with a space hid a write to `~/.ssh`. A test faking a Windows HOME made Bun write its cache under a relative `C:/` folder in the repo.
- **Root cause:** Each guard special-cased the shell syntax it knew; anything the lexer could not model was read as harmless text. The fake HOME went through `process.env`.
- **Fix:** One quote reader (including ANSI-C) shared by every splitter; constructs the lexer cannot model mark the command unreadable, and every guard denies unreadable text; the home is injected into the resolver.
- **Lesson:** When a lexer meets syntax it cannot model, report "unreadable" in one place so every guard fails closed — never chase variants per guard. Never fake HOME through `process.env` while Bun can write.
- **Tags:** review, guards, security, fail-closed

### L267 · 2026-11-06 · production-readiness #2 · review
- **Failure:** Round 4 found `echo a\ #; git commit -n` treated as a comment, and `git` behind `{`, `!`, `if`, `for`, `command -p`, `env -i`, `nice -n` never judged as git.
- **Root cause:** The lexer decided "comment" from the last character appended (an escaped space counted); no-verify and self-protect each kept a short prefix list without reserved words or prefix options.
- **Fix:** The lexer tracks word starts; one `commandIndex` in `shell.ts` skips reserved words, assignments and prefix commands with their options, used by both guards; every `git` word in a segment is judged.
- **Lesson:** "Which program runs here" must have one answer shared by every guard.
- **Tags:** review, guards, security, parsing
