# Adversarial review — floating-core#19 replan

## Goal
Cleanup and uninstall remove only canon-owned skill files and preserve unrelated user-owned files, including machine-home settings.

## Acceptance
- Carrier cleanup and uninstall preserve machine-home settings, custom skill directories, edited files, and unrelated user-owned content.
- Uninstall removes only byte-identical canon-owned skill files, refuses linked paths, and prunes only empty directories.

## changed_files
- src/commands/uninstall.ts
- src/embed.ts
- src/surfaces/adapters.ts
- tests/adversarial/carrier-merge.test.ts
- tests/carriers-install.spec.ts
- tests/uninstall-command.spec.ts
- .ai-engineering/workflow/reviews/floating-core-19-replan.md
- LEARNINGS.md

## verify
- bun test tests/adversarial/carrier-merge.test.ts
- bun test tests/carriers-install.spec.ts
- bun test tests/uninstall-command.spec.ts
- bun test

## Debate
### Critic — round 1
- **F1 (high)** `src/commands/uninstall.ts:158-171,187-188`: containment is lexical only. A locked path such as `.cursor/hooks.json` behind a symlinked parent passes the check; hashing then reads outside the repo, and unlink/write can delete or rewrite that external file. Reject symlinked path components and verify the resolved target remains under `root` before mutation.
- **F2 (medium)** `src/surfaces/adapters.ts:490-491`: `startsWith(canonReal)` treats sibling prefixes such as `skills-backup/` as inside `skills/`, so uninstall unlinks a foreign mirror symlink targeting that directory. Use path-boundary containment.
- **F3 (medium)** `src/commands/uninstall.ts:110-114`: after observing an empty directory, recursive `rmSync` can delete files created before the removal. Use atomic `rmdirSync`, which fails if the directory is no longer empty.
**VERDICT: FAIL**

## Replan — applied
**FILES**
- `src/commands/uninstall.ts`
- `src/surfaces/adapters.ts`
- `tests/uninstall-command.spec.ts`
- `tests/carriers-install.spec.ts`

**ROOT CAUSE**
- F1 used lexical containment without rejecting symlinked components, F2 used a string-prefix test instead of path-boundary containment, and F3 separated the emptiness check from recursive deletion.

**FIX**
- Validate canonical project paths component by component before reading or mutating them, use `relative()`-based containment for mirror targets, and prune with atomic `rmdirSync`; add linked-parent, backup-prefix, and non-empty-directory regressions.

**LESSON**
- Cleanup ownership requires canonical, component-checked containment, and directory pruning must use the filesystem's atomic empty-directory operation.

### Critic — round 2
- **F1 (high, unresolved):** The static linked-parent case is fixed, but `safeProjectPath()` returns a pathname that is later used by `writeFileSync`/`unlinkSync` (`src/commands/uninstall.ts:35-47,174-183,212-216,240-244`). A concurrent replacement of a checked parent with a symlink after the final check still redirects the mutation outside the repo. Bind validation to the filesystem operation or otherwise prevent path replacement between check and use.
- **F2 (resolved):** `relative()` boundary containment now preserves a `skills-backup/` mirror link, with a regression test.
- **F3 (resolved):** Project pruning now uses `rmdirSync`, so a newly non-empty directory is retained.
**VERDICT: FAIL**

## Replan — round 2
**FILES**
- `src/commands/uninstall.ts`
- `tests/uninstall-command.spec.ts`
- `.ai-engineering/workflow/reviews/floating-core-19-replan.md`

**ROOT CAUSE**
- The path was checked, then reopened by absolute name for mutation, leaving a race where replacing its parent with a symlink redirected the operation.

**FIX**
- Pin the checked parent as the process working directory, verify its canonical identity before relative unlink/rmdir, and write through an `O_NOFOLLOW` file descriptor; add deterministic parent-swap regressions for unlink and write.

**LESSON**
- Bind mutations to the checked directory at the operation boundary instead of reusing a previously checked pathname.

### Critic — round 3
- **F1 (high, still open):** Pinning the parent closes the symlink-parent race, but the file itself is not bound to the content checked: `hashFile()` is followed by `unlinkProjectPath()`, whose `lstat` only rejects symlinks before unlinking any regular replacement (`src/commands/uninstall.ts:271-275,200-205`). For settings, the earlier read is followed by `openSync(...O_TRUNC|O_NOFOLLOW)`, which can truncate a different regular file substituted before open (`src/commands/uninstall.ts:29,42-47,208-216`). Preserve the file if its identity/content changes before mutation.
- **F2 (resolved):** The static `skills-backup/` prefix collision is fixed by path-boundary containment.
- **F3 (resolved):** Project pruning uses atomic `rmdirSync`.
- **F4 (medium):** Machine mirror cleanup resolves a link target, then separately checks/unlinks the link (`src/surfaces/adapters.ts:490-495`). Replacing that symlink after `canonical(link)` but before `unlinkSync(link)` lets the stale ownership result remove a newly user-owned mirror link; bind the target check to the link removed.
**VERDICT: FAIL**
