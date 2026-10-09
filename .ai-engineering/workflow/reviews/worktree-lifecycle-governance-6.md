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
