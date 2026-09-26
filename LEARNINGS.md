# Learnings

Accumulated failures and lessons from building features, mostly written by `/ai-orchestrator`. Every planner, implementer, test writer and reviewer reads **Rules** before starting.

- **Log** is append-only: never edit or delete an entry.
- **Rules** is the distilled version. A lesson is promoted here once it has recurred (2 or more log entries) or caused a human-review rejection or a circuit-breaker stop. Each rule cites the entries it came from.

## Rules

<!-- - R1: <imperative rule>. (from L3, L7) -->

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


<!--
### L<n> · YYYY-MM-DD · <feature-slug> #<checkpoint> · <gate: behavior|ui|review|human|circuit-breaker>
- **Failure:** what failed, as the gate reported it
- **Root cause:** why, not just what
- **Fix:** what changed
- **Lesson:** one reusable sentence for next time
- **Tags:** e.g. auth, db, migration, ui, tests, webhooks
-->
