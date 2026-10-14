# ai-git-cleanup #2 — adversarial review thread

## Goal (checkpoint 2)
A fixture-repository test proves the whole emitted command plan end to end (quoting, ancestry guards, protected exclusions, dirty-worktree refusal, unanalyzed surfacing), any gap it exposes is fixed in the script or skill text, and the feature closes with CHANGELOG, a changeset and a green sweep across skills, handoff, arch and embed gates.

## Acceptance
- `bun test tests/git-cleanup-flow.spec.ts` passes and fails if any invariant (quoting, guards, exclusions, refusals) is broken.
- The fixture proves the dirty-worktree refusal and the always-present unanalyzed bucket.
- CHANGELOG.md names the skill under Unreleased Added; .changeset/ai-git-cleanup.md exists with a minor bump.
- tests/skills.spec.ts, tests/workflow-handoff.spec.ts, tests/arch.spec.ts, tests/embed-canon.spec.ts, bun run typecheck and bun run lint all pass.
- No CI integration, auto-deletion, remote branch deletion or reflog GC exists anywhere in the skill.

## changed_files
- CHANGELOG.md
- .changeset/ai-git-cleanup.md
- skills/ai-git-cleanup/SKILL.md
- tests/git-cleanup-flow.spec.ts

## Verify commands
- bun test tests/git-cleanup-flow.spec.ts
- bun test tests/git-cleanup-analyze.spec.ts
- bun test tests/git-cleanup-cli.spec.ts
- bun test tests/skills.spec.ts
- bun test tests/workflow-handoff.spec.ts
- bun test tests/arch.spec.ts
- bun test tests/embed-canon.spec.ts
- rg -q 'ai-git-cleanup' CHANGELOG.md
- bun run typecheck
- bun run lint

## Known context
- Round-1 review of checkpoint 1 is in ai-git-cleanup-1.md (all findings resolved there).
- A test-writer note on the flow spec: "removals ordered before branch deletions" is gate-2 assembly (SKILL.md step 5/6), not report shape — U16 proves the pairing data gate 2 orders by. Attack whether that contract is actually safe.

## Round 1 — critic (VERDICT: PASS)

- F1 | minor | tests/git-cleanup-flow.spec.ts:183 | single-quoting assertion matches the template, not escaping — a shellQuote mutation passes here; covered by analyze spec "quot" (evil refname case) at unit layer | combined suite catches it
- F2 | minor | tests/git-cleanup-flow.spec.ts:170-173 | protected-exclusion asserts only 3 hardcoded names; PROTECTED regex breadth (~20 patterns) tested implicitly | a regex mutation for hotfix/staging/canary slips the flow spec
- F3 | minor | tests/git-cleanup-flow.spec.ts:211-231 | pairing data proven, execution ORDER is textual (SKILL.md L84+L92 "worktrees before branches, run the plan yourself in order") | sufficient by design (main-session execution), untestable as code

Attacks that did not land: shellQuote escaping (unit "quot"), develop removal, worktreePath removal, git push smuggling, unanalyzed removal, dirty detection break, -D emission, merge-base guard break, CHANGELOG/changeset/SKILL.md drift.

Loop result: PASS in 1 round, fixer did not run. F1–F3 recorded as deferred MINOR notes.
