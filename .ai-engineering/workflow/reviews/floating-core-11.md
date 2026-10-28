# Review thread · floating-core #11 · Rewrite flow skills and the AGENTS.md contract for where-to-work

## Goal
The flow skills, the checkpoint-planner agent and AGENTS.md describe working in the current checkout or a worktree, the detected base and the three closings, with a skill schema lint replacing phrase tests and no main literals or mandatory feat/ in skills and templates.

## Acceptance
- S1: the Direct rhythm has no brainstorm or worktree step.
- S2: a spike writes no design slots.
- S7: ai-pr reads origin/HEAD or the forge default and uses `az repos pr create` without a hard-coded target; S6, S15 and S18 are described for the PR path.
- No `origin/main`/`refs/heads/main` literals or mandatory `feat/` in skills/templates.
- AGENTS.md "Where to work" matches its template; ceremony contract and orchestrator phase/gate assertions stay green.

## changed_files
- tests/agents-md-sections.spec.ts
- tests/agents-canon.spec.ts
- tests/skills-lint.spec.ts
- tests/ai-pr.spec.ts
- tests/git-cleanup-pass.spec.ts
- AGENTS.md
- FILEMAP.md
- agents/checkpoint-planner.md
- skills/ai-adversarial-loop/SKILL.md
- skills/ai-agents-md/SKILL.md
- skills/ai-brainstorm/SKILL.md
- skills/ai-git-cleanup/SKILL.md
- skills/ai-orchestrator/SKILL.md
- skills/ai-pr/SKILL.md
- skills/ai-test-planner/SKILL.md
- skills/ai-verify/tiers/1-standalone/verify-feature/SKILL.md
- skills/ai-verify/tiers/3-chain/_support/review/CONVENTIONS.md
- templates/AGENTS.md.tpl
- templates/gitignore.tpl
- LEARNINGS.md

## Verify
- `bun test tests/init-command.spec.ts`
- `bun test tests/skills-lint.spec.ts`
- `bun test tests/agents-md-sections.spec.ts`
- `bun test tests/skills.spec.ts`
- `bun test tests/workflow-handoff.spec.ts`
- `bun test tests/ai-pr.spec.ts`
- `bun test tests/git-cleanup-pass.spec.ts`
- `bun test tests/agents-canon.spec.ts`
- `bun test tests/ceremony-contract.spec.ts`
- `bun test tests/generated-payload.test.ts`
- `sh -c '! grep -rnE "refs/heads/main|origin/main" src skills templates'`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`
- `bun test --parallel=1`
## F1 · BLOCKER · open
**Where:** skills/ai-git-cleanup/SKILL.md:21
**Critic (r1):** `git branch --merged "$base_ref"` includes the selected base branch itself; the keep rules omit it, so when that branch is not checked out the approved preview can offer the integration target for deletion with `git branch -d`. Exclude the selected local base branch from candidates and test that case.

## F2 · MAJOR · open
**Where:** skills/ai-brainstorm/SKILL.md:299
**Critic (r1):** This seam unconditionally requires stamping and committing brainstorm/PRD slots, then hands off to ai-orchestrator, contradicting the light-lane rule that spikes write no slots and end at ai-verify (and the bounded light path). Scope these steps to Acordado/architectural work and give light paths an explicit no-slot exit; extend the spike contract test to cover the seam.

## F3 · MAJOR · open
**Where:** skills/ai-brainstorm/SKILL.md:6
**Critic (r1):** The `before ANY creative work` trigger and all-path hard gate route Direct bugs and one-session changes through ai-brainstorm despite ai-orchestrator saying Direct has no brainstorm. Limit the trigger/gate to paths that need it and test the cross-skill contract; the current Direct test only scans list items, while the Direct section is prose.

## F4 · MAJOR · open
**Where:** skills/ai-pr/SKILL.md:73
**Critic (r1):** The publish path fetches but never pushes the current branch before either forge create command. Since orchestrator keeps commits local until `/ai-pr`, Azure DevOps cannot create a PR from a normal unpushed branch (and GitHub may prompt interactively). Push the selected branch to the resolved remote before creation, then verify its remote ref.

## F5 · MAJOR · open
**Where:** skills/ai-pr/SKILL.md:36
**Critic (r1):** `git symbolic-ref` returns a full `refs/remotes/<remote>/<branch>` ref, but the create commands pass `$base_ref` directly to forge target options that take branch names. Normalize the detected ref for forge commands while retaining the full ref for Git comparisons; test the symbolic-ref path end to end.
