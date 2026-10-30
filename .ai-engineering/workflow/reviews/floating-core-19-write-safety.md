# Adversarial review — floating-core#19 write safety

## Goal
Preserve user-owned machine-home settings when carrier cleanup writes or removes settings.

## Acceptance
- A failed settings write leaves the original bytes intact and no partial file behind.
- A file or symlink that changes after ownership validation is preserved; cleanup aborts rather than retrying against the replacement.
- Previously resolved CP19 behavior remains green.

## changed_files
- src/commands/uninstall.ts
- src/embed.ts
- src/surfaces/adapters.ts
- tests/adversarial/carrier-merge.test.ts
- tests/carriers-install.spec.ts
- tests/uninstall-command.spec.ts
- .ai-engineering/workflow/test-plans/floating-core.json
- LEARNINGS.md
- .ai-engineering/workflow/reviews/floating-core-19-write-safety.md

## verify
- bun test tests/adversarial/carrier-merge.test.ts
- bun test tests/carriers-install.spec.ts
- bun test tests/uninstall-command.spec.ts
- bun test
### Critic — attempt 2, round 1
VERDICT: FAIL
F5 (High) — `src/surfaces/adapters.ts:409` writes the merged user settings directly to the existing path with `writeFileSync`; `removeMachineCarriers` repeats the in-place write at line 450. A short write or exception after truncation leaves partial settings. I73 injects exactly this failure; its original-bytes assertion fails at `tests/carriers-install.spec.ts:682`.
Safe fix: stage the complete replacement in an exclusive sibling temp file; finish writing and close it before touching settings. Snapshot the no-follow file identity/bytes and symlink/parent identity, and make the commit conditional on that same snapshot; abort without retry if anything changed (a plain check followed by `rename` still has a race). If staging fails, remove only this attempt's temp inode. A failed atomic same-directory rename must leave the original in place; clean the temp only if it is still ours, otherwise report and preserve it. Never truncate the original or retry against a changed path.
Failures: I73 fails because original settings bytes are not preserved. The test runner also reports a leak-guard failure from pre-existing `tests/.worktree-lifecycle-*` paths.

### Fixer — F5
FILES: `src/surfaces/adapters.ts`, `tests/carriers-install.spec.ts`.
ROOT CAUSE: `installMachineCarriers` and `removeMachineCarriers` wrote merged settings in place, so a failed write could truncate a user-owned file before I73 asserted its original bytes.
FIX: Settings rewrites now stage a complete sibling replacement and revalidate no-follow parent/file/link/target snapshots before atomic replacement; missing files publish without clobbering, empty-file removal revalidates the same snapshot, cleanup removes only this attempt's staged inode, cleanup failures are explicit, and I73 remains intact with file/parent/link-race coverage.
LESSON: Preserve user-owned settings by staging writes and revalidating the exact filesystem identity at the commit boundary.
