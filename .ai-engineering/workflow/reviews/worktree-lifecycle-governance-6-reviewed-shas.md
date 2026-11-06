# Checkpoint goal
Bind human app-review approval to a reviewed code commit, permit only checkpoint-only metadata commits afterward, then atomically publish a normal hook-running merge whose exact parents and feature ancestry are verified before safe worktree removal.

## Acceptance criteria
- Capture `reviewed_main` and `reviewed_feature` after synchronization/gates; commit the pending app-review lifecycle checkpoint alone.
- After human approval, commit the approved app-review checkpoint alone with both reviewed SHAs unchanged.
- Refuse any code or other-path commit after reviewed_feature; allow only valid checkpoint-only lifecycle commits.
- Create a normal merge commit in a temporary detached worktree; verify first parent is reviewed_main and second parent is the current approved feature tip.
- Publish local main only through expected-old CAS. On CAS loss, preserve feature and checkpoint, report refs, then invalidate approval in a checkpoint-only commit before resync/review.
- Refresh primary safely, verify ancestry, remove the feature worktree/branch non-force, and never store an active `complete` phase.

## changed_files
- `src/shared-worktree.ts`
- `src/commands/worktree.ts`
- `scripts/checkpoint-gate.py`
- `skills/ai-orchestrator/SKILL.md`
- `tests/test_checkpoint_gate.py`
- `tests/skills.spec.ts`
- `tests/git-cleanup-pass.spec.ts`
- `tests/worktree-lifecycle.spec.ts`
- `tests/worktree-command.spec.ts`
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
