# worktree-lifecycle-awareness checkpoint 4 review

## Goal
Initialize explicit `approval-before-start` lifecycle evidence only after successful AI Engineering worktree creation.

## Acceptance
- New records have the matching slug, schema version, timestamp, and `approval-before-start` state.
- Failed Git creation leaves no record; persistence failure reports partial creation without success-shaped output.
- Existing worktrees and explicit human-directed transitions remain unchanged.

## Changed files
- `src/shared-worktree.ts`
- `tests/worktree-command.spec.ts`
- `LEARNINGS.md`

## Verify commands
- `CI=true bun test ./tests/worktree-command.spec.ts`
- `CI=true bun test`
- `bun run typecheck`
- `bun run lint`
- `bun run build`
- `bun run arch`

## Round 1 — Adversarial review

**Verdict: PASS.** No checkpoint-4 findings.

The creation path writes `approval-before-start` only after Git succeeds, and uses the serialized `mustBeAbsent` write to avoid replacing lifecycle evidence. On persistence failure it returns a nonzero partial-creation error with no success output. CLI tests assert the exact successful record and timestamp, Git failure leaves no record, and simulated record-write failure reports the created path without success-shaped output. Existing explicit lifecycle transitions are unchanged.
