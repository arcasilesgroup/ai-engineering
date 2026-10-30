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
