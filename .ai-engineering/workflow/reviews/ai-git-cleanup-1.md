# ai-git-cleanup #1 — adversarial review thread

## Goal (checkpoint 1)
`skills/ai-git-cleanup/` holds SKILL.md, scripts/analyze.mjs and references/merge-evidence.md: the script prints one JSON document with every bucket, exclusion and single-quoted command plan carrying merge-base ancestry guards, attribution lands in NOTICE.md and THIRD-PARTY-NOTICES.md, assets are regenerated, and every skills gate passes.

## Acceptance
- The script's JSON always carries an unanalyzed bucket and never lists the current, default or PROTECTED branch as deletable.
- Every emitted delete is single-quoted and every safe delete carries a merge-base ancestry guard naming refs/heads/<branch> and the default branch.
- bun test tests/skills.spec.ts passes with the new folder: frontmatter, Lifecycle, links, English, no machine paths.
- NOTICE.md and THIRD-PARTY-NOTICES.md name Trail of Bits, the plugin URL and CC BY-SA 4.0; SKILL.md carries the Source: line.
- src/assets.ts embeds the new skill files and bun test tests/embed-canon.spec.ts passes.

## changed_files
- skills/ai-git-cleanup/scripts/analyze.mjs
- skills/ai-git-cleanup/SKILL.md
- skills/ai-git-cleanup/references/merge-evidence.md
- NOTICE.md
- THIRD-PARTY-NOTICES.md
- src/assets.ts
- tests/git-cleanup-analyze.spec.ts

## Verify commands
- bun test tests/git-cleanup-analyze.spec.ts
- bun test tests/git-cleanup-cli.spec.ts
- bun test tests/skills.spec.ts
- bun test tests/embed-canon.spec.ts
- bun test tests/workflow-handoff.spec.ts
- bun run typecheck
- bun run lint

## Round 1 — critic (VERDICT: FAIL)

- F1 | med | tests/git-cleanup-analyze.spec.ts:~219 | unanalyzed test is a tautology (LEARNINGS L2): `expect(report.unanalyzed).toBeArray()` passes even when the bucket contains entries; test name says 'every branch classifies' but never asserts `length === 0` — a branch erroneously routed to unanalyzed would not be caught | CHECK: add `expect(report.unanalyzed).toHaveLength(0)` after the `.toBeArray()` assertion
- F2 | med | tests/git-cleanup-analyze.spec.ts:~105 | current branch test exercises LOCAL_WORK path (unique > 0), never the CURRENT_BRANCH guard at analyze.mjs:187 where unique === 0 and the branch is checked out — if the current-branch check were removed or reordered below the merge-base guard, a merged checked-out branch could enter SAFE_TO_DELETE or MERGE_PROOF_INCONCLUSIVE with no test failure | CHECK: add a test that creates a branch, merges it into default, stays checked out on it, and asserts it is in keep with reason CURRENT_BRANCH, not in deleteCandidates
- F3 | minor | tests/git-cleanup-analyze.spec.ts:~116 | SAFE_TO_DELETE test asserts `verifyWith` but never asserts the `command` field — if `command` used `-D` instead of `-d` or dropped single quotes, no test would fail | CHECK: add `expect(entry?.command).toBe("git branch -d 'feature/merged'")`
- F4 | minor | tests/git-cleanup-analyze.spec.ts:~255 | dirty worktree test checks worktree entry flags but never asserts `worktreePath` is set on the corresponding delete candidate — analyze.mjs:249 assigns it, but no test verifies it propagates | CHECK: assert worktreePath defined on the feature/clean-wt delete candidate
- F5 | minor | skills/ai-git-cleanup/SKILL.md:~17 | 'What it produces' lists deleteCandidates, needsReview, keep, worktrees, unanalyzed, defaultBranch, currentBranch — the script also emits `cluster`/`group` on grouped entries but SKILL.md does not document it | CHECK: add it to the produced-fields list or note it is informational

Unverified suspicion (critic): defaultBranch falls back to currentBranch (analyze.mjs:123) when no origin/KNOWN_DEFAULT exists — a repo with only feature branches could treat one as default; verifyWith still runs, but no test covers this edge.

## Round 1 — fixer response

FILES: skills/ai-git-cleanup/scripts/analyze.mjs, skills/ai-git-cleanup/SKILL.md, tests/git-cleanup-analyze.spec.ts

- F1: fixed — `expect(report.unanalyzed).toHaveLength(0)` added; mutating isInventoryComplete to route branches into the bucket now fails the test.
- F2: fixed — new case: branch merged into default, left checked out at unique===0, asserts keep reason CURRENT_BRANCH and absence from deleteCandidates; deleting the guard fails it.
- F3: fixed — asserts command exactly `git branch -d 'feature/merged'`; a -d→-D mutation fails the test.
- F4: fixed — asserts delete candidate's worktreePath equals the worktree entry's path (macOS /private/var symlink handled); removing the assignment fails the test.
- F5: fixed — SKILL.md Step 1 produced-fields list documents the informational cluster field.
- suspicion: fixed — REAL GAP reproduced: no origin, default mainline, HEAD on feature/x emitted `git branch -d 'mainline'` (true default listed SAFE_TO_DELETE). Removed currentBranch from the anchor list (analyze.mjs:139); empty anchor fails closed to unanalyzed NO_DEFAULT_BRANCH; pinned by new test 'no default anchor'.

Verification claimed: analyze 16/16, cli 6/6, skills 19/19, typecheck OK, lint OK, embed-canon 13/13, workflow-handoff 2/2; U3 rewritten to resolve via origin/HEAD.

## Round 2 — critic (VERDICT: PASS)

Rulings: F1 resolved (toHaveLength(0) added; mutation would fail) · F2 resolved (current-branch at unique=0 case) · F3 resolved (command asserted exactly) · F4 resolved (worktreePath tied across sections) · F5 resolved (cluster documented) · suspicion resolved (currentBranch removed from derivation; "no default anchor" test proves fail-closed).

Attacks that did not land: NO_DEFAULT_BRANCH bucketing traced; symbolic-ref persistence check; KNOWN_DEFAULTS still resolves main/master/trunk/develop/dev locally; SKILL.md cluster text matches output shape.
New findings: none. Unverified suspicions: none remaining.

Loop result: PASS after 2 rounds; fixer changed code in round 1 → Gate 1 (behavior) re-run required before marking review passed.
