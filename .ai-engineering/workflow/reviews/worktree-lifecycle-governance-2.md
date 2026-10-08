# Checkpoint goal
Report Git-listed feature worktrees and trustworthy lifecycle state from each worktree's own checkpoint, while missing, malformed, legacy or stale state remains unknown and cannot authorize lifecycle actions.

## Acceptance criteria
- Read each lifecycle checkpoint from its matching Git-listed worktree; show dirty, detached, unclassified and likely-overlap evidence without mutation.
- Missing, unreadable, malformed, contradictory or legacy lifecycle data is visibly unknown and grants no approval, merge or removal authority.
- Validate lifecycle shape, gate/approval prerequisites, allowed transitions and reviewed_main freshness while preserving legacy checkpoint-gate behavior.
- Preserve read-only inventory behavior.

## changed_files
- `src/shared-worktree.ts`
- `scripts/checkpoint-gate.py`
- `tests/worktree-lifecycle.spec.ts`
- `tests/test_checkpoint_gate.py`
- `LEARNINGS.md`

## verify
- `bun test tests/worktree-lifecycle.spec.ts`
- `bun test tests/worktree-command.spec.ts`
- `python3 tests/test_checkpoint_gate.py`
- `bun test tests/arch.spec.ts`
- `bun run typecheck`
- `bun run lint`

## Adversarial review — findings resolved

- **F1 · P1 — `scripts/checkpoint-gate.py:225-237, 136-151`; `src/shared-worktree.ts:308-322, 399-408`:** Lifecycle shape checks validate enum values but not the relationship between checkpoint status and gates. A lifecycle in `implementation` can therefore contain an earlier checkpoint marked `passed` with a pending gate; `check_agent` trusts only that status in `unpassed_before` and authorizes the next checkpoint. Inventory also presents this contradictory lifecycle as known. Reject passed checkpoints with incomplete gates at read time, and show them as unknown; add a fixture exercising the Agent guard.
- **F2 · P1 — `scripts/checkpoint-gate.py:132-145`:** `check_agent` selects `<marker-slug>.json` but never verifies `plan["slug"]` matches that slug. A valid approved `other` plan copied to `demo.json` passes lifecycle validation and authorizes `[checkpoint demo#… implement]`, while inventory correctly treats the same file as a mismatch. Bind the gate to the selected checkpoint identity and test the mismatch.
- **F3 · P2 — `scripts/checkpoint-gate.py:314-326`:** A `ready-to-merge` plan can enter `blocked` retaining an approved app review; after local `main` advances, it cannot recover. `blocked → awaiting-app-review` is allowed only when the old review was already pending, while `blocked → ready-to-merge` fails the fresh-`reviewed_main` check. Permit the blocked stale-approval reset to pending review against current main and cover this transition.

## Resolution

- **F1 — fixed:** A passed checkpoint now requires completed gates in lifecycle validation and inventory, and predecessor checks require both passed status and completed gates; lifecycle and legacy Agent cases are covered.
- **F2 — fixed:** Agent markers now require an exact match between marker slug and loaded plan slug; the copied-plan mismatch is covered.
- **F3 — fixed:** A blocked stale app approval can resume only at pending review against current local `main`; carrying approval to ready-to-merge after changing `reviewed_main` is rejected.
- **Verification:** `python3 tests/test_checkpoint_gate.py` and `bun test tests/worktree-lifecycle.spec.ts` passed; `bun run typecheck` and `bun run lint` passed with existing warnings.

## Round 2 follow-up — independent verification

- **VERDICT: FAIL** — F1 remains open; F2 and F3 are resolved.
- **F1 · P1 (open):** `unpassed_before` (checkpoint-gate.py:124–128) compares `id < cid`; legacy plans skip lifecycle shape validation and no guard validates checkpoint IDs. The valid JSON number `1e999` decodes as infinity; a preceding `{id: 1e999, status: "passed", gates: pending}` compares false against #2, so the legacy Agent guard can still authorize #2. Reject non-finite/invalid IDs before predecessor comparisons (lifecycle plans already reject incomplete passed gates).
- **F2 — resolved:** `check_agent` now requires the loaded plan slug to equal the marker slug; separators are excluded by the marker pattern, and the mismatched-plan test covers the bypass.
- **F3 — resolved:** stale blocked approval cannot resume directly to ready-to-merge; it must enter pending app review with `reviewed_main` equal to current local `main`. Old-state validation and transition checks enforce the reset; tests cover stale direct-merge rejection and pending-review recovery.
- **Counts:** 2 resolved, 0 withdrawn, 1 open (F1).

## Round 3 — F1 resolution

- **F1 — resolved:** Checkpoint IDs are now validated as exact positive one-based integers in sequence before lookup, ordering, gate checks, and lifecycle shape/transition checks. This rejects booleans, strings, fractional and non-finite numbers, duplicates, gaps, and out-of-order IDs while leaving valid legacy plans unchanged.
- **Regression:** Valid JSON `1e999` on an incomplete predecessor can no longer authorize checkpoint #2.
- **Verification:** `python3 tests/test_checkpoint_gate.py` passed.
- **Counts:** 3 resolved, 0 withdrawn, 0 open.

## Round 3 follow-up — F1 verification

- **VERDICT: PASS** — IDs are validated as exact sequential positive integers before Agent checkpoint lookup and predecessor comparison, and before plan gate or lifecycle-transition checks. JSON `1e999` is rejected; the legacy incomplete-predecessor and lifecycle-transition regressions pass. F2 slug binding and F3 stale-review reset remain covered and intact.
- **Counts:** 3 resolved, 0 withdrawn, 0 open.
