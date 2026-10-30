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
