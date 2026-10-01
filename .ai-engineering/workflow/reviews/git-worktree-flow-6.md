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
