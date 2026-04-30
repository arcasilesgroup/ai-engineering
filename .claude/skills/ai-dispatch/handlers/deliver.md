# Handler: Phase 4 -- DELIVER

## Purpose

Deliver the dispatch changeset via PR. Build a lightweight Quality Report from Phase 3 results, delegate to ai-pr for the actual PR workflow, clean up spec state, and report completion.

## Prerequisites

- Phase 3 (Quality Check) is complete: either PASS (0 blockers/criticals/highs) or exhausted (max rounds reached with only non-blocking issues remaining).
- All task statuses in `specs/plan.md` are `DONE` or `DONE_WITH_CONCERNS` (no `BLOCKED` tasks that would prevent delivery).
- Branch has commits from per-task execution and per-quality-round fixes.

## Procedure

### Step 1: Build Quality Report

Produce a concise quality summary from Phase 3 results. This is NOT the full Integrity Report from autopilot -- it is a lightweight summary suitable for the PR body.

1. Count quality rounds executed and determine final state (CLEAN or remaining issues with severity breakdown).
2. Run `git diff main...HEAD --stat` to capture the changeset summary.
3. Produce the report:

```markdown
## Quality Report
- Rounds: N/2
- Final: CLEAN | N remaining issues (severity breakdown)
- Changeset: `git diff main...HEAD --stat` summary
```

### Step 2: Deliver PR

This step follows the thin orchestrator principle. Do NOT duplicate PR logic.

1. Read `.claude/skills/ai-pr/SKILL.md`.
2. Determine entry point:
   - If unstaged changes exist (e.g., quality report files, late fixes): execute the full ai-pr pipeline starting from Step 0 (commit pipeline through Steps 0-6).
   - If all changes are already committed: **start from Step 9** (pre-push checks). Dispatch already commits per-task and per-quality-round, so this is the normal path.
3. The PR body MUST include the following sections:
   - Standard ai-pr sections: Summary, Test Plan, Work Items, Checklist.
   - The `## Quality Report` from Step 1 as a dedicated section.
4. Enable auto-complete with squash merge per ai-pr Step 15.
5. Enter the watch-and-fix loop per ai-pr Step 16, unless dispatch was invoked with `--no-watch`. If `--no-watch`: skip the loop and proceed directly to Step 3 (Cleanup).

### Step 3: Cleanup

Execute after the PR merges (detected by the watch loop), or immediately after PR creation if `--no-watch` was passed.

1. **Clear `specs/spec.md`** with:
   ```markdown
   # No active spec

   Run /ai-brainstorm to start a new spec.
   ```

2. **Clear `specs/plan.md`** with:
   ```markdown
   # No active plan

   Run /ai-plan after brainstorm approval.
   ```

3. **Add entry to `specs/_history.md`** with the spec ID, title, date, and branch name. If `_history.md` does not exist, create it with this header first:
   ```markdown
   # Spec History

   Completed specs. Details in git history.

   | ID | Title | Status | Created | Branch |
   |----|-------|--------|---------|--------|
   ```
   Then append the new entry row to the table.

4. **Verify cleanup**: re-read `specs/spec.md` and `specs/plan.md` after clearing. If either file still contains old spec content (anything other than the placeholder text), clear it again. Do not trust the write succeeded without reading back.

5. **Stage and commit** all cleanup changes:
   ```
   chore: clear spec state after dispatch delivery
   ```

### Step 4: Final Report

Print the completion summary to the user:

```
Dispatch Complete!

Spec: spec-NNN -- [title]
Tasks: N completed, M with concerns
Quality rounds: R/2
PR: #NNN (merged|pending)
```

Field sources:
- **Spec**: from `specs/spec.md` frontmatter (read before cleanup clears it).
- **Tasks**: count from `specs/plan.md`. "completed" = status `DONE`. "with concerns" = status `DONE_WITH_CONCERNS`.
- **Quality rounds**: from Phase 3 execution log.
- **PR**: number from the PR creation step. State is "merged" if watch loop confirmed merge, "pending" if `--no-watch` was used.

## Resume Protocol

When dispatch is invoked with `--resume` and the pipeline is at the deliver phase:

1. **PR exists**: check for an open PR on the current branch.
   - If found: enter the watch-and-fix loop (ai-pr Step 16). Skip Steps 1-2.
   - If merged: proceed to Step 3 (Cleanup).
2. **PR does not exist**: start from Step 1 (Build Quality Report) and execute the full deliver procedure.

Resume NEVER re-executes completed phases. The plan.md task statuses are the source of truth for resume decisions.

## Failure Modes

| Condition | Action |
|-----------|--------|
| PR creation fails (VCS error, auth failure, network) | STOP and report the error. Do NOT retry PR creation -- VCS errors require user diagnosis. The changeset is preserved in the branch. |
| Watch loop escalates (same check fails 3 times) | STOP per ai-pr handler protocol (Step 14). Report which check is failing and the 3 attempts made. PR remains open for manual intervention. |
| Cleanup fails (file write error, permission denied) | Warn but do NOT block. The PR is already delivered -- cleanup is best-effort. Report which cleanup step failed so the user can run it manually. |
| `_history.md` does not exist | Create it with the standard header (see Step 3.3), then add the entry. This is expected on first dispatch delivery. |
| Pre-push checks fail (Step 9 via ai-pr) | STOP and report. Quality issues that slip past Phase 3 must be resolved before delivery. Do not force-push or skip checks. |
