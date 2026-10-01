# Review · git-worktree-flow #2 — the worktree verb

## Goal
`ai-eng worktree new|rm|list` creates `<repo>.worktrees/<slug>` (canonicalized, root overridden by `[git].worktrees_dir`), cuts an ephemeral branch carrying `branch.<slug>.remote = .` and `merge = refs/heads/main`, refuses a dry refusal on an invalid slug or on an uncommitted pre-worktree artifact, warns without blocking on an overlap, lists the open session worktrees, and removes a worktree plus its branch (pruning a stale entry). `src/cli.ts` only dispatches, the parser is thin, and the logic lives in the `shared` layer.

## Acceptance
1. `new` resolves the root from `[git].worktrees_dir` when present and falls back to `<repo>.worktrees`; the created path is canonical and carries the upstream config.
2. `new` refuses when a pre-worktree artifact (`brainstorm.html`, `spec.html`, `plan.html`) is uncommitted in the invoked repository, whatever shape the dirt has, including a wholly untracked `.ai-engineering/`; the pre-worktree list is its own definition in the shared module, next to the spec-close sweep list it must not borrow.
3. A slug is validated against `^[a-z0-9][a-z0-9._-]*$` before anything is created; a slug with a space or a `/` exits non-zero, creates nothing, and names the reason; a valid kebab-case slug succeeds.
4. A second worktree declaring a file an open worktree already declared warns and does not block.
5. `list` reports the open session worktrees only; `rm` removes the worktree and its branch; no emitted command ever contains `git push`.
6. `src/cli.ts` contains only the dispatch case; the spec-close slot list keeps one definition; `tests/arch.spec.ts` stays green with no change to `.ai-engineering/arch.rules.json`.

## changed_files
- `src/shared-worktree.ts`
- `src/commands/worktree.ts`
- `src/cli.ts`
- `src/shared-verbs.ts`
- `src/spec/index.ts`
- `tests/worktree-command.spec.ts`

## Verify commands
- `bun test tests/worktree-command.spec.ts`
- `bun test tests/spec-command.spec.ts`
- `bun test tests/arch.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun run build`

## Gate history
Behavior attempt 1 FAILED: the refusal never fired when `.ai-engineering/` was wholly untracked (`git status --porcelain` without `-uall`), the refusal borrowed the spec-close sweep list so a dirty `recap.html` blocked a new session, and `list` printed the primary checkout. Fixed in `2282f7ba`; the three cases added in `f098e3d2`. Behavior attempt 2 is the run that opened this thread.
