# Review thread · floating-core #4 · Make src/workflow/checkpoint.ts the single checkpoint state module

## Goal
One TypeScript module owns the checkpoint JSON schema, phases, transitions, the legacy reviewed_main reading and the brainstorm approval parser, and it is the only code in src/ that reads the checkpoint JSON.

## Acceptance
- S12: an old checkpoint JSON with awaiting-app-review and reviewed_main is read and translated; the next write stores reviewed_base and base_ref.
- Every phase and every transition of 6.5 has a passing and a refusing case.
- The arch test proves a single reader of the checkpoint JSON in src/.
- Existing worktree merge and request-changes tests still pass on the shared module.

## changed_files
- tests/workflow-checkpoint.spec.ts
- tests/arch.spec.ts
- .ai-engineering/arch.rules.json
- FILEMAP.md
- src/shared-worktree.ts
- src/workflow/checkpoint.ts

## Verify
- `bun test tests/workflow-checkpoint.spec.ts`
- `bun test tests/worktree-command.spec.ts`
- `bun test tests/worktree-lifecycle.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`
- `bun test --parallel=1`
