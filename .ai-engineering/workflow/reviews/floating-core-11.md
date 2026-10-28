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
## F1 · BLOCKER · fixed
**Where:** skills/ai-git-cleanup/SKILL.md:21
**Critic (r1):** `git branch --merged "$base_ref"` includes the selected base branch itself; the keep rules omit it, so when that branch is not checked out the approved preview can offer the integration target for deletion with `git branch -d`. Exclude the selected local base branch from candidates and test that case.

**Fixer (r2):** fixed — excluded `$base_branch` from the merged candidate list (`skills/ai-git-cleanup/SKILL.md:23`, `tests/git-cleanup-pass.spec.ts:16`) · verify: `bun test tests/git-cleanup-pass.spec.ts tests/skills-lint.spec.ts tests/ai-pr.spec.ts` ✓
**ROOT CAUSE:** The merged-branch preview included the selected base itself.
**FIX:** Filter the exact selected short base name before presenting deletion candidates and pin the filter in the skill contract test.
**LESSON:** Remove protected refs at candidate selection, before any deletion path can see them.

## F2 · MAJOR · fixed
**Where:** skills/ai-brainstorm/SKILL.md:299
**Critic (r1):** This seam unconditionally requires stamping and committing brainstorm/PRD slots, then hands off to ai-orchestrator, contradicting the light-lane rule that spikes write no slots and end at ai-verify (and the bounded light path). Scope these steps to Acordado/architectural work and give light paths an explicit no-slot exit; extend the spike contract test to cover the seam.

**Fixer (r2):** fixed — scoped artifact writes and orchestrator handoff to standard/full lanes (`skills/ai-brainstorm/SKILL.md:196,279,324`) · verify: `bun test tests/git-cleanup-pass.spec.ts tests/skills-lint.spec.ts tests/ai-pr.spec.ts` ✓
**ROOT CAUSE:** The artifact seam and lifecycle promised slot writes and orchestrator handoff without checking the lane.
**FIX:** Limit those steps to standard/full, explicitly end light paths at `ai-verify` with no slot, and test the spike/light contract.
**LESSON:** Make artifact ownership and handoff conditional on the classified lane.

## F3 · MAJOR · fixed
**Where:** skills/ai-brainstorm/SKILL.md:6
**Critic (r1):** The `before ANY creative work` trigger and all-path hard gate route Direct bugs and one-session changes through ai-brainstorm despite ai-orchestrator saying Direct has no brainstorm. Limit the trigger/gate to paths that need it and test the cross-skill contract; the current Direct test only scans list items, while the Direct section is prose.

**Fixer (r2):** fixed — narrowed trigger and gate to brainstorm-owned paths (`skills/ai-brainstorm/SKILL.md:4,23`, `tests/skills-lint.spec.ts:193`) · verify: `bun test tests/git-cleanup-pass.spec.ts tests/skills-lint.spec.ts tests/ai-pr.spec.ts` ✓
**ROOT CAUSE:** A broad creative-work trigger and all-path approval gate contradicted the orchestrator's Direct rhythm.
**FIX:** Exclude clear Direct/light tasks and add a cross-skill contract that pins the bypass.
**LESSON:** Route clear work to its execution skill instead of imposing a separate brainstorm gate.

## F4 · MAJOR · fixed
**Where:** skills/ai-pr/SKILL.md:73
**Critic (r1):** The publish path fetches but never pushes the current branch before either forge create command. Since orchestrator keeps commits local until `/ai-pr`, Azure DevOps cannot create a PR from a normal unpushed branch (and GitHub may prompt interactively). Push the selected branch to the resolved remote before creation, then verify its remote ref.

**Fixer (r2):** fixed — publish and verify the selected source ref before creation, only in requested PR flow (`skills/ai-pr/SKILL.md:79-93`, `tests/ai-pr.spec.ts:63`) · verify: `bun test tests/git-cleanup-pass.spec.ts tests/skills-lint.spec.ts tests/ai-pr.spec.ts` ✓
**ROOT CAUSE:** The create path had no publication step for a local-only branch.
**FIX:** Push the selected branch to its selected remote and compare the remote ref's hash with local `HEAD`; keep no-remote local-merge/ask behavior.
**LESSON:** Publish and verify the source ref only after an explicit PR request and before forge creation.

## F5 · MAJOR · fixed
**Where:** skills/ai-pr/SKILL.md:36
**Critic (r1):** `git symbolic-ref` returns a full `refs/remotes/<remote>/<branch>` ref, but the create commands pass `$base_ref` directly to forge target options that take branch names. Normalize the detected ref for forge commands while retaining the full ref for Git comparisons; test the symbolic-ref path end to end.

**Fixer (r2):** fixed — keep full `$base_ref` for Git and use normalized `$base_branch` for forge targets (`skills/ai-pr/SKILL.md:42-46,98-110`, `tests/ai-pr.spec.ts:51`) · verify: `bun test tests/git-cleanup-pass.spec.ts tests/skills-lint.spec.ts tests/ai-pr.spec.ts` ✓
**ROOT CAUSE:** The full remote-tracking ref was reused as a forge target.
**FIX:** Derive a short `$base_branch` and use it for create and protection commands, while retaining `$base_ref` for Git comparisons.
**LESSON:** Keep Git revisions and forge branch names distinct at the boundary.
