# ai-git-cleanup-v2 #2 — adversarial review thread

## Goal (checkpoint 2)
The single approved plan carries the post-cleanup local sync — `git worktree prune` only if a worktree was removed, `git pull --ff-only` on the default branch only if it is behind its upstream, ahead reported never pushed — the flow spec proves the pairing contract and every invariant end to end, and the feature closes with CHANGELOG, an amended changeset and a green full sweep.

## Acceptance
- postSync: prune only when a worktree removal is queued; ff-only pull only when default behind; ahead report-only (no push anywhere); part of the ONE approved plan in acceptance order (deletions → prune → pull → ahead report).
- flow spec proves pairing + no-push + fetchStatus/postSync presence end to end.
- CHANGELOG names the skill under Unreleased; .changeset/ai-git-cleanup.md amended (minor).
- skills/workflow-handoff/arch/embed-canon/typecheck/lint + full `bun test` green.
- No CI integration, auto-deletion, remote branch deletion or reflog GC anywhere.

## changed_files
- skills/ai-git-cleanup/scripts/analyze.mjs (postSync emission)
- skills/ai-git-cleanup/SKILL.md (single gate carries sync, produced-fields names postSync)
- CHANGELOG.md (v2 bullet added)
- .changeset/ai-git-cleanup.md (amended)
- tests/git-cleanup-analyze.spec.ts (U6-U8 + F2 bucket assertions)
- tests/git-cleanup-flow.spec.ts (U9-U10, F1 comment reword)
- tests/git-cleanup-cli.spec.ts (8 postSync cases + aheadBehind type fix)

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
- bun test (full sweep)

## Known context
- Gate 1 (behavior) PASS: all layers green, full sweep 912/912; spot-check behind → `git pull --ff-only 'origin' 'main'` present, ahead → report-only, zero commands contain 'push' across both JSONs, single-JSON stdout, exit 0.
- Coordination note: ordering ruling — checkpoint acceptance order is the contract (deletions → prune → pull → ahead), tests pin neither.
- cp1 thread: .ai-engineering/workflow/reviews/ai-git-cleanup-v2-1.md (PASS; F1 comment + F2 buckets resolved in this checkpoint's test changes).

## Round 1 — critic (VERDICT: PASS)

- F1 | minor | skills/ai-git-cleanup/scripts/analyze.mjs:265 | the `deletable.has(entry.branch)` guard in the stale condition is untested in the config where it alone decides (clean worktree on a keep-branch) — mutation `stale = !dirty` passes all 42 tests; if regressed, a clean worktree holding unmerged work would be planned for removal | add fixture: clean worktree on branch in keep → assert stale !== true

Attacks that did not land: push hiding in prune (hardcoded), pull (config-derived, quoted), worktree.command (shellQuote), branch names (commandStrings + flow /push/ scan); postSync always spread (Object.hasOwn x6); upstream-empty guard; behind>0 only; single-approval covers deletions AND sync (SKILL.md step 4); CHANGELOG/changeset/postSync-shape truth; F1 comment reworded; F2 bucket assertions present; deepPairs catches postSync commands.

Loop result: PASS in 1 round, no fixer. F1 → deferred MINOR note for app review.
