# Checkpoint 2 · Prove the GitHub Markdown contract statically

Goal: A deterministic static contract test protects the GitHub provider instructions and existing report template without inventing an executable provider runtime.

Acceptance:
- The check verifies separate complete GitHub issue/PR inventories and pagination, per-item analysis, evidence, ranking, read-only rules, and existing report-template coverage.
- The check verifies no active remote mutation commands are introduced.
- The check does not execute a synthetic provider run.

Changed files:
- `tests/triage-github.spec.ts`
- `skills/ai-triage/references/github.md`

Verify:
- `bun test tests/triage-github.spec.ts`

## Debate · round 1
VERDICT: FAIL
- F1 · P1 · `tests/triage-github.spec.ts:72-75` — The mutation regex misses write forms such as `gh api --method PATCH` and `gh repo edit`; an active remote mutation can be added while the negative assertion still passes.
- F2 · P2 · `tests/triage-github.spec.ts:15-25` — Inventory command literals and the generic paging sentence are asserted independently, so pagination can stop applying to one inventory without failing this test.
- F3 · P2 · `tests/triage-github.spec.ts:30-44` — Field-label presence proves a template exists, not that instructions require one analysis record for every fetched issue/PR; the per-item acceptance can be removed while labels remain.
- Verify: `bun test tests/triage-github.spec.ts` passes (3 tests).

### Response · round 1
- F1 fixed: the mutation detector covers `gh api -X`, `gh api --method`, and `gh repo edit`; sentinel assertions keep those forms covered.
- F2 fixed: the test scopes both separate inventory commands, pagination, and fetched-count requirements to the same inventory step.
- F3 fixed: the test requires one returned analysis block per item and the block contract to specify one shape per item.
- Verify: `bun test tests/triage-github.spec.ts` — 3 passed, 0 failed (42 assertions).

### Debate · round 2
VERDICT: FAIL
- F1 · P1 · `tests/triage-github.spec.ts:94-100` — The detector only recognizes explicit `-X`/`--method`; `gh api -f/--raw-field` or `-F/--field` can default to POST, so an active write could pass.
- F2 · P2 · `tests/triage-github.spec.ts:30-32` — The regex checks both list commands precede one generic pagination sentence, not that pagination applies to each; guidance scoped to only one inventory can still pass.
- F3 · RESOLVED — `:51-55` requires an analysis block per item and the fixed block shape per item.

### Response · round 2
- F1 fixed: the static mutation check covers every write verb through both `-X` and `--method`, plus field flags that default to POST.
- F2 fixed: pagination is asserted separately from each issue-list and PR-list command.
- F3 remains resolved; no related assertions were changed.
- Verify: `bun test ./tests/triage-github.spec.ts` — 3 passed, 0 failed (53 assertions).

### Debate · round 3
VERDICT: FAIL
- F1 · P1 · `tests/triage-github.spec.ts:101-115` — The mutation detector still misses active write verbs such as `gh issue reopen` (also `gh issue delete` / `gh pr close`); adding one to the instructions passes the negative assertion.
- F2 · P2 · `tests/triage-github.spec.ts:31-38` — Both slices run from their list command to the end of `inventoryStep`; one pagination sentence after `gh pr list` therefore satisfies both assertions, even if issue pagination guidance is removed.
- F3 · RESOLVED — `:51-62` requires one returned analysis block per item and pins its per-item shape.
- Verify: `bun test ./tests/triage-github.spec.ts` — 3 passed, 0 failed (53 assertions).

### Response · round 3
- F1 fixed: the detector and sentinels cover `gh issue reopen`, other issue/PR write verbs, and API write methods/fields.
- F2 fixed: the test isolates each inventory and requires its own pagination rule and fetched-count agreement; the provider text states each independently.
- F3 remains resolved and untouched.
- Verify: `bun test tests/triage-github.spec.ts` — 3 passed, 0 failed (57 assertions).

### Debate · round 4
VERDICT: FAIL
- F1 · P1 · `tests/triage-github.spec.ts:102-125` — The remote-write detector still omits `gh pr lock` and `gh pr unlock`, which mutate GitHub PR state; adding either active command to the provider instructions passes the negative assertion.
- F2 · RESOLVED — `:18-45` isolates issue and PR command ranges and asserts each range's own pagination and fetched-count instruction; the reference provides both separately.
- F3 · RESOLVED — The per-item block and its shape assertions remain intact.
- Verify: `bun test ./tests/triage-github.spec.ts` — 3 passed, 0 failed (57 assertions).
