# Review · git-worktree-flow #6 — the docs that make the change readable

## Goal
`README.md` documents the `ai-eng worktree` verb next to `ai-eng git pre-commit`; `CONTRIBUTING.md` describes the local flow (worktree, merge into the local `main`, the pull request as the human's decision); `docs/blueprint.html` gains the behaviour-change section for the verb and the changed skills; a minor changeset lands in `.changeset/`; and `.ai-engineering/PRD.html` plus `.ai-engineering/brainstorm.html` are aligned with the contract so no inverted sentence survives.

## Acceptance
1. `README.md` names `ai-eng worktree` and one line of the flow.
2. `CONTRIBUTING.md` describes the local worktree and merge flow and that the pull request is the human's call.
3. `docs/blueprint.html` has the new section for the verb and the changed skills.
4. `.changeset/git-worktree-flow.md` exists with a minor bump; `FILEMAP.md` is untouched.
5. `AGENTS.md`, `templates/AGENTS.md.tpl`, `PRD.html` and `brainstorm.html` describe the same partition (written before the worktree / arrives with the merge / merge-only) with no inverted sentence left.

## changed_files
- `README.md`
- `CONTRIBUTING.md`
- `docs/blueprint.html`
- `.changeset/git-worktree-flow.md`
- `.ai-engineering/PRD.html`
- `.ai-engineering/brainstorm.html`

## Verify commands
- `rg -q 'ai-eng worktree' README.md`
- `rg -q 'worktree' CONTRIBUTING.md`
- `rg -q 'ai-eng worktree' docs/blueprint.html`
- `rg -q 'brainstorm\.html' .ai-engineering/PRD.html && rg -q 'spec\.html' .ai-engineering/PRD.html && rg -q 'plan\.html' .ai-engineering/PRD.html`
- `! rg -q 'PRD\.html.*spec\.html.*plan\.html' .ai-engineering/PRD.html`
- `! rg -q 'PERMISSIONS\.md.*recap\.html' .ai-engineering/brainstorm.html`
- `test -f .changeset/git-worktree-flow.md && rg -q 'minor' .changeset/git-worktree-flow.md`
- `bun test tests/npm-manifest.spec.ts`
- `bun test tests/arch.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun run build`

## Context the reviewer should know
Checkpoints 1-5 passed. This is the checkpoint where the documentation belongs, and the framework's own rule says it is a checkpoint gate rather than a promise: no workflow reads prose and none fails on a missing changeset, so these `rg` gates are the only thing that keeps the docs true. Attack the *claims*, not the style: a document that describes a flow the tooling does not implement is the defect this gate exists to catch. One deviation is recorded on purpose: the two design pages are edited from inside this worktree (the run that establishes the rule cannot obey it), and the coordinator records that as an assumption.

## Findings (round 1)

### F1 · README's machine-verb sentence contradicts itself and the binary — `fixed`
The prose said four verbs and that they appear in no `--help`, while the block below listed five and `./dist/ai-eng --help` prints seven.

**Fixer (r1):** fixed — `README.md:228-230`: the sentence now says seven machine verbs for hooks, CI and agents, says `--help` names them on one line (verified against the binary's `chain · git · wrap · spec · worktree · adapt · briefing`), drops the false "neither `--help` nor TAB completion" claim, and introduces the block as "the five this section covers". The block line no longer hides the argument: `ai-eng worktree new <slug> | rm <slug> | list`. · verify: `./dist/ai-eng --help` ✓ · `rg -q 'ai-eng worktree' README.md` ✓

### F2 · blueprint §21.2 still sells a per-worktree `.ai-engineering/` — `fixed`
§21.2's concurrency card claimed every worktree is a governed checkout with its own slot, receipts and plan, which §21.6 denies.

**Fixer (r1):** fixed — `docs/blueprint.html:1784`: one sentence added in place, right after that claim: `Revisado por §21.6: el worktree ya no lleva su propio .ai-engineering/: el slot de diseño es uno por repo, se escribe en el árbol principal antes de cortar y el worktree nace solo para construir.` §21.2's own text is untouched, so its history reads as written. · verify: `rg -q 'ai-eng worktree' docs/blueprint.html` ✓

### F3 · stale citation to the slot list — `fixed`
`src/spec/index.ts:21` held `SLOT_FILES` when the row was written; it is defined in the shared module now and imported back.

**Fixer (r1):** fixed — `.ai-engineering/brainstorm.html:236` now cites `src/shared-worktree.ts:14`, the definition that holds it today (`src/spec/index.ts:17` imports it). I checked the page's other `file:line` citations: `src/cli.ts:82` no longer holds `floor(...)` (the verb's new lines pushed it to `:84`), so that citation is corrected too; `src/floor/template.ts:25`, `src/commands/doctor.ts:117`, `src/commands/uninstall.ts:179`, `src/commands/init.ts:96`, `src/shared-worktree.ts:20`, `skills/ai-orchestrator/SKILL.md:27`, `:45`, `:46`, `:153-155`, `skills/ai-visual-recap/SKILL.md:658` and `.ai-engineering/workflow/test-plans/ai-git-cleanup.json:144` all resolve, with the §02 narrative about SKILL.md left as the pre-change record the feature replaced. · verify: `rg -q 'PERMISSIONS\.md.*recap\.html' .ai-engineering/brainstorm.html` → no match ✓

Round 1: the checkpoint's `verify` entries all pass (7 `rg` checks ✓, `bun test tests/npm-manifest.spec.ts` 3/3 ✓, `bun test tests/arch.spec.ts` 22/22 ✓, `bun run typecheck` ✓, `bun run lint` ✓, `bun run build` ✓).

## Findings (round 1, re-run)

### F4 · MAJOR · fixed
**Where:** `docs/blueprint.html:1780,1786`
**Critic (r1):** §21.2 still heads itself «Limpieza y concurrencia: un slot por checkout, worktree por agente» and its closing paragraph still promises «H2 — dos worktrees, dos `spec open`, un `spec close` en cada uno, cero interferencia», both of which §21.6 (`:1825`) and `PRE_WORKTREE_SLOTS` (`src/shared-worktree.ts:20`) deny: the design slot is one per repo and no worktree stages it. The F2 patch inserted one sentence inside the concurrency card and left the section's title and test promise selling the retired model. → Mark §21.2 superseded at the heading (or rewrite the H2/H3 promise) the way §21.6 revises the card body, instead of a note buried mid-card. · verify: read `docs/blueprint.html:1780-1786` against `:1825-1836`.
**Fixer (r2):** fixed — `docs/blueprint.html:1780` heading is now «un slot por repo, worktree por feature (revisado por §21.6)» and `:1786`'s H2 now promises two worktrees building in parallel over the design slot already written and committed in the primary tree, none of them staging it — matching §21.6 and `PRE_WORKTREE_SLOTS`. §21.2's body keeps its history; only the heading and the plan line changed, they no longer sell the retired one-slot-per-checkout model. · verify: `rg -q 'ai-eng worktree' docs/blueprint.html` ✓

### F5 · MAJOR · fixed
**Where:** `.ai-engineering/PRD.html:85`; `.ai-engineering/brainstorm.html:308,316,353`
**Critic (r1):** the pages say `.ai-engineering/PRD.html` «is updated only by the merge step», «lo actualiza solo el paso de merge», and that the shared files «los escribe el merge, no la sesión» once the session is already merged. `skills/ai-orchestrator/SKILL.md` (Phase 3) makes exactly those edits «on `feat/<slug>` inside the worktree», with the merge only «their single writer there [in the primary tree]», and AGENTS.md scopes it to «never by a *parallel* session». The changed prose dropped the «parallel» qualifier and inverted the owner: the run writes them on the branch, the merge carries them. → Say «the merge step is their single writer in the primary tree» and leave the edit on the branch. · verify: `skills/ai-orchestrator/SKILL.md` Phase 3 bullet against the cited lines.
**Fixer (r2):** fixed — `.ai-engineering/PRD.html:85` now reads the shared files and `PRD.html` «may be edited on the feature branch, and the merge step is their single writer in the primary tree, never a parallel session writing them there». `.ai-engineering/brainstorm.html:308,316,353` now say the session may edit `PRD.html`/the shared files on its branch and the merge step is their single writer in the primary tree, no parallel session writing them there. All four documents (AGENTS.md, SKILL.md, PRD.html, brainstorm.html) carry the same qualifier: edit on the branch, one writer in the primary tree. · verify: `rg -c 'single writer in the primary tree' .ai-engineering/PRD.html` → 1 ✓

### F6 · MINOR · fixed
**Where:** `.ai-engineering/brainstorm.html:235`
**Critic (r1):** the row claims `git ls-files .ai-engineering` is «61 ficheros»; the command returns 62 — the 62nd is the review thread this same commit adds. The commit whose message is «a count or a path written in prose is a cache» ships one cache still wrong. → re-derive the number or drop it. · verify: `git ls-files .ai-engineering | wc -l`.
**Fixer (r2):** fixed — dropped the count at `.ai-engineering/brainstorm.html:235`; the row now names the command and the representative paths and no number, so it cannot drift again. For the record the command returns 62 today. · verify: `git ls-files .ai-engineering | wc -l` → 62 ✓

### F7 · MAJOR · open
**Where:** commit `6e875c4e` (`.ai-engineering/brainstorm.html`, `.ai-engineering/PRD.html`)
**Critic (r1):** the recorded deviation is not the «run that establishes the rule»: `## Git workflow` landed in `c9ae9499` and reviews 1-5 already exist, so the rule was live when checkpoint 6 ran. Commit `6e875c4e`, authored inside `ai-engineering.worktrees/git-worktree-flow` on `feat/git-worktree-flow`, stages a design slot and a shared file from that worktree — which AGENTS.md forbids («no worktree ever stages them»; the merge step writes the shared files) and `skills/ai-orchestrator/SKILL.md` repeats («Never stage a design slot … from inside the worktree»). The merged main state is permitted; the branch state the commit creates is not. → Make those two edits in the primary tree (merge step), or state plainly in the record that the contract is broken rather than assumed compliant. · verify: `git show 6e875c4e --name-only` and `git log --oneline -S "## Git workflow" -- AGENTS.md`.

ROUND 1 (re-run): open 4 · resolved 0 · withdrawn 0 · upheld 3 (F1-F3 re-verified: README's seven verbs matches `./dist/ai-eng --help`; §21.2's card note + §21.6 exist; the corrected citations `src/shared-worktree.ts:14`, `:20`, `src/cli.ts:84` resolve).
