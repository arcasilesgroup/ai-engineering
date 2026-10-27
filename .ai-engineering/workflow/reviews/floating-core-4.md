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

## F1 · MAJOR · fixed
**Where:** `src/shared-worktree.ts:1120`
**Critic (r1):** `request-changes` parses the checkpoint JSON again and preserves `reviewed_main` on its next write instead of serializing the normalized checkpoint. That contradicts CP4's legacy migration contract and leaves a second checkpoint parser outside the state module; the arch test misses it because it only recognizes direct `readFileSync` calls. Always serialize the normalized `nextPlan` through `serializeCheckpoint` and strengthen the reader assertion.
**Fixer (r1):** fixed — `request-changes` now always serializes normalized `nextPlan`; legacy item defaults make the canonical output rereadable, and the arch guard catches direct checkpoint JSON parsing · verify: targeted tests and arch ✓

## F2 · MAJOR · fixed
**Where:** `src/shared-worktree.ts:675`
**Critic (r1):** `lifecycleStatus` supplies `refs/heads/main` as the checkpoint context, so a legacy `reviewed_main` is translated to `base_ref: refs/heads/main`, not the detected base required by §6.5. Resolve and pass the actual base context here; add a non-main-base legacy fixture.
**Fixer (r1):** fixed — lifecycle listing and request-changes resolve the base with `resolveContext`; a diverged `develop` fixture verifies legacy translation · verify: targeted lifecycle and command tests ✓

## F3 · MAJOR · fixed
**Where:** `tests/workflow-checkpoint.spec.ts:398`
**Critic (r1):** The plan-approval transition is tested only as a refusal with pending approval; there is no passing `awaiting-plan-approval` → approved `implementation` case for the transition implemented at `src/workflow/checkpoint.ts:416`. Add the successful transition case to satisfy the acceptance requirement that each transition has passing and refusing coverage.
**Fixer (r1):** fixed — added a passing approved plan-approval transition assertion alongside the existing pending refusal · verify: targeted checkpoint tests ✓
- `bun test tests/worktree-lifecycle.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`
- `bun test --parallel=1`
