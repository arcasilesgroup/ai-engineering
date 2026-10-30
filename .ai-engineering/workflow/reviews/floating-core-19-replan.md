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
