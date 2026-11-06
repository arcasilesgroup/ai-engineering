# Adversarial review — floating-core#19 machine-state aliases

## Goal
Preserve user-owned settings and machine state when settings paths can alias `machine.json`.

## Acceptance
- Any settings symlink or hard link to `machine.json`, including an unselected surface, causes machine-state mutation to be refused with a warning.
- A settings alias replaced at the mutation boundary is preserved; neither its target nor `machine.json` is overwritten or deleted.
- Local canon installation and configuration continue when machine-state mutation is refused.

## changed_files
- src/commands/init-shared.ts
- src/commands/uninstall.ts
- src/embed.ts
- src/surfaces/adapters.ts
- tests/adversarial/carrier-merge.test.ts
- tests/adversarial/lock-security.test.ts
- tests/carriers-install.spec.ts
- tests/init-command.spec.ts
- tests/uninstall-command.spec.ts
- tests/update-command.spec.ts
- tests/config-command.spec.ts
- tests/surfaces.test.ts
- tests/adversarial/init-recovery.test.ts
- .ai-engineering/workflow/test-plans/floating-core.json
- LEARNINGS.md
- .ai-engineering/workflow/reviews/floating-core-19-machine-state.md

## verify
- bun test tests/adversarial/carrier-merge.test.ts
- bun test tests/carriers-install.spec.ts
- bun test tests/uninstall-command.spec.ts
- bun test tests/init-command.spec.ts
- bun test tests/update-command.spec.ts
- bun test tests/config-command.spec.ts
- bun test tests/surfaces.test.ts
- bun test tests/adversarial/lock-security.test.ts
- bun test tests/adversarial/init-recovery.test.ts
- bun test
