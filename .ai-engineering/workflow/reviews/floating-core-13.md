# Checkpoint 13 review

## Goal

Existing installs without `[canon] packs` adopt all six packs on their first update, explicit pack choices remain selected, and local edits stay protected.

## Acceptance

- The first update of an existing install keeps all six packs and removes none.
- An update preserves explicitly selected packs.
- A locally edited skill remains protected by its lock hash.

## changed_files

- `src/commands/update.ts`
- `src/embed.ts`
- `src/env.ts`
- `src/surfaces/adapters.ts`
- `tests/update-command.spec.ts`

## Verify

- `bun test tests/update-command.spec.ts`
- `bun run build`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`

## Round 1 findings

- **F13-1 — MAJOR — `src/commands/update.ts:154-155`, `src/surfaces/adapters.ts:175-179`, `src/embed.ts:213-216`:** A local edit to any selected canon skill makes `canonDrift` trigger `installCanon`, which unconditionally rewrites every selected skill. These machine-side files are not entries in `planEntries` or the project lock, so the recorded-hash protection tested by `syncPlan` is not on this path. The current skill test fabricates a `syncPlan` entry and does not exercise `updateMain`; preserve the edited canon file or route it through hash-aware conflict handling.
- **F13-2 — MINOR — `tests/update-command.spec.ts:341-368`:** The update integration coverage tests only an absent `[canon] packs` key. No update test proves explicit `[]` or partial selections remain selected, despite that distinction being a prior regression; exercise both through `updateMain`.

**Verdict: FAIL** — F13-1 major remains. The listed verification commands pass.

## Round 1 fixer response

- **ROOT CAUSE:** `updateMain` treated any aggregate canon drift as permission to reinstall every selected skill; the project lock does not own machine-side canon files.
- **FIX:** Update now preserves existing canon skills whose hashes differ from the selected payload and reports them as kept. Added an update integration test for an edited selected pack skill and coverage for explicit empty and partial pack selections.
- **LESSON:** Without a machine-side ownership hash, preserve differing canon files instead of treating them as disposable.
- **Verification:** `bun test ./tests/update-command.spec.ts` (18 pass), `bun test ./tests/embed-canon.spec.ts` (15 pass), and `bun run typecheck` passed. Full serial suite not run.
