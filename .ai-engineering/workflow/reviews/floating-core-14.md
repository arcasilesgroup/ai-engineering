# Checkpoint 14 review

## Goal

Test consolidation and fixture hygiene preserve every behavior assertion, including S11 and orchestrator phase/gate checks, while the serial suite passes twice in a row under 180 seconds.

## Acceptance

- The serial suite passes twice in a row, each run under 180 seconds.
- S11 and the orchestrator phase/gate assertions are kept.

## changed_files

- `tests/skills.spec.ts`
- `tests/workflow-handoff.spec.ts`
- `tests/ai-pr.spec.ts`
- `tests/worktree-command.spec.ts`
- `tests/worktree-lifecycle.spec.ts`
- `tests/doctor-command.spec.ts`
- `tests/adversarial/init-recovery.test.ts`
- `tests/test-hygiene.spec.ts`
- `tests/preload.ts`
- `tests/fixtures/worktree-command.ts`
- `tests/checkpoint-guard.spec.ts`
- `tests/floor-hooks.spec.ts`

## Verify

- `bun test tests/ai-pr.spec.ts`
- `bun test tests/skills.spec.ts`
- `bun test tests/workflow-handoff.spec.ts`
- `bun test tests/worktree-command.spec.ts`
- `bun test tests/worktree-lifecycle.spec.ts`
- `bun test tests/doctor-command.spec.ts`
- `bun test ./tests/adversarial/init-recovery.test.ts`
- `bun test tests/test-hygiene.spec.ts`
- `bun test tests/checkpoint-guard.spec.ts`
- `bun test tests/floor-hooks.spec.ts`
- `bun test tests/ceremony-contract.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`
- `sh -c 'start=$(date +%s); bun test --parallel=1 && [ $(( $(date +%s) - start )) -lt 180 ]'`
- `sh -c 'start=$(date +%s); bun test --parallel=1 && [ $(( $(date +%s) - start )) -lt 180 ]'`

## Round 1 findings

- **F1 — Major:** The `Next` assertion that `ai-brainstorm` routes to `ai-orchestrator` was removed from `tests/skills.spec.ts`, and the matching `ai-brainstorm Lifecycle names ai-orchestrator` test was also removed from `tests/workflow-handoff.spec.ts`. Remaining G13 and U34 checks do not assert this `Next` link, so a broken standard-lane handoff would pass.
- **F2 — Minor:** `tests/adversarial/init-recovery.test.ts` now checks only that the missing global skill file exists after update. An empty or incorrect replacement passes; assert the repaired payload (or doctor’s missing/drift state) while retaining the local-edit preservation assertion.
- **VERDICT: FAIL** — F1 remains major; no blocker beyond F1. The two serial commands are full-suite runs with the same `<180s` ceiling, and both passed in the target worktree.

## Round 1 fixer response

- ROOT CAUSE: The handoff route was dropped from the dedicated workflow-boundary tests, while canon recovery asserted presence rather than payload integrity.
- FIX: Assert the standard `Next` route in `workflow-handoff.spec.ts`; compare the repaired core skill to its shipped payload while retaining local-edit preservation.
- LESSON: Keep workflow-link assertions at the handoff boundary and verify repaired payloads byte-for-byte.
