# ai-git-cleanup-v3 #1 — adversarial review thread

## Goal (checkpoint 1)
analyze.mjs stays the read-only deterministic engine but emits the v3 shape — a phase-0 migration plan (default-branch detection, dirty/stash steps, ff-only pull pinned to the default branch), protection-filtered classification, the one delete batch with category and evidence, and report data — with the unit and CLI specs reworked to pin the new behavior in its exact configurations.

## Acceptance
- One JSON document per run: fetchStatus, migration plan (pull pinned to default branch, never HEAD), protection-filtered classification, one batch with per-entry category/evidence/guarded single-quoted command, worktrees, report data.
- Every classification branch lands in its exact configuration; any error/uncertainty fails closed to KEEP and appears in the report (R3/R2).
- The protection filter runs before every classification path: no PROTECTED, default, or linked-worktree-checked-out branch ever reaches the batch.
- No `git push`, reflog GC or remote deletion in any emitted command; `-d` entries always carry the merge-base guard.
- analyze 30/30, cli 19/19, typecheck, lint clean.

## changed_files
- skills/ai-git-cleanup/scripts/analyze.mjs (v3 restructure: mode flags, migration/batch/report shape, protection-first classification)
- tests/git-cleanup-analyze.spec.ts (30 cases; header pins the authoritative shape)
- tests/git-cleanup-cli.spec.ts (19 cases; mode scoping rewritten to pinned sections)

## Verify commands
- bun test tests/git-cleanup-analyze.spec.ts
- bun test tests/git-cleanup-cli.spec.ts
- bun run typecheck
- bun run lint
- (informational) bun test tests/git-cleanup-flow.spec.ts — 0/3 OLD-shape failures deferred to cp2 by the plan's regressions map

## Known context
- Gate 1 attempt 1 FAILED on fixture-premise bugs (L19: identical-sha cherry-picks, HEAD not restored, deepPairs double-emit, ahead truth 4) + a shape conflict ruled by the orchestrator: NO separate `classification` section — batch/keep/unanalyzed ARE the classification (analyze-spec header pin authoritative). Attempt 2 PASS.
- Worktree-batch rule (plan assumption): CLEAN+stale held branch IS batched with worktreePath; DIRTY held branch never batched (requiresAcknowledgment → KEEP).
- Migration pull is EMITTED DATA only (analyzer is read-only; execution is the skill's main session in cp2).
- Safety backbone: R3 (protection before every path), R4 (pull pinned to default ref, never HEAD), R16 no mutable default anchor, fail-closed.

## Round 1 — critic (VERDICT: FAIL)

- F1 | high | skills/ai-git-cleanup/scripts/analyze.mjs:347-354 | EMPTY_DIFF/GONE_EMPTY classification lacks the isCurrent guard — a checked-out branch tree-identical to default but not merged is classified -D and batched targeting itself; merged (:327) and gone (:357) paths HAVE the guard, empty-diff between them does not | CHECK: branch from main, commit+revert (tree-identical, not ancestor), HEAD on it → batch contains current branch as -D
- F2 | minor | tests/git-cleanup-analyze.spec.ts | no test covers current-branch + empty-diff config (both tree-identical tests checkout main first), the exact config where isCurrent alone stands (R3) | CHECK: leave HEAD on the tree-identical branch, assert CURRENT_BRANCH keep, not -D

Attacks that did not land: regex casing, defaultBranch fall-through, pull pinned+behind-gated, stash message injection, shellQuote hostile refnames, -D only on diff.status===0, push/gc/reflog document scan, mode isolation, fail() stderr-only, INVENTORY_INCOMPLETE gate.

Unverified suspicions: diff --quiet vs gc'd default ref (caught by DIFF_FAILED park); worktree-inventory/batch execution race (inherent to read-only-plan design).

## Round 1 — fixer response

FILES: skills/ai-git-cleanup/scripts/analyze.mjs, tests/git-cleanup-analyze.spec.ts, tests/git-cleanup-cli.spec.ts

- F1: fixed — single choke-point guard inside classify() (the only batch-pushing function): branch===currentBranch && (action!=="keep" || reason==="REMOTE_GONE") → keep/CURRENT_BRANCH, command dropped; per-path guards removed so MERGED/EMPTY_DIFF/GONE_EMPTY/REMOTE_GONE all covered by construction (batch.push only after the guard). Repro: BEFORE held {action:-D, command: git branch -D …}; AFTER batch empty, keep CURRENT_BRANCH. cli tree-identical fixture left HEAD on the buggy branch — switched back to trunk.
- F2: fixed — new case proves HEAD on feature/treesame (symbolic-ref), not merged, diff status 0 → CURRENT_BRANCH, absent from batch, no command names it; fails without guard (Received: undefined), passes with it.

Verification claimed: analyze 31/31, cli 19/19, typecheck 0, lint 0 (3 pre-existing warnings); flow untouched.
LESSON: A protection rule belongs in the one choke point every categorization funnels through, and every fixture must prove where HEAD sits — a test left sitting on the guarded branch silently pins the bug it claims to forbid.

## Round 2 — critic (VERDICT: PASS)

Rulings: F1 resolved — classify() choke point at :202 intercepts before the sole batch.push (:219); all 7 callers funnel through; per-path guards removable by construction. F2 resolved — new analyze.spec case (:494) proves HEAD via symbolic-ref + not-merged + diff=0 → CURRENT_BRANCH keep, absent from batch; cli tree-identical fixture now on trunk (proves -D for non-current).

New findings: none. Attacks that did not land: recursive classify termination, gone-empty fixture HEAD position, work-safety keeps pass-through (action=keep && reason≠REMOTE_GONE), 31/31 + 19/19 + typecheck 0 + lint 0 confirmed.

Loop result: PASS after 2 rounds; fixer changed code in round 1 → Gate 1 (behavior) re-run required before marking review passed.
