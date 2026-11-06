# Checkpoint goal
Serialize the human-approved feature merge into the current local `main`, ensure the merge is based on exactly the reviewed SHA, re-review if `main` moved, and remove the feature only after merge ancestry is verified.

## Acceptance criteria
- Require `HEAD == reviewed_main` and a clean primary checkout; stage only `feat/<slug>` with `git merge --no-commit --no-ff`.
- Recheck the ref before commit, use Git-native merge/index/ref protection instead of a custom lock, and abort/preserve on stale state or contention.
- Verify first parent equals reviewed_main and feature ancestry before safe non-force `ai-eng worktree rm`.
- Never incorporate unapproved siblings, force, fetch, or delete on uncertain state; mark complete only after verified merge/removal.

## changed_files
- `skills/ai-orchestrator/SKILL.md`
- `scripts/checkpoint-gate.py`
- `tests/test_checkpoint_gate.py`
- `tests/skills.spec.ts`
- `tests/worktree-lifecycle.spec.ts`

## verify
- `bun test ./tests/worktree-lifecycle.spec.ts`
- `bun test ./tests/worktree-command.spec.ts`
- `bun test ./tests/skills.spec.ts`
- `bun test ./tests/workflow-handoff.spec.ts`
- `python3 tests/test_checkpoint_gate.py`
- `bun scripts/gen-assets.ts`
- `bun test ./tests/embed-canon.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun test`
- `bun test ./tests/arch.spec.ts`

## Adversarial review

**VERDICT: FAIL — 3 findings (3 P1).**

- **F1 · P1 — `scripts/checkpoint-gate.py:224-256`; `tests/test_checkpoint_gate.py:647-660`.** `verified_merge` accepts `complete` while checked out on `feat/<slug>` and only checks that this `HEAD` is an ancestor of some reviewed-main merge. U28 explicitly attempts the complete write while the feature worktree and branch still exist, then removes them afterward. Thus completion does not require verified removal; the primary-checkout path also checks absence of a branch-attached worktree, not absence of the target worktree path if detached. Require completion from the primary `main` only, and verify the exact feature worktree path and branch are gone before acceptance; exercise both pre-removal refusal and post-removal success.
- **F2 · P1 — `scripts/checkpoint-gate.py:243-256`.** After removal, the primary-checkout shortcut accepts any two-parent first-parent merge whose first parent equals `reviewed_main`; it never binds the second parent to the approved feature tip. An unrelated sibling merged from that same reviewed SHA can therefore satisfy this checkpoint's merge proof. Persist the captured approved feature SHA through removal and require it as the merge's second parent (plus ancestry); test a real Git fixture with the wrong feature parent.
- **F3 · P1 — `skills/ai-orchestrator/SKILL.md:228-230`; `tests/worktree-lifecycle.spec.ts:732-790`.** The final `HEAD`/`main` read and `git commit` are separate operations, so Git's ref lock does not cover their gap. A real Git probe moved `refs/heads/main` after `merge --no-commit` but before `git commit`; commit succeeded with the moved SHA as first parent. If that movement lands after the final read, the post-commit check is too late and abort cannot restore the pre-merge state. Publish with a Git-native expected-old ref transaction tied to `reviewed_main` (no custom lock), and add a controlled test that moves main in this exact gap and proves no commit lands.

**Changed files reviewed:** `skills/ai-orchestrator/SKILL.md`, `scripts/checkpoint-gate.py`, `tests/test_checkpoint_gate.py`, `tests/skills.spec.ts`, `tests/worktree-lifecycle.spec.ts`. No code or tests edited.

## Debate mode — round 1 (2026-10-09)

**VERDICT: FAIL.** Counts: resolved 3; withdrawn 1; open 2.

- **Prior findings:** The old F1 completion-after-removal requirement is withdrawn because the approved design now explicitly forbids a stored `complete` phase. Old F2's unrelated-parent concern is resolved by exact first- and second-parent verification. Old F3's commit/ref race is resolved by detached merge preparation and expected-old `update-ref` CAS. The reviewed-shas artifact's tracked-checkpoint F1 is resolved: the current fixture commits the checkpoint as a tracked file and the command validates the checkpoint-only descendants.
- **F4 · High — approval commits can change the approved checkpoint plan, not just lifecycle metadata.** `scripts/checkpoint-gate.py:186,638-665` snapshots only each checkpoint's status and gate states; the lifecycle check does not freeze the other plan fields. `src/shared-worktree.ts:709-765` likewise validates the descendant commit's changed path and lifecycle/gates, but not that the checkpoint content outside `lifecycle` matches the reviewed plan. A checkpoint-only descendant can therefore change tasks, acceptance details, or file scope after gates and human review while remaining mergeable. Freeze the approved plan payload (or compare all non-lifecycle content across the reviewed tip and descendants) and test a changed non-lifecycle field at both gate and merge boundaries.
- **F5 · Medium — close hides the ignored-data deletion warning.** `worktreeRm` reports ignored paths or an unreadable ignored-path scan (`src/shared-worktree.ts:1452-1478`), but `removeMergedFeature` discards `removed.out` and returns generic success (`src/shared-worktree.ts:1049-1088`). `ai-eng worktree merge` can therefore remove ignored local files without warning. Refuse when ignored content is present/unreadable or propagate the warning, with a real-Git merge test. This is the unresolved ignored-content finding from `worktree-lifecycle-governance-6-reviewed-shas.md`.
- **Verified:** The checkpoint-gate test command passed; the worktree-command test process exited successfully. The exact reviewed parents, expected-old main CAS, stale-main refusal/retry path, feature preservation on failure, and non-force removal checks are present. No production code or tests edited.
- **Files changed:** `.ai-engineering/workflow/reviews/worktree-lifecycle-governance-6.md` only.


## Debate mode — round 2 (2026-10-09)

**VERDICT: FAIL.** Counts: resolved 1; withdrawn 0; arbitrated 0; open 1.

- **Resolved F4:** Plan scope is now compared while entering app review and ready-to-merge, allowing only lifecycle plus checkpoint/gate runtime metadata. Merge-time `reviewedFeatureChainProblem` independently loads the plan at `reviewed_feature` and compares every checkpoint-only descendant, so direct Git commits cannot bypass the gate. Tests cover task/acceptance/files mutations at the gate, runtime-field changes, and a changed-plan metadata commit at merge; the latter preserves main and the feature.
- **Resolved U31 / exact-SHA and metadata-chain checks:** U31 now commits an implementation checkpoint before recording `reviewed_feature`; its real CLI merge test confirms the checkpoint exists at that SHA, the two subsequent commits touch only that checkpoint, and the merge has exact reviewed parents. The review/approval SHA tests, post-review code rejection, CAS races, stale-review invalidation, failed-hook preservation and interrupted-cleanup retry all passed.
- **F5 remains open (Medium):** The normal success path forwards `removed.out`, but cleanup warnings still disappear on post-removal failure. `removeMergedFeature` returns an empty `out` if its post-removal Git inventory/ref/path check fails after `worktreeRm` has already deleted the worktree. Also, `worktreeRm` returns on branch-delete failure before it formats its ignored-path/unreadable-scan note, although the worktree removal already happened. In either case the caller gets an error but not the warning about user data that was dropped. Preserve the scan warning in every outcome after scanning/destructive cleanup, and cover a removal-success/post-verification-failure case (plus branch-delete failure if separately handled).
- **Verification:** `bun test tests/worktree-lifecycle.spec.ts tests/worktree-command.spec.ts tests/embed-canon.spec.ts` — 88 passed; `python3 tests/test_checkpoint_gate.py` — all checks passed; `bun test tests/skills.spec.ts` — 26 passed. UI remains n/a. No code or tests edited.
- **Files changed:** `.ai-engineering/workflow/reviews/worktree-lifecycle-governance-6.md` only.


## Debate mode — round 3 (2026-10-09)

**VERDICT: PASS.** Counts: resolved 1; open 0.

- **Resolved F5:** Ignored-path and unreadable-scan warnings now survive worktree-removal failure, branch-delete failure, and failed post-removal verification. The merge caller forwards removal output on errors, and messages distinguish confirmed removal from uncertain state without claiming a removed worktree was preserved.
- **Verified:** Real-Git cases cover a failed removal with ignored paths, branch-delete failure with an unreadable scan after the worktree is gone, normal merged cleanup, and post-removal inventory failure after the worktree and branch were removed. F4's plan freeze and U31's tracked-checkpoint fixture remain intact.
- **Verification:** `bun test ./tests/worktree-command.spec.ts` — 62 passed; `bun run typecheck` and `bun run lint` exited successfully.
- **Files changed:** `src/shared-worktree.ts`, `tests/worktree-command.spec.ts`, `LEARNINGS.md`, and this review thread.

## Critic ruling — round 3 (2026-10-09)

**VERDICT: PASS.** Counts this round: resolved 1; withdrawn 0; arbitrated 0; open 0.

- **F5 resolved:** The removal path now carries the ignored-scan result through successful cleanup, failed worktree removal, failed branch deletion, and post-removal verification errors. Each error distinguishes what is known about the worktree path and branch, while unreadable scans explicitly state that data may have been dropped unseen or that the result is unknown. `worktreeMerge` forwards the error/output, and the worktree command writes both streams to the caller. Real-Git tests exercise each failure path; a refusal reports found ignored files without claiming they were deleted.
- **F4 remains resolved:** Gate transitions compare the reviewed plan payload while permitting only the intended lifecycle and gate runtime fields. Merge independently compares that payload from the full `reviewed_feature` commit against every descendant metadata commit and refuses changed scope before publishing. The direct-Git bypass test preserves local main and the feature.
- **U31 remains resolved:** The real-Git fixture commits the implementation checkpoint before capturing `reviewed_feature`; subsequent approval commits touch only that checkpoint. The test verifies the exact merge parents and successful removal.
- **Attack/verification:** `bun test ./tests/worktree-command.spec.ts ./tests/worktree-lifecycle.spec.ts` — 78 pass, 0 fail; `python3 tests/test_checkpoint_gate.py` — all checks pass. The recorded complete 12-command Behavior gate (attempt 31) also passes. No new finding; UI n/a. No production code or tests edited.
- **Files changed by this review:** `.ai-engineering/workflow/reviews/worktree-lifecycle-governance-6.md` only.
