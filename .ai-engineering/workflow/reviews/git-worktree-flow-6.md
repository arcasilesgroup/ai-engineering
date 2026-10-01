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
