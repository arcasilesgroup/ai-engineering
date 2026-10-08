# Checkpoint goal
Use one read-only local preflight before brainstorm and orchestrator work to show current Git worktrees and lifecycle approvals, resume the same slug, pause likely overlap, and preserve unrelated or uncertain work.

## Acceptance criteria
- Both skills use the same `ai-eng worktree list` preflight before new or resumed work.
- Orchestrator Phase 0 resumes the Git-listed path for the same slug or opens a clean feature worktree from local `main`.
- Likely overlap pauses for a human decision; clearly unrelated work can continue; dirty or unknown work is preserved.
- No remote sync, unapproved sibling merge, primary-tree plan creation or checkpoint copying is introduced.

## changed_files
- `skills/ai-brainstorm/SKILL.md`
- `skills/ai-orchestrator/SKILL.md`
- `tests/skills.spec.ts`
- `tests/workflow-handoff.spec.ts`
- `tests/worktree-lifecycle.spec.ts`
- `LEARNINGS.md`

## verify
- `bun test tests/skills.spec.ts`
- `bun test tests/workflow-handoff.spec.ts`
- `bun test tests/worktree-lifecycle.spec.ts`
- `bun scripts/gen-assets.ts`
- `bun test tests/embed-canon.spec.ts`
- `bun test tests/arch.spec.ts`
- `bun run typecheck`
- `bun run lint`

## Adversarial review

- **F1 · P2 · closed:** Added U17 to check the same-slug status guard, preservation and stop conditions, and that creation remains on the unlisted-slug path. It also rejects rebase/remove commands in the guarded branch.
- **F2 · P2 · closed:** Added U18 to check that both preflights report pending human approvals after the shared listing and before proceeding to creation.
