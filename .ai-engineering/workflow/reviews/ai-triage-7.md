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
