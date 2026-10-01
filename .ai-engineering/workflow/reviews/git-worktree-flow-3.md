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
- `! rg -q '<slug>#N' skills/ai-orchestrator/SKILL.md`
- `bun test tests/workflow-handoff.spec.ts`
- `bun test tests/embed-canon.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun run build`

## Context the reviewer should know
The contract this skill must follow is `AGENTS.md` → `## Git workflow` (checkpoint 1, passed). The verb it now calls is checkpoint 2 (passed). The commit convention it must respect is enforced at `src/floor/index.ts:145`, and this run already lost two attempts to it: the skill's own table named types (`plan`, `gate`, `wip`) and a scope (`<slug>#N`) that the hook rejects.

## F1 · BLOCKER · fixed
**Where:** `.ai-engineering/workflow/reviews/git-worktree-flow-3.md` (verify list) vs `skills/ai-orchestrator/SKILL.md:29,159`
**Critic (r1):** The published verify command `! rg -q '<slug>#' skills/ai-orchestrator/SKILL.md` fails: `<slug>#` occurs at `:29` and `:159` inside the gate marker `[checkpoint <slug>#<id> <stage>]`, which `scripts/checkpoint-gate.py` requires (`MARKER = re.compile(r"^\s*\[checkpoint\s+([\w.-]+)#(\d+)\s+(\w+)\]")`) and which the skill must keep. The thread's own acceptance text says `<slug>#N`, and the checkpoint JSON line 148 uses `! rg -q '<slug>#N'`, which passes. As written the verify command exits 1, so the checkpoint cannot be verified against its own instrument. → Use `<slug>#N` (or `\(<slug>#`) in the thread's verify list; the skill text itself is right. Check: `rg -q '<slug>#' skills/ai-orchestrator/SKILL.md; echo $?` → `0`.

**Fixer (r1):** fixed — the thread's own verify list now carries `! rg -q '<slug>#N'` (see **Verify commands** above), the pattern the checkpoint JSON uses; the skill's `[checkpoint <slug>#<id> <stage>]` marker is unchanged. verify: `! rg -q '<slug>#N' skills/ai-orchestrator/SKILL.md` ✓

## F2 · BLOCKER · fixed
**Where:** `skills/ai-orchestrator/SKILL.md:173`
**Critic (r1):** The close drops the old "Then make sure everything on `feat/<slug>` is committed" step (present at `1c785bf2^:172`, removed here). Phase 4 runs `/ai-visual-recap`, which only writes `.ai-engineering/recap.html` (its Lifecycle: "Writes: .ai-engineering/recap.html"), never commits, and archives nothing by itself; the orchestrator no longer calls `ai-eng spec close`, which `src/spec/index.ts:201` shows is the only thing that path used to make tracked ("git keeps the history"). `recap.html` is not gitignored (only `.ai-engineering/workflow/playwright/` is, `.gitignore:8`), so an untracked one (a) is not carried by `git merge --no-ff feat/<slug>`, breaking acceptance 3 ("arrives with the merge"), and (b) makes `ai-eng worktree rm <slug>` run `git worktree remove` without `--force` (src/shared-worktree.ts) and refuse on modified/untracked files — the close deadlocks with no recovery instruction. → Commit `recap.html` (and any leftover worktree files) on `feat/<slug>` before the rebase/merge, or say what to do when `worktree rm` refuses. Check: create `.ai-engineering/recap.html` in a worktree, then run the literal close and observe the merge not carrying it and the removal failing.

**Fixer (r1):** fixed — the close is now four numbered moves (`skills/ai-orchestrator/SKILL.md:173-178`); move 1 commits `.ai-engineering/recap.html` (and `.ai-engineering/workflow/reviews/<slug>-*.md`) by path on `feat/<slug>` before the rebase and merge, and says a still-dirty worktree must be committed or reported to the user because `ai-eng worktree rm` runs `git worktree remove` without `--force`. verify: hand walk ✓ (cut worktree, commit, untracked recap, literal close → recap merged, `worktree rm` exit 0; a stray file makes `rm` exit 1 with "use --force")

## F3 · MAJOR · fixed
**Where:** `skills/ai-orchestrator/SKILL.md:82,173`
**Critic (r1):** Phase 0 records the primary checkout's *current* branch (`git rev-parse --abbrev-ref HEAD`) and calls it "the merge target later", but the close never switches to or names that branch — it just runs `git merge --no-ff feat/<slug>` in whatever the primary tree has checked out. `AGENTS.md:51` pins the destination to the local `main`. If the primary checkout sits on a stale feature branch or a human's branch, the feature merge lands there. → Name the destination: switch the primary tree to local `main` (or refuse when HEAD isn't `main`) before `git merge --no-ff`. Check: leave the primary tree on a non-`main` branch and follow the close literally; inspect the merge commit's first parent.

**Fixer (r1):** fixed — Phase 0 (`:82`) now pins the destination: the merge target is the local `main` by name, the primary tree is switched to `main` when clean and the run refuses (saying which branch and what is dirty) when it is not; close move 3 (`:176`) switches to `main` before `git merge --no-ff`. verify: grep ✓

## F4 · MAJOR · fixed
**Where:** `skills/ai-orchestrator/SKILL.md:83`
**Critic (r1):** Phase 0 unconditionally runs `ai-eng worktree new <slug>`, and nothing commits the design slots first. `worktreeNew` refuses (exit 2) when `brainstorm.html`/`spec.html`/`plan.html` are dirty in the primary tree (`dirtySlot`, src/shared-worktree.ts), and the brainstorm gate requires a `brainstorm.html` freshly written for this feature — so a literal run right after `/ai-brainstorm` stalls on the first Phase 0 step. The same call also fails when a crashed run already left `<repo>.worktrees/<slug>`/`feat/<slug>` (`git worktree add -b` errors); the "on resume" parenthetical assumes the run knows it is resuming, but the delegated Phase 0 subagent is just told to run the verb. → Add "commit the design slots in the primary tree" and "if `ai-eng worktree list` already names `<slug>`, enter that worktree instead of running `new`". Check: with an uncommitted `brainstorm.html`, or with the worktree already present, run the literal Phase 0 line.

**Fixer (r1):** fixed — Phase 0 (`:83`) now commits the design slots (`brainstorm.html`, `spec.html`, `plan.html`) to `main` first (the verb refuses a dirty slot), then runs `ai-eng worktree list` and enters the existing worktree when `<slug>` is listed (a crashed-run resume), cutting only when it is not. verify: hand walk ✓ (`worktree list` empty → `worktree new` exit 0 → listed; dirty-slot refusal is the verb's own test)

## F5 · MINOR · fixed
**Where:** `skills/ai-orchestrator/SKILL.md:47`
**Critic (r1):** The stated `commit-msg` contract is wrong: `src/floor/index.ts:145` accepts `feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert` and never checks for a checkpoint number in the body, while the skill claims only `feat`, `docs`, `chore`, `fix` and `test` and that the number is required in the body. The table's messages are all valid, so nothing is rejected, but the skill documents a contract that does not exist. → Quote the real regex, or drop the "checkpoint number in the body" claim and point at the rule that actually requires it. Check: `grep -n 'feat|fix|docs' src/floor/index.ts`.

**Fixer (r1):** fixed — `skills/ai-orchestrator/SKILL.md:47` now states the real rule: the hook accepts all eleven types (`feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert`) with an optional scope matching `[a-z0-9._/-]+` and checks nothing in the body; the number-in-body is labeled this repo's house convention, not hook-enforced. verify: `bun test tests/embed-canon.spec.ts` ✓
**Critic (r2):** verified against `src/floor/index.ts:137-160` — the regex is `^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9._/-]+\))?!?: \S` with no body check; `:47` matches the hook and labels the number as house convention. **resolved**

## Round 2 rulings

**F1 Critic (r2):** verified — the thread's Verify commands now carry `! rg -q '<slug>#N'` and it passes (`rg -q '<slug>#N'` exits 1); the hook-required marker at `:29`/`:159` is untouched. **resolved**
**F2 Critic (r2):** verified — `:173` move 1 stages `.ai-engineering/recap.html` and `.ai-engineering/workflow/reviews/<slug>-*.md` by path on `feat/<slug>` before the rebase, and states the worktree must end empty because `ai-eng worktree rm` runs `git worktree remove` without `--force` (`src/shared-worktree.ts`); `recap.html` is not gitignored (`.gitignore:8` ignores only `workflow/playwright/`). **resolved**
**F3 Critic (r2):** verified — `:82` pins the merge destination to the local `main` by name, switches the primary tree only when clean and otherwise refuses; close move 3 (`:176`) re-checks and switches before `git merge --no-ff`. Matches `AGENTS.md:51`. **resolved**
**F4 Critic (r2):** verified in intent — `:83` commits the design slots and runs `ai-eng worktree list` to enter an existing worktree before cutting; the resume branch is correct (`git worktree add -b` would fail on an existing branch). The slot-commit instruction itself is broken — carried by N1. **resolved**
**F5 Critic (r2):** verified — `:47` matches `src/floor/index.ts:145`. **resolved**

## N1 · MAJOR · fixed (r2)
**Where:** `skills/ai-orchestrator/SKILL.md:83`
**Critic (r2):** The fix says "first commit the design slots (`.ai-engineering/brainstorm.html`, `.ai-engineering/spec.html`, `.ai-engineering/plan.html`) to `main`". A three-path `git add` fails atomically when one path does not exist: `git add a.html b.html` with `b.html` missing → `fatal: pathspec 'b.html' did not match any files`, exit 128, **nothing staged** (verified in a scratch repo). This repo has no `.ai-engineering/spec.html` or `plan.html` (only `brainstorm.html`, `PRD.html`, `recap.html` exist), and a project driven by the orchestrator's own brainstorm gate creates only `brainstorm.html` — so the instruction fails exactly in the case it was added to fix: the slot stays uncommitted and the very next sentence's `ai-eng worktree new` refuses on `dirtySlot`. → Stage only the slots that exist (e.g. `git add -- .ai-engineering/brainstorm.html` when present, guarded per file). Check: `ls .ai-engineering/spec.html .ai-engineering/plan.html` (absent here), then the literal `git add` → exit 128 and `git status` still shows `??`.

**Fixer (r2):** fixed — `skills/ai-orchestrator/SKILL.md:83` now checks each slot and `git add`s it by its own path only when it exists, and forbids naming two paths in one `git add` (a missing path aborts the call, exit 128, nothing staged); a dirty slot that must not be committed is a stop-and-report. verify: hand walk without `spec.html`/`plan.html` ✓ (commit step ends clean, `ai-eng worktree new` exit 0)

## N2 · MINOR · fixed (r2)
**Where:** `skills/ai-orchestrator/SKILL.md:46`
**Critic (r2):** `:46` says of the design slots "they are written in the primary tree before the worktree is cut and no session stages them", while the new `:83` instructs the session to stage and commit those same three files in the primary tree. Two absolute rules in one file, contradicting each other; an agent following both cannot execute Phase 0. → Scope the ban to the run's worktree commits ("never stage a design slot from inside the worktree") and point at the Phase 0 primary-tree commit. Check: read `:46` and `:83` side by side.

**Fixer (r2):** fixed — `skills/ai-orchestrator/SKILL.md:46` now scopes the ban to "from inside the worktree" and points at the Phase 0 primary-tree commit, which `:83` describes; the two rules no longer contradict. verify: read `:46` + `:83` ✓
