# ai-git-cleanup-v2 #1 — adversarial review thread

## Goal (checkpoint 1)
SKILL.md asks exactly once: one view presents the full analysis table with the per-row command plan (worktree removals first, then guard-paired deletes) and a single ask (delete all recommended / pick / stop); analyze.mjs emits a top-level fetchStatus that the gate displays; every execution guard is unchanged and the unit and structure specs are green.

## Acceptance
- SKILL.md contains exactly one ask before any change; no text implies a second confirmation; display includes fetchStatus.
- analyze.mjs emits top-level fetchStatus: `ok` (success or no origin) or `failed: <first stderr line>`; exit codes, single-JSON stdout and conservative classification unchanged.
- All 20 analyze + 6 cli cases green; skills/embed-canon/workflow-handoff/flow green; typecheck+lint clean.
- Safety invariants unchanged: one-approval floor (never zero), guards immediately before every -d, -D only with on-screen evidence, protected/current/default never deletable, dirty worktree refusal, unanalyzed surfaced, fail-closed, deletions only in main session.

## changed_files
- skills/ai-git-cleanup/SKILL.md
- skills/ai-git-cleanup/scripts/analyze.mjs
- src/assets.ts (regenerated, byte-unchanged)
- tests/git-cleanup-analyze.spec.ts (4 new cases + WorktreeEntry.command type fix)
- tests/git-cleanup-cli.spec.ts (C1/C2 extended for fetchStatus)

## Verify commands
- bun test tests/git-cleanup-analyze.spec.ts
- bun test tests/git-cleanup-cli.spec.ts
- bun test tests/skills.spec.ts
- bun test tests/embed-canon.spec.ts
- bun test tests/workflow-handoff.spec.ts
- bun test tests/git-cleanup-flow.spec.ts
- bun run typecheck
- bun run lint

## Known context
- Gate 1 (behavior) PASS: 20/20 + 6/6 + structure suites; spot-check bogus remote → fetchStatus `failed: …`, deleteCandidates []; no remote → `ok`.
- Feature request hard floor: never zero confirmations; no fetch retry model (visible only).
- Prior feature's threads: .ai-engineering/workflow/reviews/ai-git-cleanup-1.md and -2.md (R1–R3 in LEARNINGS came from them).

## Round 1 — critic (VERDICT: PASS)

- F1 | minor | tests/git-cleanup-flow.spec.ts:236 | stale "gate 2" comment references the removed two-gate structure (file outside cp1 scope; cp2 reworks it) | grep -n 'gate [12]'
- F2 | minor | tests/git-cleanup-analyze.spec.ts:437-454 | single-view test asserts deleteCandidates/worktrees/fetchStatus/defaultBranch/worktreePath but not keep/needsReview/unanalyzed/currentBranch presence | add bucket-presence expects (R2)

Attacks that did not land: one-approval floor bypass (step 4 explicit "Nothing runs before that approval"); noisy-successful fetch still ok (status!==0 check); single-JSON stdout intact (single stdout.write, stderr captured); exact-stderr assertion replays same command+fixture (not hardcoded git wording); failed fetch never fabricates delete candidates (deleteCandidates=[], LOCAL_WORK kept); step 5 execute strictly after step 4 ask.

Loop result: PASS in 1 round, no fixer run. F1 → fixed by cp2's flow-spec rework; F2 → deferred note, fed to cp2's test writer.
