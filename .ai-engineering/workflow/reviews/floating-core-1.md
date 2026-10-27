# Review thread · floating-core #1 · Make the serial suite green, deterministic and quiet on commit

## Goal
The serial suite passes twice in a row, no suite leaves folders under tests/, a green pre-commit prints nothing and never scans receipts, and receipts stay bounded by an automatic daily retention.

## Acceptance
- The test that made the serial suite fail is named with its cause and fixed, or logged in LEARNINGS.md with the reason it is external.
- F7: a green pre-commit prints 0 lines and does not read the receipts folder, even with thousands of receipts present.
- Receipts stay bounded after N writes; retention runs on its own at most once a day, in bounded batches, and never from the git pre-commit hook.
- No suite creates a folder under tests/; environment variables and cwd are restored after every suite that changes them.
- The p95 latency check is `bun run bench`, outside the test gate.
- CI runs `bun test --parallel=1` and actionlint validates platforms.yml.
- `bun test --parallel=1` passes twice in a row.

## changed_files
- .ai-engineering/PRD.html
- .github/workflows/check.yml
- FILEMAP.md
- package.json
- skills/.chain-bundle/ai-eng-chain.ts
- src/chain/mod.ts
- src/commands/doctor.ts
- src/floor/entry.ts
- src/receipts.ts
- scripts/bench-chain.ts
- tests/adversarial/chain.test.ts
- tests/floor-gates.spec.ts
- tests/uninstall-command.spec.ts
- tests/worktree-lifecycle.spec.ts

## Verify
- `grep -qF "bun test --parallel=1" .github/workflows/check.yml`
- `sh -c 'grep actionlint .github/workflows/check.yml | grep -q platforms'`
- `bun test tests/test-hygiene.spec.ts`
- `bun test tests/floor-hooks.spec.ts`
- `bun test tests/receipts-retention.spec.ts`
- `bun test tests/receipts-summary.spec.ts`
- `bun test tests/uninstall-command.spec.ts`
- `bun test tests/worktree-lifecycle.spec.ts`
- `bun test tests/doctor-command.spec.ts`
- `bun test tests/adversarial/chain.test.ts`
- `bun run bench`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`
- `bun test --parallel=1`
- `bun test --parallel=1`


## Round 1 · critic

Verify re-run (r1): typecheck 0, lint 0, the 9 named suites 186/186, `bun run bench` p95 8.14 ms exit 0, `bun test --parallel=1` 1411/1411 (126 s). Green; the findings below are behaviour and coverage, not failing commands.

## F1 · BLOCKER · fixed
**Where:** src/receipts.ts:348 and src/receipts.ts:355 (called from src/chain/mod.ts:262)
**Critic (r1):** The daily pass is bounded only in deletions, not in reads. Before it knows whether anything is stale it runs `summarizeReceipts(receipts)` (opens every receipt inside the 40-day name window) and `lstat`s every entry in the folder. On the brainstorm's own numbers (F7: 239,991 receipts; 36k opens = 5 s) the first tool call of each day now blocks the PreToolUse hook for tens of seconds to minutes — F7's cost is moved from the pre-commit into the guard hot path, inside a harness hook timeout, against the 50 ms budget. → Make the pass bounded in work, not just in unlinks: select stale candidates by the timestamped filename (sorted, cut at the TTL, take the first `maxDeletes`) without stat-ing the whole folder, and only tally the receipts actually being deleted (or skip the summary entirely when the batch is empty) instead of a full `summarizeReceipts`. Add a test that seeds thousands of in-window receipts and asserts the pass opens at most O(batch) files (spy on readFileSync/lstatSync, as F7's test does for readdir).
**Fixer (r1):** fixed — the pass no longer calls `summarizeReceipts` nor stats the whole folder. `collectReceipts` (src/receipts.ts:369) lists the folder once and picks stale candidates by the writer's timestamp in the name (src/receipts.ts:378; only a name without that stamp falls back to `lstat` mtime), sorts, takes the first `maxDeletes`, and only those are `lstat`-ed (file check), read and unlinked; the summary is folded from exactly the receipts deleted (src/receipts.ts:410, tallied after a successful unlink) and skipped when nothing was deleted. `summary.json`'s daily series is now additive (each receipt counted once, on the pass that deletes it); `total` is the store size from the listing, no opens. New case tests/receipts-retention.spec.ts:225 seeds 3000 in-window + 5 stale receipts and spies `readFileSync`/`lstatSync`/`statSync`/`openSync`: the receipts touched are exactly the 5 stale ones (with a positive control); it fails on the previous receipts.ts. · verify: `bun test tests/receipts-retention.spec.ts` ✓ 8/8, `bun run bench` ✓ p95 4.93 ms

## F2 · MAJOR · fixed
**Where:** src/receipts.ts:317 and src/receipts.ts:395-401
**Critic (r1):** "Receipts stay bounded" fails whenever the chain writes more than 500 receipts a day: one pass per UTC day × 500 deletions = 500/day drained, while the store F7 describes grew to ~240k (well over 500/day). The backlog never shrinks and the folder grows without limit — the acceptance criterion is not met, and the test (40 receipts, then 525 over two days) never models a write rate above the batch. → When a pass hits `maxDeletes`, do not mark the day done (e.g. stamp only when `deleted < batch`), so later calls keep draining in bounded batches until the backlog is clear, then fall back to once a day. Add a case: stale backlog of 3×batch is cleared over successive same-day calls, and a fourth same-day call does no scan.
**Fixer (r1):** fixed — `collectReceipts` reports `hasBacklog` (stale entries left after the batch, src/receipts.ts:421) and `retainReceipts` releases the day's claim when a backlog remains (src/receipts.ts:461), so later same-day calls drain in bounded batches; the day is only closed by a pass that leaves nothing stale. New case tests/receipts-retention.spec.ts:254: 3×batch stale cleared by three same-day calls, a fourth same-day call returns `{ran:false}` and leaves a new stale arrival alone, and the split day sums to 3×batch in summary.json. Fails on the previous receipts.ts. · verify: `bun test tests/receipts-retention.spec.ts` ✓

## F3 · MAJOR · fixed
**Where:** tests/doctor-command.spec.ts:32-33, tests/config-command.spec.ts:31-32, tests/init-command.spec.ts:138-140, tests/spec-command.spec.ts:143-144
**Critic (r1):** Acceptance says env and cwd are restored "after every suite that changes them", and test-hygiene.spec.ts's own header names delete-instead-of-restore as the leak. Only uninstall-command.spec.ts was fixed; these four still `delete` AI_ENG_HOME / PI_CODING_AGENT_DIR / GIT_CONFIG_GLOBAL unconditionally, so any later suite in the same serial process loses the home it started with. doctor-command.spec.ts is in this checkpoint's own files/verify list. The hygiene test probes only uninstall-command, so it cannot catch them (R3/R6: the guard sits where one test pinned one config). → Apply the same snapshot/restore afterEach to the four suites (one shared helper in tests/fixtures rather than a fifth copy), and parametrize the env-restoration case in test-hygiene.spec.ts over every suite that assigns these variables.
**Fixer (r1):** fixed — one helper, tests/fixtures/sandbox-env.ts (`SANDBOX_VARS`, `snapshotSandboxEnv`, `restoreSandboxEnv`), now used by doctor-command, config-command, init-command, spec-command and uninstall-command (its private copy removed). The hygiene case is parametrized over every suite that assigns or deletes one of the three variables, derived from the tree at run time (tests/test-hygiene.spec.ts:82 — 25 suites today), run serially in one child with a preload that Bun evaluates per file, recording the env/cwd each suite found and left (tests/fixtures/env-snapshot.preload.ts, keyed by `Bun.main`); every pair must equal the handed values (tests/test-hygiene.spec.ts:127). Running it surfaced three more leaks, also fixed: spec-lifecycle.test.ts deleted GIT_CONFIG_GLOBAL in afterAll (now restores); adversarial/isolation.test.ts never restored AI_ENG_HOME (now restores) and read the "real" global config before dropping a borrowed GIT_CONFIG_GLOBAL; init-command.spec.ts's sandbox did not own GIT_CONFIG_GLOBAL (tests/init-command.spec.ts:66), so with one inherited its `--yes` test wrote `init.templateDir` into the inherited config. Cost: the serial suite grows ~43 s (126 → 170 s). FILEMAP.md updated. · verify: `bun test tests/test-hygiene.spec.ts` ✓ 2/2

## F4 · MINOR · fixed
**Where:** src/receipts.ts:395-401 and src/receipts.ts:333
**Critic (r1):** The stamp is check-then-write, so parallel tool calls at the first call of a day (routine for agents) both run the pass; both then `writeFileSync` summary.json non-atomically. A torn summary.json is read back as "no prior" on the next merge, dropping the 90-day daily series — the gc's only long-term memory. → Claim the day atomically (open a per-day stamp with the `wx` flag; losers return idle) and write summary.json via temp file + rename.
**Fixer (r1):** fixed — the day is claimed by exclusive create (`openSync(claim, "wx")`, src/receipts.ts:447) of a per-day file in .ai-engineering/cache; losers return idle; earlier days' claims are removed after the pass. summary.json is written to a non-`.json` staging name and `renameSync`-ed into place (src/receipts.ts:354). New case tests/receipts-retention.spec.ts:277: six processes race the first call of a day — exactly one reports `ran:true` with all 40 deleted, and the series counts 40, not more. Fails on the previous receipts.ts. · verify: `bun test tests/receipts-retention.spec.ts` ✓

**Fixer (r1) verify:** `bun run typecheck` exit 0 · `bun run lint` exit 0 · `bun test tests/arch.spec.ts` 22/22 · `bun run bench` p95 4.93 ms · `bun test --parallel=1` 1414/1414 twice (170.6 s, 169.0 s) · chain bundle regenerated with `bun scripts/gen-assets.ts`.
