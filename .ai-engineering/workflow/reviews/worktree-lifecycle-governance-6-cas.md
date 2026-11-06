# Checkpoint goal
Close a human-approved worktree through a normal hook-running merge commit with exact reviewed parents, compare-and-swap publication to local `main`, primary refresh, ancestry proof and safe worktree removal.

## Acceptance criteria
- Bind human app approval to full `reviewed_main` and `reviewed_feature` SHAs.
- Create the merge commit in a temporary detached worktree so repository hooks run; publish only with expected-old `git update-ref` CAS.
- A CAS loser preserves the feature and checkpoint, reports refs, cleans only its temporary worktree and requires renewed sync/review.
- Verify exact merge parents, refresh primary safely, then remove only after approved feature ancestry is proven.
- Do not write lifecycle `complete` inside a worktree that is removed; no unapproved sibling/remote/force/custom lock.

## changed_files
- `src/shared-worktree.ts`
- `src/commands/worktree.ts`
- `scripts/checkpoint-gate.py`
- `skills/ai-orchestrator/SKILL.md`
- `tests/test_checkpoint_gate.py`
- `tests/skills.spec.ts`
- `tests/worktree-lifecycle.spec.ts`
- `tests/worktree-command.spec.ts`
- `tests/git-cleanup-pass.spec.ts`
- `tests/workflow-handoff.spec.ts`
- `README.md`
- `CONTRIBUTING.md`
- `docs/blueprint.html`
- `CHANGELOG.md`
- `FILEMAP.md`
- `LEARNINGS.md`
- `.ai-engineering/workflow/checkpoints/worktree-lifecycle-governance.json`
- `.ai-engineering/workflow/test-plans/worktree-lifecycle-governance.json`

## verify
- `bun test ./tests/worktree-lifecycle.spec.ts`
- `bun test ./tests/worktree-command.spec.ts`
- `bun test ./tests/skills.spec.ts`
- `bun test ./tests/git-cleanup-pass.spec.ts`
- `bun test ./tests/workflow-handoff.spec.ts`
- `python3 tests/test_checkpoint_gate.py`
- `bun scripts/gen-assets.ts`
- `bun test ./tests/embed-canon.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun test`
- `bun test ./tests/arch.spec.ts`

## Adversarial review — FAIL

- **Counts:** resolved 0; withdrawn 0; open 2.
- **F1 · High · The prescribed approval write makes a tracked checkpoint unmergeable.** `skills/ai-orchestrator/SKILL.md:46,230` stages the checkpoint and then edits it after capturing `reviewed_feature`. `mergeReadyFeature` (`src/shared-worktree.ts:726-28,778`) requires a clean feature worktree and `reviewed_feature == HEAD`; the checkpoint edit dirties a tracked file, while committing it advances `HEAD` and makes the saved SHA stale. The real-Git merge fixtures mask this by adding the checkpoint glob to `.git/info/exclude` (`tests/worktree-command.spec.ts:267-272`). Decouple approval metadata from the reviewed commit or allow only this exact post-tip checkpoint edit, then add a tracked-checkpoint close test.
- **F2 · Medium · Successful close silently drops ignored feature data.** Feature cleanliness ignores Git-ignored files; `worktreeRm` reports the ignored paths it deletes (or that it could not read them), but `removeMergedFeature` discards `removed.out` and returns generic success (`src/shared-worktree.ts:980-1006,1372-1383`). A ready feature containing an ignored local file can therefore lose it without warning. Refuse removal when ignored content is present/unreadable, or propagate an explicit warning and pin that close behavior in a real-Git test.
- **Verified:** normal temporary-worktree hooks and exact parents; expected-old CAS refusal/race; one winner under concurrent CAS; retry after refresh/removal obstruction; merge-failure cleanup and feature/checkpoint preservation; exact ancestry before non-force removal; lifecycle rejects `complete`; approval/handoff order and public docs otherwise align.
- **Changed files:** this review thread only; no code or tests edited.
