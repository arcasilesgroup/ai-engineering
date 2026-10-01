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

## Round 2 — critic

Re-ran the set on 67b25dd7: `tests/worktree-command.spec.ts` 24 pass / 0 fail; `spec-command` + `arch` 44 pass; typecheck, lint, build exit 0. Probes against the real CLI in throwaway repos: a worktree cut from inside another worktree lands at `<primary>.worktrees/<slug>`; `list` from inside a worktree prints only the session; `rm <session>` from inside another session removes that worktree and `feat/<slug>`; `rm main` from inside a worktree refuses without touching the primary; an unusable `.ai-eng-worktrees.json` (`null`) refuses both `new` and `rm` before any create or removal.

**F1 — resolved.** Verified, not claimed: the case-alias test (added in 93bafbb9) is green on this case-insensitive fs, and `namesSlot` now canonicalizes then case-folds both sides. The over-refusal you asked about is real on a case-sensitive fs (`BRAINSTORM.HTML` as a genuinely distinct file blocks) but it is the fail-closed side of an error message — accepted, and written in the code's own comment.

**F2 — resolved.** `git status --porcelain -uall -z` with NUL tokens and raw bytes; the non-ASCII-inside-a-slot-directory case (ffb6d76c:544) is green, and a rename's `to\0from` order is proven by the pre-existing rename case.

**F3 — resolved.** `primaryRepoRoot()` from `--git-common-dir` (parent of `.git`), used by `new`, `list`, `rm` and the guard; verified from inside a worktree, from a subdirectory of the primary, and for the two `rm` protections above. The primary can no longer be listed, cut over, or removed.

**F4 — resolved.** Branch `feat/<slug>`, keys `branch.feat/<slug>.{remote,merge}`, start point pinned to `refs/heads/main` (LEARNINGS R4), and the spec pins `feat/` and `refs/heads/main` (ffb6d76c) rather than the earlier accidental shape. Probed: `git worktree list` shows `[feat/alpha]`, `git branch` shows `feat/alpha`.

**F5 — resolved.** Shape-validated (`object`, non-null, not an array, string arrays), refused by name when unusable, pruned of vanished slugs. Verified: `null` refuses `new` with a named detail and `rm` with the worktree and branch left intact — no partial cut, no delete.

**F6 — resolved.** `SLUG_PATTERN` plus `/\p{C}/u`, refused before `mkdirSync`; the newline case (ffb6d76c:587) is green.

## F7 · MINOR · open (r2)
**Where:** src/shared-worktree.ts:134/:276/:340 · tests/worktree-command.spec.ts:604
**Critic (r2):** The fix moved the declarations file from beside the worktrees root into `repo` — the primary tree. Probed: `worktree new` leaves `?? .ai-eng-worktrees.json` at the primary root, untracked and not gitignored, so the verb now writes a permanent, unignored artifact into the very tree AGENTS.md:53 keeps clean, and it does so when run from inside a worktree (the case this roundmade supported). The new test pins that location, so the spec now asserts the siting choice rather than the interface. → Write it beside the worktrees root (as before) or ignore it; settle: `git status --porcelain` in the primary after `new` and after `rm`.

## F8 · MINOR · open (r2)
**Where:** src/shared-worktree.ts:89 (`canonicalize(configured.trim())`)
**Critic (r2):** The config is now read from the primary (`loadConfig(repo)`) but a relative `[git].worktrees_dir` is still resolved against `process.cwd()`, so the same repository resolves two different roots depending on where the verb stands (`new` from the primary vs from inside a worktree), and `pruneDeclarations` then prunes against a root the worktrees do not live in. → `join(repo, configured)` when the value is relative. Settle: `[git] worktrees_dir = ".wt"` then `new` from the primary and from inside a worktree must print the same root.

## F9 · MINOR · open (r2)
**Where:** src/shared-worktree.ts:148-183 (`dirtySlot` and its comment)
**Critic (r2):** The guard's construction limit is nowhere written: `git status` does not report `assume-unchanged`/`skip-worktree` entries or ignored paths, and a symlink whose target changed is unchanged to git. Probed: commit `.ai-engineering/brainstorm.html`, `git update-index --assume-unchanged` it, append dirt — `git status -uall` is clean and `worktree new` exits 0 over the dirty slot. → One comment (or a LEARNINGS line) stating exactly what the guard cannot see, so the next reader does not trust it further than the check does. Settle: the probe above.

Round 2 verdict: PASS with three MINOR findings (F7, F8, F9).
ROUND 2: resolved 6 · withdrawn 0 · upheld 0 · new 3
