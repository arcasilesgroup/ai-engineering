---
name: ai-board-sync
description: "Use to update work item state on the project board at lifecycle phase transitions. Automatically invoked by /ai-brainstorm (refinement, ready), /ai-dispatch (in_progress), and /ai-pr (in_review). Also invoke manually for 'move this issue to in-review', 'update the board', 'mark as in progress', 'sync the work item state'. Fail-open: never blocks the calling workflow."
effort: medium
argument-hint: "<phase> <work-item-ref> [--comment <text>]"
tags: [board, sync, work-items]
---



# Board Sync

## Purpose

Updates work item state on the project board at each lifecycle transition. Called internally by other skills (ai-brainstorm, ai-dispatch, ai-pr) and by provider-side runbooks when they need to move an item through the configured lifecycle. Fail-open: never blocks the calling skill's workflow.

## When to Use

- Called automatically by `/ai-brainstorm` (refinement, ready transitions)
- Called automatically by `/ai-dispatch` (in_progress transition)
- Called automatically by `/ai-pr` (in_review transition)
- Manual override: `/ai-board-sync <phase> <ref>`

## Inputs

| Parameter | Required | Description |
|-----------|----------|-------------|
| phase | Yes | Lifecycle phase: `refinement`, `ready`, `in_progress`, `in_review`, `done` |
| work-item-ref | Yes | Work item reference: `#45` (GitHub issue) or `AB#100` (ADO) |
| --comment | No | Comment to add to the work item (e.g., spec reference, PR URL) |

## Process

1. **Read config** -- read `.ai-engineering/manifest.yml` `work_items` section:
   - `provider` -- determines which CLI to use
   - `state_mapping` -- maps lifecycle phase to provider-specific state name
   - `github_project` -- Projects v2 field IDs and option IDs (GitHub only)
   - `custom_fields` -- any custom fields to update per transition

2. **Validate** -- check that the requested phase has a mapping:
   - If `state_mapping.<phase>` is null: log info "State mapping not configured for <phase>, skipping", return success
   - If `github_project.number` is null and provider is github: check for labels fallback

3. **Update state** -- based on provider:

   **GitHub Projects v2** (primary):
   a. Get the project item ID for the issue:
      ```
      gh project item-list <number> --owner <org> --format json | jq '.items[] | select(.content.number == <issue_number>)'
      ```
   b. Update the status field:
      ```
      gh project item-edit --project-id <project_id> --id <item_id> --field-id <status_field_id> --single-select-option-id <option_id>
      ```

   **GitHub Labels** (fallback):
   a. Remove existing `status-*` labels:
      ```
      gh issue edit <number> --remove-label "status-refinement,status-ready,status-in-progress,status-in-review,status-done"
      ```
   b. Add new status label:
      ```
      gh issue edit <number> --add-label "status-<phase>"
      ```

   **Azure DevOps**:
   a. Update work item state:
      ```
      az boards work-item update --id <number> --state "<mapped_state>" -o json
      ```

4. **Add comment** (if --comment provided or if context available):
   - **GitHub**: `gh issue comment <number> --body "<comment>"`
   - **Azure DevOps**: `az boards work-item update --id <number> --discussion "<comment>"`
   - Include context: spec reference, PR URL, or transition reason

5. **Update custom fields** (if configured for this transition):
   - Read `custom_fields` from manifest for fields that should update on this phase
   - Example: set "Start Date" on `in_progress` transition, set "Target Date" on `ready`
   - Respect hierarchy policy: feature-level records remain read-only even if the provider exposes writable fields

6. **Return result** -- report success or failure to caller:
   - Success: `{ "status": "updated", "phase": "<phase>", "ref": "<ref>", "provider_state": "<mapped>" }`
   - Skipped: `{ "status": "skipped", "reason": "no state mapping configured" }`
   - Failed: `{ "status": "failed", "error": "<message>", "remediation": "<hint>" }`

## Fail-Open Protocol

This skill NEVER blocks the calling skill's workflow:

1. If provider CLI is not authenticated: log warning with `gh auth login` or `az login` hint, return success
2. If project item not found: log warning "Issue #N not found in project #M", return success
3. If field update fails: log warning with error details, return success
4. If network error: log warning, return success

The calling skill checks the return status for logging but NEVER stops its own execution based on board-sync failure.

## Lifecycle Phase Reference

| Phase | Trigger | Typical Caller |
|-------|---------|---------------|
| refinement | Work item fetched for brainstorm | ai-brainstorm (step 1) |
| ready | Spec written and approved | ai-brainstorm (step 4) |
| in_progress | Implementation begins | ai-dispatch (step 2.5) |
| in_review | PR created | ai-pr (step 12.5) |
| done | PR merged | GitHub/ADO automation (close rules) |

## Common Mistakes

- Blocking the calling skill when board-sync fails (violates fail-open)
- Using provider-specific state names instead of lifecycle phase names
- Not checking if state_mapping is configured before attempting update
- Attempting Projects v2 update without first looking up the project item ID

## Scripts

- `scripts/board-sync-github.sh <project-number> [--owner <org>]` -- query GitHub Projects v2 items and summarize work item states

## Integration

- **Called by**: `ai-brainstorm`, `ai-dispatch`, `ai-pr` (internal calls, not user-facing)
- **Reads**: `.ai-engineering/manifest.yml` (work_items section)
- **Writes**: external only (provider board state, work item comments)
- **Pair**: `/ai-board-discover` (discover writes the config this skill reads; run discover if sync fails)

$ARGUMENTS
