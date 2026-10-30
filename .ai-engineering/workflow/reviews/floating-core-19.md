# Adversarial review — floating-core#19

## Goal
Init, update, config, doctor, and uninstall handle the complete skills inventory safely, ignore legacy `[canon].packs` without rewriting config, and never execute installed skills.

## Acceptance
- Fresh init installs every skill without a pack prompt or `[canon].packs` entry, and executes none.
- Update installs every skill for legacy pack settings without changing config bytes.
- Update repairs missing shipped payloads while preserving edited skills and unrelated user-owned skill directories.
- Doctor verifies every installed skill regardless of legacy config; config edits preserve unrelated bytes.
- Uninstall removes only canon-owned skill files.
- Installed-skill frontmatter stays within 5,000 tokens and `templates/AGENTS.md.tpl` within 1,200.
- Init recovery restores its edited skill fixture before checking clean-canon drift.
- Live progress opens the new current checkpoint; findings are visible outside Technical details and linked from the status banner.

## changed_files
- README.md
- CHANGELOG.md
- src/env.ts
- src/commands/config.ts
- src/commands/doctor.ts
- src/commands/init-shared.ts
- src/commands/init.ts
- src/commands/uninstall.ts
- src/commands/update.ts
- src/embed.ts
- src/surfaces/adapters.ts
- templates/config.toml.tpl
- templates/viewer.html.tpl
- .ai-engineering/workflow/checkpoints/viewer.html
- tests/init-command.spec.ts
- tests/viewer-audit.spec.ts
- tests/update-command.spec.ts
- tests/config-command.spec.ts
- tests/doctor-command.spec.ts
- tests/uninstall-command.spec.ts
- tests/adversarial/init-recovery.test.ts
- tests/carriers-install.spec.ts
- tests/ceremony-contract.spec.ts
- tests/token-budget.spec.ts
- .ai-engineering/workflow/reviews/floating-core-19.md
- LEARNINGS.md

## verify
- bun test tests/init-command.spec.ts
- bun test tests/viewer-audit.spec.ts
- bun test tests/adversarial/init-recovery.test.ts
- bun test tests/update-command.spec.ts
- bun test tests/config-command.spec.ts
- bun test tests/doctor-command.spec.ts
- bun test tests/uninstall-command.spec.ts
- bun test tests/carriers-install.spec.ts
- bun test tests/ceremony-contract.spec.ts
- bun test tests/token-budget.spec.ts
- bun run build
- bun test
- bun run lint
- bun run typecheck
- bun test tests/arch.spec.ts

## Critic — round 1
VERDICT: FAIL
F1 (High) — `src/commands/config.ts:188`: Valid TOML `[surfaces] # comment` does not match the header; rewrite appends a duplicate table, reports success, and leaves config unparseable. Fix: recognize comments or update parsed table in place.
F2 (Medium) — `src/surfaces/adapters.ts:178`, `src/embed.ts:194-195`: Canon install follows existing symlink components while materializing missing payloads, allowing writes outside the canon. Fix: reject symlinked components or materialize via a contained staging path.
F3 (Medium) — `src/commands/uninstall.ts:237`: Recursive removal of `home()` deletes custom skills and other user files after selective artifact cleanup, contrary to preserving non-canon-owned files. Fix: selectively remove shipped assets and preserve foreign content.
F4 (Medium) — `templates/viewer.html.tpl:199`: `plan.halted` replaces banner text and skips the findings/link branch even when the current checkpoint has findings. Fix: retain a link to the halted/current checkpoint.
Changed files: CP19 scoped list in the review header (24 files).
Failures: `L216` fixture issue fixed (13 focused tests; serial suite passed); `L217` nine init failures unreproduced (focused 33 passed); viewer 24 passed, teardown failed on pre-existing `tests/.worktree-lifecycle-*` paths.

## Fix — round 1

FILES
- `.ai-engineering/workflow/checkpoints/viewer.html`
- `.ai-engineering/workflow/reviews/floating-core-19.md`
- `src/commands/config.ts`
- `src/commands/uninstall.ts`
- `src/embed.ts`
- `templates/viewer.html.tpl`
- `tests/carriers-install.spec.ts`
- `tests/config-command.spec.ts`
- `tests/uninstall-command.spec.ts`
- `tests/viewer-audit.spec.ts`

ROOT CAUSE: The four failures came from a strict table-header regex, unchecked symlink traversal, recursive removal of the shared machine home, and a halted-render branch that discarded its checkpoint link.

FIX: Config rewrites now accept commented table headers, materialization rejects symlinked asset paths, uninstall removes only byte-identical embedded assets and prunes empty directories, and halted banners retain a safe current-checkpoint link.

LESSON: Treat configuration syntax, filesystem ownership, and every viewer state as explicit boundaries, and verify each with a behavior-level regression.

## Critic — round 2
VERDICT: PASS
F1 (Resolved): The commented `[surfaces]` header is recognized and rewritten in place; the regression asserts preserved comment and a single table.
F2 (Resolved): Materialization rejects symlinked destination roots, descendants, and files before writing; the symlink regression confirms the external target stays empty.
F3 (Resolved): Uninstall now removes only byte-identical embedded assets, refuses linked paths, and prunes only empty directories; the regression preserves custom, edited, and unrelated files.
F4 (Resolved): Halted and active banners link to the current step, findings render outside Technical details, and live progress opens the new current step.
New actionable findings: none. Resolved: 4; withdrawn: 0; arbitrated: 0; open: none.
Changed files: no round-two changes; round-one FILES remain as listed above.
Failures: focused regression run had 115 passing tests; preload teardown failed on pre-existing `tests/.worktree-lifecycle-*` paths. `bun run typecheck` and `bun run lint` exited 0 with warnings.

## Attempt 3 — Round 1 · Preserve User Files During Cleanup

### Goal
Cleanup and uninstall remove only canon-owned skill files and preserve unrelated user-owned files, including machine-home settings.

### Acceptance
- Preserve custom, edited, and unrelated content; remove only byte-identical canon-owned skill files; refuse linked paths and prune only empty directories.
- Unsafe machine-settings creation, replacement, or removal warns and preserves original/external targets.
- Local canon installation/configuration/updates/lock recovery still complete when machine registration is refused.
- Protect all settings aliases to `machine.json`, including unselected surfaces and replacements at mutation time.

### changed_files
- `src/commands/uninstall.ts`
- `src/commands/init-shared.ts`
- `src/embed.ts`
- `src/surfaces/adapters.ts`
- `tests/adversarial/carrier-merge.test.ts`
- `tests/carriers-install.spec.ts`
- `tests/uninstall-command.spec.ts`
- `tests/init-command.spec.ts`
- `tests/update-command.spec.ts`
- `tests/config-command.spec.ts`
- `tests/surfaces.test.ts`
- `tests/adversarial/lock-security.test.ts`
- `tests/adversarial/init-recovery.test.ts`
- `.ai-engineering/workflow/reviews/floating-core-19-replan.md`
- `.ai-engineering/workflow/reviews/floating-core-19-write-safety.md`
- `.ai-engineering/workflow/reviews/floating-core-19-machine-state.md`
- `.ai-engineering/workflow/test-plans/floating-core.json`
- `LEARNINGS.md`

### verify
- `bun test tests/adversarial/carrier-merge.test.ts`
- `bun test tests/carriers-install.spec.ts`
- `bun test tests/uninstall-command.spec.ts`
- `bun test tests/init-command.spec.ts`
- `bun test tests/update-command.spec.ts`
- `bun test tests/config-command.spec.ts`
- `bun test tests/surfaces.test.ts`
- `bun test tests/adversarial/lock-security.test.ts`
- `bun test tests/adversarial/init-recovery.test.ts`
- `bun test`

### Findings

## F8 · BLOCKER · open
**Where:** `src/surfaces/adapters.ts:336-338, 741-747, 794-803`
**Critic (r1):** The final all-surface alias scan is still separate from `writeMachineState`/`unlinkSync`; replacing an unselected settings path with an alias after that scan but immediately before the state syscall still mutates or deletes the aliased file. The state writer also follows a symlinked `machine.json`. The added race test changes the alias before the final scan, not at the state syscall. → Fail closed when the alias set or state-file identity cannot be bound to the mutation; preserve the state rather than make a pathname-only commit.

## F9 · BLOCKER · open
**Where:** `src/commands/uninstall.ts:480-483`
**Critic (r1):** Cleanup hashes an asset by pathname, then unlinks that pathname without revalidating its parent or inode. Replacing a checked parent with a symlink between the hash and unlink redirects deletion outside the canon and can erase an unrelated user file. → Bind unlink to a validated directory/entry, or refuse deletion when that cannot be guaranteed.

## F10 · BLOCKER · open
**Where:** `src/surfaces/adapters.ts:845-866`
**Critic (r1):** Any symlink in a skill mirror is treated as owned solely because its resolved target is somewhere under the canon. A user-created alias such as `my-shortcut -> .../skills/ai-debug` is therefore deleted by the machine sweep despite not being an installed mirror entry. → Remove only the exact generated name/target pairs (or otherwise prove ownership) and preserve other links.

### Verification results
- All nine focused entries passed their test cases but exited 1 in preload teardown because the four pre-existing `tests/.worktree-lifecycle-*` directories remain in the checkout.
- Full `bun test`: 1,579 passed, 16 skipped, 3 failed; failures were the same baseline test-hygiene artifacts plus the pre-existing `src/.DS_Store` architecture scan result. No test artifacts were removed.
- Source/tests not modified; only this review thread was appended.
