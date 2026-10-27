# Review thread · floating-core #3 · Add one Git runner and one Git context resolver

## Goal
src/git/run.ts is the single Git runner and resolveContext(cwd) in src/git/context.ts returns root, current branch or detached, linked-worktree flag, base and where the base came from, following the 6.7 order.

## Acceptance
- resolveContext covers checkout, linked worktree, detached HEAD, no remote and explicit base.
- S6: an explicit base wins over the detected one.
- S7: origin/HEAD pointing at develop yields base develop with source remote-head.
- S15: with no remote the base comes from config or the result says ask.
- S16: detached HEAD is reported as detached, never as unknown or as a branch.
- S18: base equal to the current branch yields ask.
- No network access and no literal main in src/git/.

## changed_files
- src/git/run.ts
- src/git/context.ts
- templates/config.toml.tpl
- .ai-engineering/arch.rules.json
- FILEMAP.md
- tests/git-context.spec.ts

## Verify
- `bun test tests/git-context.spec.ts`
- `bun test tests/generated-payload.test.ts`
- `sh -c '! grep -rnE "refs/heads/main|origin/main" src/git'`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`
- `bun test --parallel=1`
