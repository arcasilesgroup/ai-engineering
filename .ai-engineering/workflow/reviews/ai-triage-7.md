# Checkpoint ai-triage#7 adversarial review

**Goal:** Preserve the previous report byte-for-byte on partial temporary-write and replacement failures, while cleaning up only temporary files owned by the writer.

**Acceptance:** Successful replacement publishes the complete report; injected partial-write and replacement failures leave prior bytes unchanged; cleanup removes only owned temporary files.

**changed_files:** `skills/ai-triage/scripts/render-report.mjs`, `tests/triage-report.integration.spec.ts`

**Verify:** `bun test tests/triage-report.integration.spec.ts`; `bun run typecheck`; `bun run lint`

## Round 1 — VERDICT: FAIL

### F1 — open (P1): temp-path substitution defeats ownership checks
- `render-report.mjs:596-599` renames or unlinks by pathname after closing the handle, trusting `ownsTemporaryFile` even if another writer replaced that path. A synthetic `replaceFile` probe replaced the staged path with another writer's bytes: on rejection cleanup deleted that file; on successful rename the writer resolved but published those bytes instead of the complete report.
- `triage-report.integration.spec.ts:519-563` preserves an unrelated `.other-writer.tmp`, but its failure hooks never replace the staged path. It therefore does not establish ownership under a same-path race.
- Fix the stage-to-replace/cleanup path so the staged file's identity cannot be substituted; add synthetic same-path substitution tests covering both rejection cleanup and successful publication.

**Checks:** `bun test tests/triage-report.integration.spec.ts` — 16 passed; `bun run typecheck` and `bun run lint` exited 0 with warnings; both synthetic path-substitution probes reproduced F1. No Azure/GitHub calls or code edits.

## Round 1 response — VERDICT: PASS

### F1 — closed
- **Root cause:** Temporary-path cleanup and publication did not verify that the path still named the file opened by this writer.
- **Fix:** Stage under a private unique directory, retain the opened handle until atomic rename, compare device/inode before rename, and clean up only the matching file. The replacement test hook now runs before the guarded native rename.
- **Regression tests:** Synthetic substitutions immediately before cleanup and replacement both preserve the previous report and keep foreign temporary bytes intact; successful replacement still publishes the complete report.
- **Files:** `skills/ai-triage/scripts/render-report.mjs`, `skills/ai-triage/scripts/render-report.d.mts`, `tests/triage-report.integration.spec.ts`, `LEARNINGS.md`.
- **Checks:** `bun test tests/triage-report.integration.spec.ts` — 18 passed; `bun run typecheck` — passed with existing warnings; `bun run lint` — passed with existing warnings; `git diff --check` — passed.
- No live calls or real data used. No commit created.

## Round 2 — VERDICT: PASS

### F1 — closed
- `atomicWriteReport` now stages in a unique `mkdtemp` directory, captures the opened file's device/inode, waits for write and sync, then checks that identity before native rename. On failure, cleanup unlinks only a matching staged file; foreign substitutions leave both the previous report and foreign bytes intact.
- Synthetic tests exercise substitutions during cleanup and before replacement, partial-write and replacement-stage failures, and successful full-content publication. The targeted suite passed 18/18 tests (192 assertions); typecheck and lint exited 0 with warnings.
- No live calls or code edits.
