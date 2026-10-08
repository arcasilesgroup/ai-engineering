# Checkpoint goal
Persist the plan-approval phase in the selected feature worktree and block implementation dispatch until the existing Phase 1 human approval is received.

## Acceptance criteria
- After Phase 0, initialize the checkpoint in that feature worktree with `awaiting-plan-approval`, pending plan approval, app review not started and no reviewed main.
- Keep the existing human plan-review stop; only after the human approves may lifecycle transition to `implementation` and implementation dispatch begin.
- Validate lifecycle shape, approval-state ordering and prerequisite gates without breaking legacy plans.
- Preserve the distinction: the local gate validates state/order; the orchestrator records approval only after the human response.

## changed_files
- `skills/ai-orchestrator/SKILL.md`
- `scripts/checkpoint-gate.py`
- `tests/test_checkpoint_gate.py`
- `tests/skills.spec.ts`
- `tests/workflow-handoff.spec.ts`
- `LEARNINGS.md`
- `.ai-engineering/workflow/test-plans/worktree-lifecycle-governance.json`

## verify
- `python3 tests/test_checkpoint_gate.py`
- `bun test tests/skills.spec.ts`
- `bun test tests/workflow-handoff.spec.ts`
- `bun scripts/gen-assets.ts`
- `bun test tests/embed-canon.spec.ts`
- `bun test tests/arch.spec.ts`
- `bun run typecheck`
- `bun run lint`

## Adversarial review

### F1 — Lifecycle initialization can still occur in the primary checkout

`check_plan` requires the selected feature worktree only when `not had_plan`, where `had_plan` means merely that the old JSON already has a checkpoint list. A legacy checkpoint plan already in the primary checkout therefore passes its first transition to `awaiting-plan-approval` at the matching primary-tree path. `tests/test_checkpoint_gate.py` currently blesses this exact case as “valid initial lifecycle shape” before testing fresh worktree creation. This violates the feature-worktree-only initialization rule even though the later approval handoff remains required. Apply the worktree check whenever a plan first gains lifecycle state, irrespective of whether its legacy checkpoint list already existed, and add a regression for the legacy plan in the primary checkout.

### Round 2 follow-up — F1

- **Resolved:** `check_plan` now applies the worktree check whenever lifecycle state is first added, including legacy checkpoint plans. Regression coverage denies primary-checkout initialization and accepts initialization in the matching Git-listed feature worktree (`tests/test_checkpoint_gate.py:272-295`). The exact branch/slug and configured-root checks are present; path escapes are rejected by the resolved-path equality and containment checks (`scripts/checkpoint-gate.py:419-497`). Legacy primary-checkout gate writes without lifecycle remain allowed (`tests/test_checkpoint_gate.py:273-276`).
- **Open — canonical-path symlink alias:** `lifecycle_plan_path_error` realpaths both the supplied path and expected path, then accepts equality (`scripts/checkpoint-gate.py:425-435`). A symlink alias resolving to the canonical checkpoint file therefore passes, despite the canonical-path-only requirement; no regression covers this case.
- Gate 1 was rerun; all eight checkpoint 4 commands passed.

### Round 3 follow-up — canonical-path symlink alias

- **Resolved:** Lifecycle initialization now compares the normalized supplied path to the canonical checkpoint path and rejects a symlink in the target or any path component (`scripts/checkpoint-gate.py`). Real Git feature-worktree regressions cover both a symlinked target file and a symlinked checkpoint-directory component (`tests/test_checkpoint_gate.py`).
- Legacy primary-checkout writes without lifecycle and the existing primary/feature, branch, and path-escape checks remain unchanged.

### Round 3 verification — one open finding

- **Open — exact alias-path regression missing:** The implementation rejects an alias path because its normalized target differs from the canonical checkpoint (`scripts/checkpoint-gate.py:445-459`), but the “target-file symlink” test supplies the canonical `selected_path` itself and replaces that file with a symlink (`tests/test_checkpoint_gate.py:303-319`). It does not pass a distinct symlink alias path that resolves to the canonical checkpoint. Add a portable alias-path regression using the existing symlink-availability handling; expect lifecycle initialization through that alias to be denied.
- **Verified:** Initialization is bound to the canonical checkpoint in the matching Git-listed `feat/<slug>` worktree; tests deny primary-checkout initialization, wrong branch/slug, out-of-root/path escape, and symlinked target/component paths. Legacy primary gate writes without lifecycle remain allowed.
