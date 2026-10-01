# Review · git-worktree-flow #1 — the missing git contract

## Goal
`AGENTS.md` and `templates/AGENTS.md.tpl` carry the worktree-per-feature contract that `ai-orchestrator` already cites by name, and the shipped template keeps the headings its section test requires.

## Acceptance
1. Both files state: worktree per slug cut from the local `main`; one merge commit per feature into the local `main`; no push from a session; the pull request as the human's decision; the primary tree untouched while a session runs; design slots written and committed in the primary tree before any worktree and never staged from a worktree; shared files written by the merge step.
2. The template still contains the headings `tests/agents-md-sections.spec.ts` requires, and both files stay under doctor's 120-line ceiling.
3. The embedded assets are in sync (`tests/embed-canon.spec.ts`).

## changed_files
- `AGENTS.md`
- `templates/AGENTS.md.tpl`

## Verify commands
- `rg -q 'worktree' AGENTS.md`
- `rg -q 'merge --no-ff' AGENTS.md`
- `rg -q '## Git workflow' templates/AGENTS.md.tpl`
- `rg -q 'worktree' templates/AGENTS.md.tpl`
- `bun test tests/agents-md-sections.spec.ts`
- `bun test tests/embed-canon.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun run build`

---

## Round 1 — critic

Verify re-run: all seven commands pass (rg ×4, agents-md-sections 17 pass, embed-canon pass, typecheck exit 0, lint exit 0, build exit 0). AGENTS.md 65 lines, template 90 lines — both under doctor's 120. Acceptance 1 is met by both files. Findings below are drift, a rule-vs-consumer contradiction, and two scenarios the contract does not answer; no BLOCKER, no MAJOR, so PASS.

## F1 · MINOR · resolved
**Where:** templates/AGENTS.md.tpl:44-45 (vs AGENTS.md:51-52)
**Critic (r1):** The shipped template's contract is weaker than the repo's: line 45 drops "against `origin/main`" and "cut from the local `main` without a worktree" (AGENTS.md:52), and line 44 drops "the one undoable unit" (AGENTS.md:51). A project installed from the template never learns the PR branch is cut from the local main without a worktree — the exact rule PRD §84 and brainstorm §06 fix. → Mirror AGENTS.md:51-52 verbatim in the template. Settle: `diff <(sed -n '50,55p' AGENTS.md) <(sed -n '43,48p' templates/AGENTS.md.tpl)` shows the two dropped clauses.

**Fixer (r1):** fixed — mirrored AGENTS.md's merge/PR/slot/shared clauses into the template (templates/AGENTS.md.tpl:44-48): `--no-ff` "the one undoable unit", PR "against `origin/main`, cut from the local `main` without a worktree", build-session vs merge-step ownership, and the corrected slot/shared lists. · verify: `bun scripts/gen-assets.ts` + `bun test tests/embed-canon.spec.ts` ✓; the two blocks now differ only in the template's `;` in bullet 1.

## F2 · MINOR · open
**Where:** AGENTS.md:51 (vs skills/ai-orchestrator/SKILL.md:45,172)
**Critic (r1):** The change exists because the skill cites "the AGENTS.md git workflow" by name, but the skill still closes with `git merge --squash feat/<slug>` and "one squashed commit per feature" — the direct opposite of `git merge --no-ff` / "one merge commit per feature". Until checkpoint 3 rewrites the skill, the new contract is contradicted by its named consumer, so the rule cannot be trusted to describe the run that cites it. → Checkpoint 3 owns the rewrite; the coordinator must not treat the contract as live before it lands (or cp3 must land in the same merge). Settle: `rg 'squash|--no-ff' skills/ai-orchestrator/SKILL.md` — both appear.

**Fixer (r1):** not fixed here — checkpoint 3 owns `skills/ai-orchestrator/SKILL.md`; the contract is correct and its named consumer is rewritten there. Left open for the coordinator so the contract is not treated as live before cp3 lands.

## F3 · MINOR · resolved
**Where:** AGENTS.md:52; templates/AGENTS.md.tpl:45
**Critic (r1):** "A session never pushes" is absolute, but the approved design makes `ai-pr` push from a session-inside-agent (PRD §84/§06: "pushes, opens the pull request against main"; brainstorm §06: "empuja, abre el PR"). Read literally the rule forbids the very PR mechanism the next clause announces, so an agent running `ai-pr` cannot tell which rule wins. → Carve it out: "a build session never pushes; the only push is the PR step (`ai-pr`), which the human starts." Settle: compare the rule with the `ai-pr` skill's git commands once checkpoint 5 lands.

**Fixer (r1):** fixed — AGENTS.md:52 / templates/AGENTS.md.tpl:45 now read "A build session never pushes: the only push is the pull-request step the human triggers, against `origin/main`, cut from the local `main` without a worktree." Scopes the ban to the build session and names the human-triggered PR step as the sole push.

## F4 · MINOR · resolved
**Where:** AGENTS.md:53,55; templates/AGENTS.md.tpl:46,48
**Critic (r1):** "The primary tree is not touched while a session runs" collides with the shared-files rule: the merge step must write `CHANGELOG.md`/`LEARNINGS.md`/`FILEMAP.md`/`PERMISSIONS.md`/`recap.html` in the primary tree (design §08 "en el árbol principal") — and with two parallel sessions, session B is still running when session A's merge writes there. The rule does not say *who* may not touch it, so the merge step is left either violating it or guessing. → Scope it to sessions: "a running session never writes in the primary tree; the primary tree is the merge step's workspace." Settle: two worktrees, merge one while the other runs, observe the merge step writing `CHANGELOG.md` in the primary tree.

**Fixer (r1):** fixed — AGENTS.md:53 / templates/AGENTS.md.tpl:46 now "A build session does not touch the primary tree; only the merge step writes there, once, after that session's branch has merged." Names who may write (the merge step) and when (once, after that branch merged).

## F5 · MINOR · upheld
**Where:** AGENTS.md:54-55 (vs src/spec/index.ts:21)
**Critic (r1):** The design-slot list disagrees with the code that defines it: AGENTS.md calls `PRD.html` a design slot and `recap.html` a merge-written shared file, but `SLOT_FILES` at src/spec/index.ts:21 is `["spec.html","plan.html","brainstorm.html","recap.html"]` — the inverse on both names. One of the two is stale, and the contract cannot be verified against the code until they agree. → Checkpoint 2's shared design-slot module must make `PRD.html` a slot and `recap.html` a shared file, matching AGENTS.md:54-55. Settle: `sed -n '21p' src/spec/index.ts` vs AGENTS.md:54.

**Fixer (r1):** fixed — read `src/spec/index.ts:21` (`SLOT_FILES = ["spec.html","plan.html","brainstorm.html","recap.html"]`) and `:196-205` (`spec close` deletes exactly those). AGENTS.md:54 / templates/AGENTS.md.tpl:47 now list the slots as `brainstorm.html`, `spec.html`, `plan.html`, `recap.html`; `PRD.html` moved to the merge-step shared files (AGENTS.md:55 / tpl:48) as `.ai-engineering/PRD.html` — the cumulative product doc planted by `src/commands/plant-workflow.ts:12`. The shared list is now `CHANGELOG.md`, `LEARNINGS.md`, `FILEMAP.md`, `PERMISSIONS.md`, `.ai-engineering/PRD.html`, with no slot among them.

## Round 2 — critic

Re-ran the verify set: `rg` ×4 ok; `agents-md-sections` + `embed-canon` 17 pass; typecheck exit 0; template still has `## Git workflow` and 15 `## ` headings, 90 lines; AGENTS.md 65. `src/assets.ts` is unmodified in `git status`, so `gen-assets` changed nothing (the template is embedded by reference).

**F1 — resolved.** Read both blocks: templates/AGENTS.md.tpl:43-48 now mirrors AGENTS.md:50-55 clause for clause (`--no-ff` + "the one undoable unit", PR "against `origin/main`, cut from the local `main` without a worktree", slot/shared lists). The only difference is the `;` in bullet 1, which is the template's own style. Verified, not just claimed.

**F2 — correctly deferred.** Checkpoint 3 owns `skills/ai-orchestrator/SKILL.md` (plan: "rewrites ai-orchestrator Phase 0/close"; notes put the verb at cp2 and the orchestrator at cp3). The contract is right and the consumer is scheduled; do not treat the contract as live until cp3 lands.

**F3 — resolved.** AGENTS.md:52 / tpl:45 now read "A build session never pushes: the only push is the pull-request step the human triggers…" — the ban is scoped and the sole push is named. Matches PRD §06/§84.

**F4 — resolved.** AGENTS.md:53 / tpl:46 now read "A build session does not touch the primary tree; only the merge step writes there, once, after that session's branch has merged." Names the actor who may write, so the merge step no longer violates the rule while a second session runs.

**F5 — upheld.** The fix matched `SLOT_FILES` membership but dragged `recap.html` into a rule whose clauses it violates; see F6.

## F6 · MAJOR · fixed
**Where:** AGENTS.md:54; templates/AGENTS.md.tpl:47
**Critic (r2):** The bullet now says the design slots — including `recap.html` — "are written and committed in the primary tree before any worktree exists, and no worktree ever stages them". That is false for `recap.html`: the consumer writes it at the app review, on the feature branch, after the worktree exists — `skills/ai-orchestrator/SKILL.md:172` "run `/ai-visual-recap` on this branch first. The page it writes, `.ai-engineering/recap.html`, is the review", and brainstorm §08 says the versioned artifacts (it names `recap.html`) sit inside the worktree and must return to the primary tree. A rule that forbids the worktree from staging `recap.html` directly contradicts the step that produces it. → Keep only `brainstorm.html`, `spec.html`, `plan.html` in the pre-worktree slot bullet, and handle `recap.html` under the run-close/merge rules (per PRD §Rules it is a shared file written once by the merge step). Settle: read `skills/ai-orchestrator/SKILL.md:172` + the `spec close` list at `src/spec/index.ts:21` side by side with AGENTS.md:54.

**Fixer (r2):** fixed — read `skills/ai-orchestrator/SKILL.md:172`; the rule no longer claims recap is pre-worktree. AGENTS.md:54-56 / templates/AGENTS.md.tpl:47-49 now split by where each file is really born: `brainstorm.html`, `spec.html`, `plan.html` written and committed in the primary tree before any worktree is cut (no worktree stages them); `.ai-engineering/recap.html` generated at the app review on the feature branch and reaching the primary tree with the merge; the merge step writes `.ai-engineering/PRD.html` when the feature changes scope, plus `CHANGELOG.md`, `LEARNINGS.md`, `FILEMAP.md`, `PERMISSIONS.md`. · verify: `bun scripts/gen-assets.ts`, `bun test tests/embed-canon.spec.ts` ✓

## F7 · MINOR · open
**Where:** AGENTS.md:54-55; templates/AGENTS.md.tpl:47-48
**Critic (r2):** The fix swapped the two lists against the checkpoint's own requirement: PRD §Rules and brainstorm §08 name `PRD.html` a design artifact and `.ai-engineering/recap.html` a shared file, and both docs still do. F5's fix resolved the code drift but opened a docs drift; one of the two sides must be amended in the docs checkpoint, and the contract may not silently override the requirement it was written to satisfy. → Amend PRD §Rules + brainstorm §08 to the code-canonical lists (slots `brainstorm/spec/plan/recap`, `PRD.html` merge-written), or revert the bullet. Settle: `rg -n 'recap.html|PRD.html' .ai-engineering/PRD.html` vs AGENTS.md:54-55.

**Fixer (r2):** not fixed here — the docs drift between these lists and `.ai-engineering/PRD.html` / `brainstorm.html` is checkpoint documentation's job; those pages are design artifacts and are never edited from a worktree. Left open for that checkpoint.
