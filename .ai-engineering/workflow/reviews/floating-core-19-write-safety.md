# Adversarial review — floating-core#19 write safety

## Goal
Preserve user-owned machine-home settings when carrier cleanup writes or removes settings.

## Acceptance
- Machine-settings create/replace/remove operations that cannot be bound safely to the validated filesystem identity are refused with a warning; original bytes and symlink targets remain unchanged.
- A file or symlink that changes after ownership validation is preserved; cleanup aborts rather than retrying against the replacement.
- Previously resolved CP19 behavior remains green.

## changed_files
- src/commands/uninstall.ts
- src/commands/init-shared.ts
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

### Critic — attempt 2, round 2
VERDICT: FAIL
F5 (Resolved) — I73 now passes: the replacement is staged before the original is touched, and a staging-write exception preserves the original bytes. Cleanup failure is reported while leaving the original intact; the staged-file cleanup attempts to preserve a path whose inode changed.
F6 (High) — The final ownership check is still separate from each pathname mutation: `src/surfaces/adapters.ts:629-635` checks the snapshot, then `renameSync` unconditionally replaces whatever is at `targetName`; `:671-674` checks then unlinks whatever is at `name`. Another process can replace the settings file or symlink after the check but before the syscall, so the replacement is overwritten or removed, contrary to the agreed abort-and-preserve rule. `cleanupMachineSettingsStage` has the same `lstat`/`unlinkSync` gap at `:569-573`. The added races replace paths during revalidation, not at the final syscall boundary.
Fix: bind each mutation to the validated identity with an operation-level conditional primitive; if unavailable, fail closed rather than treating an adjacent check plus plain rename/unlink as conditional. Cleanup must likewise avoid unlinking a changed staged path; never retry against replacements.
Failures: `bun test tests/carriers-install.spec.ts -t "machine settings"` passes all 5 selected tests, including I73, but the teardown leak guard fails on pre-existing `tests/.worktree-lifecycle-*` paths. Open: F6.

### Fixer — F6
FILES: `src/surfaces/adapters.ts`, `src/commands/init-shared.ts`, `src/commands/uninstall.ts`, `tests/carriers-install.spec.ts`, `tests/adversarial/carrier-merge.test.ts`, `tests/uninstall-command.spec.ts`, `.ai-engineering/workflow/reviews/floating-core-19-write-safety.md`.
ROOT CAUSE: The F5 snapshot checks still preceded path-based `renameSync`/`unlinkSync`; portable Node/Bun filesystem APIs provide no operation that conditionally mutates a pathname only while it names the validated inode.
FIX: Machine settings creation, replacement, and removal now fail closed when a pathname mutation would be needed; no stage cleanup, rename, or unlink touches those settings paths, warnings explain the refusal, I73 now asserts refusal preserves the original bytes, and deterministic boundary tests prove injected replacements survive without a settings-path mutation.
LESSON: A pathname check cannot bind a later syscall to an inode; when the portable filesystem API cannot make that binding, refuse the mutation instead of claiming the race is closed.
