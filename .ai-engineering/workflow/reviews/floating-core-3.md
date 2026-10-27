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

## F1 · MAJOR · fixed
**Where:** src/git/context.ts:69 (loadConfig at src/env.ts:131-134)
**Critic (r1):** A `config.toml` that exists but does not parse is read as `{}`, so a declared `[git] base` silently vanishes and the resolver falls through to remote-head. Probed: `[git] base = "release"` plus one broken table header elsewhere in the file → `base: "develop", baseSource: "remote-head"` — the work is aimed at the wrong branch with no signal. R8 says a read that cannot decide denies; P3 says "if it cannot be read, ask". → In `configuredBase`, when the config file exists but loadConfig cannot parse it, fail closed (throw naming the path and the fix, or return ask) instead of answering "no base"; add a case with a malformed config that declares `[git] base` and assert the result is not remote-head.
**Fixer (r1):** fixed — `configuredBase` now reads config.toml through its own strict `readConfig` (src/git/context.ts:74-80, :84-97): absent file → no base; a file that exists but does not read or parse throws `cannot read <path> (...): fix the TOML so it parses, or remove the file`; a non-table `git` also throws (:89-91). Kept out of `loadConfig` because src/env.ts is compiled into the committed chain bundle (tests/generated-payload.test.ts). Cases: tests/git-context.spec.ts:493 (malformed file declaring `[git] base` with origin/HEAD=develop present → throws, never remote-head), :504. · verify: `bun test tests/git-context.spec.ts tests/arch.spec.ts` ✓ · `bun run typecheck` ✓ · `bun run lint` ✓ · `bun test --parallel=1` ✓ (1410 pass)

## F2 · MAJOR · fixed
**Where:** src/git/run.ts:18-22, :26 (used by src/git/context.ts:29-31)
**Critic (r1):** Isolated mode strips config injection but keeps the repository-discovery environment (`GIT_DIR`, `GIT_WORK_TREE`, `GIT_COMMON_DIR`, `GIT_INDEX_FILE`, … — the set `git rev-parse --local-env-vars` lists). Git sets `GIT_DIR` for hooks, and this resolver is the context the hook floor and guards will consume. Probed: `GIT_DIR` pointing at another repo, `resolveContext(<feature clone>)` → `root` of the clone but `branch: "other"` from the foreign repo, `baseSource: "ask"`; a relative `GIT_DIR=.git` from a subdirectory throws "not inside a Git working tree". Ambient mutable state decides what is seen (R8), and the result mixes two repositories. → In isolated mode also delete every variable `git rev-parse --local-env-vars` names (cwd alone must decide), and add a runGit/resolveContext case with `GIT_DIR` set to a second repo proving root, branch and base all come from cwd.
**Fixer (r1):** fixed — isolated mode now deletes every variable `git rev-parse --local-env-vars` lists (GIT_DIR, GIT_WORK_TREE, GIT_COMMON_DIR, GIT_INDEX_FILE, config injection, …), asked of git once per process (src/git/run.ts:22-38); if that list cannot be read, the run returns status 1 instead of falling back to the ambient env (:45). Cases: tests/git-context.spec.ts:559 (GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE → another repo; runGit isolated toplevel and the full resolveContext view come from cwd; premise proves plain git reads the foreign repo), :581 (relative GIT_DIR=.git from a subdirectory). · verify: `bun test tests/git-context.spec.ts tests/arch.spec.ts` ✓ · `bun run typecheck` ✓ · `bun run lint` ✓ · `bun test --parallel=1` ✓ (1410 pass)

## F3 · MINOR · fixed
**Where:** src/git/context.ts:20-22, :103-104
**Critic (r1):** For `remote-head` the result returns only the short name and drops which remote it came from (in I17 `release` exists only as `refs/remotes/upstream/release`), so the merge and PR consumers must re-derive the remote or resolve a bare short name against mutable local refs/tags (R4). → Carry the remote (or the full base ref) in `GitContext` when `baseSource` is `remote-head`.
**Fixer (r1):** fixed — `GitContext.baseRemote` carries the remote whose HEAD named the base, non-null exactly when baseSource is remote-head (src/git/context.ts:22-24, :136); the case table asserts it on every row (I17 → upstream) plus the invariant. · verify: `bun test tests/git-context.spec.ts tests/arch.spec.ts` ✓ · `bun run typecheck` ✓ · `bun run lint` ✓ · `bun test --parallel=1` ✓ (1410 pass)

## F4 · MINOR · fixed
**Where:** tests/git-context.spec.ts (case table) vs src/git/context.ts:57-58, :62-65, :71, :83-84, :94-96
**Critic (r1):** Several guards have no case of their own (R3): an explicit or configured base that is not a branch name (`-x`, `HEAD`, `@{-1}`), a non-string `[git] base`, a local upstream (`.`), and a dangling `refs/remotes/origin/HEAD`. → Add one table row or focused test per guard asserting the throw message or `ask`.
**Fixer (r1):** fixed — added I20 local upstream `.` → origin (tests/git-context.spec.ts:406), I21 dangling origin/HEAD → ask (:424), explicit `-x`/`HEAD`/`a..b`, explicit and configured `@{-1}` with git expanding it to develop (premise proves only the name check stands, :530), non-string `[git] base`. · verify: `bun test tests/git-context.spec.ts tests/arch.spec.ts` ✓ · `bun run typecheck` ✓ · `bun run lint` ✓ · `bun test --parallel=1` ✓ (1410 pass)

## F5 · MINOR · fixed
**Where:** src/git/context.ts:46, :65, :71
**Critic (r1):** The thrown refusals name the problem but not the next step, against P8 ("every refusal says what it protects, the exact path, and the next step"). → Append the fix to each message (e.g. "run from inside the repository", "set `[git] base` to a branch name in <path>").
**Fixer (r1):** fixed — every refusal now names the next step (src/git/context.ts:49, :62, :69 with per-origin fix, :79, :90, :95, :105); asserted in the refusal describe (tests/git-context.spec.ts:492+). · verify: `bun test tests/git-context.spec.ts tests/arch.spec.ts` ✓ · `bun run typecheck` ✓ · `bun run lint` ✓ · `bun test --parallel=1` ✓ (1410 pass)
