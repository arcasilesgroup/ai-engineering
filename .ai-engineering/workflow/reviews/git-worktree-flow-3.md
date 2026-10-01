# Review · git-worktree-flow #3 — the orchestrator runs in its own copy

## Goal
`skills/ai-orchestrator/SKILL.md` Phase 0 opens `<repo>.worktrees/<slug>` through `ai-eng worktree new <slug>` instead of creating `feat/<slug>` in the shared tree, the run happens inside that worktree, and the close step becomes: rebase on the local `main` inside the worktree, `git merge --no-ff feat/<slug>` in the primary tree, then worktree and branch cleanup. The shared files are written once by that merge step, and the commit-message table emits only messages this repository's `commit-msg` hook accepts.

## Acceptance
1. Phase 0 no longer creates `feat/<slug>` in the shared tree; it names `ai-eng worktree new <slug>`.
2. The close step rebases on local `main` inside the worktree, merges with `git merge --no-ff`, and cleans up the worktree and branch; it never pushes.
3. The shared files are assigned to the merge step only; `recap.html` is generated on the branch at the app review and arrives with the merge.
4. The `## Lifecycle` block still hands off per `tests/workflow-handoff.spec.ts`.
5. No message the skill emits can be rejected by the `commit-msg` hook: every pattern of its table matches `^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9._/-]+\))?!?: \S`, so `plan`, `gate` and `wip` and the `<slug>#N` scope are gone.

## changed_files
- `skills/ai-orchestrator/SKILL.md`
- `src/assets.ts` (regenerated)

## Verify commands
- `rg -q 'ai-eng worktree new' skills/ai-orchestrator/SKILL.md`
- `! rg -q 'git switch -c feat/' skills/ai-orchestrator/SKILL.md`
- `rg -q 'merge --no-ff' skills/ai-orchestrator/SKILL.md`
- `rg -q 'worktree rm' skills/ai-orchestrator/SKILL.md`
- `! rg -q 'plan\(<slug>|gate\(<slug>|wip\(<slug>' skills/ai-orchestrator/SKILL.md`
- `! rg -q '<slug>#' skills/ai-orchestrator/SKILL.md`
- `bun test tests/workflow-handoff.spec.ts`
- `bun test tests/embed-canon.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun run build`

## Context the reviewer should know
The contract this skill must follow is `AGENTS.md` → `## Git workflow` (checkpoint 1, passed). The verb it now calls is checkpoint 2 (passed). The commit convention it must respect is enforced at `src/floor/index.ts:145`, and this run already lost two attempts to it: the skill's own table named types (`plan`, `gate`, `wip`) and a scope (`<slug>#N`) that the hook rejects.
