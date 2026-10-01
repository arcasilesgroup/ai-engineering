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

## Round 1 — critic

Re-ran the set on HEAD (93bafbb9): `bun test tests/worktree-command.spec.ts` **19 pass, 1 fail** (the case-alias case, added in 93bafbb9) — the checkpoint's own verify command is red. `tests/spec-command.spec.ts` + `tests/arch.spec.ts` 44 pass. Probes below were run against the real CLI in throwaway repos; read `src/shared-worktree.ts`, `src/commands/worktree.ts`, `src/cli.ts`, `src/spec/index.ts`, the spec, AGENTS.md:49-56 and the checkpoint json.

## F1 · BLOCKER · open
**Where:** src/shared-worktree.ts:128 (`dirtySlot`) · tests/worktree-command.spec.ts:521
**Critic (r1):** The carried-forward finding is a real defect, not an out-of-contract nit. On a case-insensitive filesystem `brainstorm.HTML` *is* the slot, and when the slot is not yet tracked git reports the name as typed (`?? .ai-engineering/brainstorm.HTML`), so the literal equality match misses it and `worktree new` cuts a worktree over a dirty design artifact — the exact failure the guard exists to prevent, on this project's own platform. Also the new test makes the verify command red. → Compare case-insensitively (`path.toLowerCase()` against the slot path), which cannot over-refuse on a case-sensitive fs beyond a name that is a slot everywhere except case. Settle: the case-alias test, and a probe that shows exit 0 today with `?? .ai-engineering/brainstorm.HTML` in a throwaway repo.

## F2 · BLOCKER · open
**Where:** src/shared-worktree.ts:114 (`statusPaths`) · :135 (`startsWith` match)
**Critic (r1):** `git status --porcelain` quotes and C-escapes any path with a non-ASCII byte, a `"` or a `\`; 0e337b76 also dropped the old `replace(/^"(.*)"$/, "$1")`. So a slot replaced by a directory whose inner file has a non-ASCII name arrives as `".ai-engineering/brainstorm.html/caf\303\251.txt"`, `startsWith` fails, and the guard passes. Probed: exit 0, worktree cut. → Ask for `-z` and split on NUL (never quoted), or unquote + unescape; the equality/nesting match then sees the true path. Settle: a case with a non-ASCII filename inside `brainstorm.html/` must refuse.

## F3 · BLOCKER · open
**Where:** src/shared-worktree.ts:53 (`canonicalRepoRoot`) · :92/:198/:208
**Critic (r1):** `repoRoot()` is the nearest `.git`, so from inside a session worktree (`.worktrees/alpha`, where sessions live) it is the worktree, not the common tree. Probed: `list` printed `main <repo>` — the primary as a session — and hid `alpha` itself, the precise bug 2282f7ba claimed to fix; `new beta` cut at `alpha.worktrees/beta`, not `<repo>.worktrees/beta`, and ran the slot guard against the worktree's status, not the primary's; `rm main` resolves the primary as its slug. → Resolve the primary from `git rev-parse --git-common-dir` and use it for the root, the guard and the primary filter (and as the `rm` slug namespace). Settle: `list` and `new` invoked from inside an existing worktree.

## F4 · MAJOR · open
**Where:** src/shared-worktree.ts:186 · AGENTS.md:50 · templates/AGENTS.md.tpl:43
**Critic (r1):** The verb cuts a bare `<slug>` branch and pins it in the spec, while the contract this command implements says `feat/<slug>` — AGENTS.md:50, the embedded template, PRD.html:80, brainstorm §268 and checkpoint 3's tasks (`git switch feat/<slug>` on resume, `git merge --no-ff feat/<slug>`). cp3 as planned will fail against a worktree whose branch is `alpha`. The docs are themselves split (PRD:81's `branch.<slug>.remote` implies the bare name), so one side must be amended before cp3. → Settle the name in one commit; if `feat/<slug>`, fix the config key and the slug derived from `branch` in `openWorktrees`. Settle: `git -C <worktree> rev-parse --abbrev-ref HEAD` vs `rg 'feat/<slug>' AGENTS.md`.

## F5 · MINOR · open
**Where:** src/shared-worktree.ts:72 (`readDeclarations`)
**Critic (r1):** Parse-ability is the only check: a `null` file makes `declarations[entry.slug]` throw on the next `new` (exit 2, no message about the real cause), an `[]` file silently drops every declaration on the next write (overlap warning lost forever), and slugs removed out-of-band are never pruned. → Validate `typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)` and default `{}`; drop keys absent from `openWorktrees` when writing. Settle: seed `.ai-eng-worktrees.json` with `null` and with `[]`.

## F6 · MINOR · open
**Where:** src/shared-worktree.ts:24 (`SLUG_PATTERN`)
**Critic (r1):** `$` also matches before a trailing newline, so `SLUG_PATTERN.test("alpha\n")` is true and the validation admits a value it is meant to reject; `mkdirSync(root)` has already run by the time git refuses the ref. → Anchor with a class that excludes the newline (`[a-z0-9._-]*\z` equivalent) or reject `slug !== slug.trim()`. Settle: `worktree new $'alpha\n'` creates nothing and names the reason.

Round 1 verdict: FAIL (F1 BLOCKER, F2 BLOCKER, F3 BLOCKER, F4 MAJOR; F5, F6 MINOR).
