# Handler: Phase 6 -- DELIVER

## Purpose

Build the Integrity Report from Phase 4 Self-Reports and Phase 5 quality audit, deliver the full changeset via PR following the ai-pr SKILL.md, clean up autopilot state, and provide the Resume Protocol for mid-pipeline recovery.

## Prerequisites

- Phase 5 (QUALITY LOOP) is complete: either PASS (0 blockers/criticals/highs) or exhausted (round 3 reached with only criticals/highs remaining).
- Manifest at `.ai-engineering/specs/autopilot/manifest.md` has `## Quality Rounds` section with round log.
- Sub-spec directories exist at `.ai-engineering/specs/autopilot/sub-NNN/` with `plan.md` containing populated `## Self-Report` sections from Phase 4 implementation agents.
- Parent spec is available at `.ai-engineering/specs/spec.md`.

## Procedure

### Step 1: Build Transparency Report

1. Glob `.ai-engineering/specs/autopilot/sub-*/plan.md`. For each sub-spec, read the `## Self-Report` section. Extract per-file/function classifications: real, aspirational, stub, failing, invented, hallucinated.
2. Read the manifest's `## Quality Rounds` section. Extract the consolidated findings from Phase 5: final state (CLEAN or remaining issues with severity breakdown), number of rounds executed, and per-round summaries.
3. If any sub-specs have status `blocked` or `cascade-blocked` in the manifest: collect their ID, title, scope, and blocking reason. These form the "Blocked / Undelivered" section.
4. Aggregate all classifications across sub-specs into totals. Cross-reference against quality findings -- a file classified as "real" in a Self-Report but failing checks in Phase 5 should be reclassified as "failing".
5. Produce the `## Integrity Report` section:

```markdown
## Integrity Report

### Summary
- Real: N files/functions (fully implemented and verified)
- Aspirational: N (implemented, not fully tested)
- Stub: N (placeholder, needs completion)
- Failing: N (implemented but failing checks)
- Invented: N (not in spec, added by agents)
- Hallucinated: N (referenced non-existent things -- fixed or flagged)

### Quality Convergence
- Rounds: N/3
- Final state: CLEAN | N remaining issues (severity breakdown)

### Blocked / Undelivered
[Only present if blocked sub-specs exist]
- sub-NNN: [title] -- blocked: [reason]
- sub-MMM: [title] -- cascade-blocked by sub-NNN

### Details
| File | Function | Classification | Evidence | Notes |
|------|----------|----------------|----------|-------|
| path/to/file.py | ClassName.method | real | tests pass, lint clean | |
| path/to/other.py | helper_func | stub | raises NotImplementedError | Needs real impl |
| path/to/new.py | util | invented | not in spec | Added for DRY |
```

Classification rules:
- **Real**: tests pass AND lint clean AND in spec scope.
- **Aspirational**: implementation exists but test coverage is incomplete or tests are not fully passing.
- **Stub**: placeholder implementation (raises `NotImplementedError`, returns hardcoded values, or contains TODO markers).
- **Failing**: implementation exists but fails lint, type check, or test assertions.
- **Invented**: not traceable to any spec requirement. Added by an agent for utility, DRY, or structural reasons.
- **Hallucinated**: references non-existent modules, functions, or APIs. Fixed during quality loop or flagged for manual resolution.

### Step 2: Deliver PR

This step follows the thin orchestrator principle. Do NOT duplicate PR logic.

1. Read `.claude/skills/ai-pr/SKILL.md`. Follow its FULL procedure -- all steps, in order. Note: ai-pr Step 7 dispatches 2 consolidated documentation subagents (CHANGELOG+README, docs-portal+quality-gate) rather than 5 separate agents.
2. The PR body MUST include the following sections in addition to the standard ai-pr structure:
   - The `## Integrity Report` from Step 1 as a dedicated section.
   - A `## Sub-Spec Completion` table:
     ```markdown
     ## Sub-Spec Completion
     | # | Title | Status | Wave |
     |---|-------|--------|------|
     | sub-001 | [title] | complete | 1 |
     | sub-002 | [title] | complete | 1 |
     | sub-003 | [title] | blocked | -- |
     ```
   - Standard PR sections (Summary, Test Plan, Checklist) per ai-pr protocol.
3. Enable auto-complete with squash merge per ai-pr Step 15.
4. Enter the watch-and-fix loop per ai-pr Step 16, unless `--no-watch` flag was passed. If `--no-watch`: skip the loop and proceed directly to Step 3 (Cleanup).

### Step 3: Cleanup

Execute after the PR merges (detected by the watch loop), or immediately after PR creation if `--no-watch` was passed.

1. **Delete autopilot directory**:
   ```
   rm -rf .ai-engineering/specs/autopilot/
   ```

2. **Clear `.ai-engineering/specs/spec.md`** with:
   ```markdown
   # No active spec

   Run /ai-brainstorm to start a new spec.
   ```

3. **Clear `.ai-engineering/specs/plan.md`** with:
   ```markdown
   # No active plan

   Run /ai-plan after brainstorm approval.
   ```

4. **Add entry to `specs/_history.md`** with the spec ID, title, date, and PR number. If `_history.md` does not exist, create it with this header first:
   ```markdown
   # Spec History

   Completed specs. Details in git history.

   | ID | Title | Status | Created | Branch |
   |----|-------|--------|---------|--------|
   ```
   Then append the new entry row to the table.

5. **Verify cleanup** (lesson from spec-056): re-read `.ai-engineering/specs/spec.md` and `.ai-engineering/specs/plan.md` after clearing. If either file still contains old spec content (anything other than the placeholder text), clear it again. This is a hard verification -- do not trust the write succeeded without reading back.

6. **Stage and commit** all cleanup changes:
   ```
   chore: clear autopilot state after spec-NNN delivery
   ```

### Step 4: Final Report

Print the completion summary to the user:

```
Autopilot Complete!

Spec: spec-NNN -- [title]
Sub-specs: N completed, M blocked
Waves: W executed
Quality rounds: R/3
PR: #NNN (merged|pending)
Integrity: N real, N aspirational, N stub, N failing, N invented, N hallucinated
```

Field sources:
- **Spec**: from `.ai-engineering/specs/spec.md` frontmatter (read before cleanup clears it).
- **Sub-specs**: count from manifest. "completed" = status `complete`. "blocked" = status `blocked` or `cascade-blocked`.
- **Waves**: count from manifest's `## Execution DAG` section.
- **Quality rounds**: from manifest's `## Quality Rounds` section.
- **PR**: number from the PR creation step. State is "merged" if watch loop confirmed merge, "pending" if `--no-watch` was used.
- **Integrity**: totals from the Integrity Report built in Step 1.

## Resume Protocol

When the autopilot is invoked with `--resume`, read `.ai-engineering/specs/autopilot/manifest.md` and re-enter the pipeline at the correct phase. Resume NEVER re-executes completed phases. The manifest is the single source of truth for all resume decisions.

### Resume Decision Logic

Read the manifest. Inspect sub-spec statuses, section presence, and wave completion state. Apply the first matching rule:

1. **All sub-specs are `planning`**: Phase 2 (DEEP PLAN) never completed. Re-enter at Phase 2 by reading `handlers/phase-deep-plan.md` and executing from the start.

2. **`## Execution DAG` section is missing**: Phase 3 (ORCHESTRATE) never completed. Re-enter at Phase 3 by reading `handlers/phase-orchestrate.md` and executing from the start.

3. **Some waves are `implemented` and others are not**: Phase 4 (IMPLEMENT) was interrupted mid-execution. Identify the first incomplete wave (a wave where not all sub-specs are `complete`, `blocked`, or `cascade-blocked`). Re-enter Phase 4 at that wave. Skip all completed waves -- do not re-dispatch their agents.

4. **All waves are `implemented` but `## Quality Rounds` section is absent**: Phase 5 (QUALITY LOOP) never started. Re-enter at Phase 5 by reading `handlers/phase-quality.md` and executing from the start.

5. **`## Quality Rounds` exists but pipeline stopped** (e.g., blockers after round 3 that have since been manually resolved, or a crash during the quality loop): Re-enter at Phase 5 for another attempt. Reset the round counter to 0. The quality loop starts fresh but operates on the current state of the codebase.

6. **Quality passed but PR not created**: Phase 6 delivery was interrupted before the PR was created. Re-enter at Phase 6 Step 2 (Deliver PR). Skip the Integrity Report build only if `## Integrity Report` already exists in the manifest -- otherwise, start from Step 1.

### Resume Safeguards

- Never re-execute a phase whose artifacts are already complete and valid.
- If the manifest is missing or corrupted (unparseable): STOP. Report: "Manifest is missing or corrupted. Cannot resume. Inspect `.ai-engineering/specs/autopilot/manifest.md` manually."
- If the manifest exists but no sub-specs files are found: STOP. Report: "Manifest exists but sub-spec files are missing. Pipeline state is inconsistent."
- After determining the re-entry point, report to the user before proceeding:
  ```
  Resume: re-entering at Phase N ([phase name]).
  Reason: [why this phase was selected].
  Completed phases: [list of phases that will be skipped].
  ```

## Output

- PR created with Integrity Report, Sub-Spec Completion table, and standard ai-pr sections.
- Autopilot state cleaned: `.ai-engineering/specs/autopilot/` deleted, `.ai-engineering/specs/spec.md` and `.ai-engineering/specs/plan.md` cleared.
- Entry added to `specs/_history.md`.
- Final report printed to user.

## Failure Modes

| Condition | Action |
|-----------|--------|
| PR creation fails (VCS error, auth failure, network) | STOP and report the error. Do NOT retry PR creation -- VCS errors require user diagnosis. The Integrity Report and changeset are preserved in the branch. |
| Watch loop escalates (same check fails 3 times) | STOP per ai-pr handler protocol (Step 14 / `handlers/watch.md`). Report which check is failing and the 3 attempts made. PR remains open for manual intervention. |
| Cleanup fails (file write error, permission denied) | Warn but do NOT block. The PR is already delivered -- cleanup is best-effort. Report which cleanup step failed so the user can run it manually. |
| `_history.md` does not exist | Create it with the standard header (see Step 3.4), then add the entry. This is not a failure -- it is expected on first autopilot delivery. |
| Manifest missing or corrupted on `--resume` | STOP. Report: "Manifest is missing or corrupted. Cannot resume." Do not guess pipeline state. |
| Sub-spec files missing on `--resume` | STOP. Report: "Sub-spec files missing. Pipeline state inconsistent." Do not proceed with partial data. |
| Integrity Report aggregation finds zero Self-Reports | STOP. Phase 4 did not complete properly. Report: "No Self-Reports found in sub-specs. Phase 4 may not have completed. Run `--resume` to re-evaluate pipeline state." |
