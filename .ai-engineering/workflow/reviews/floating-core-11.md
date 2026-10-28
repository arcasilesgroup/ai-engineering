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
