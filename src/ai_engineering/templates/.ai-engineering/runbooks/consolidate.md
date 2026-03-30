---
name: consolidate
description: "Group related work items into consolidated tasks ready for brainstorm"
type: operational
cadence: weekly
---

# Work Item Consolidation

## Objetivo

Reduce board noise by identifying duplicate, overlapping, or closely related work items and consolidating them into a single well-described task. The consolidated task is structured as a draft brainstorm input, ready for `/ai-brainstorm` to refine into a spec. Runs weekly and requires user confirmation before any mutations.

## Precondiciones

- Work items provider configured in `manifest.yml` (`github` or `azure_devops`)
- CLI access: `gh` for GitHub, `az` for Azure DevOps
- `work-item-audit` has already run in the current weekly hygiene cycle; consolidate assumes invalid noise has been removed first
- At least 5 open work items in the backlog (below this threshold, manual review is more efficient)

## Procedimiento

### Step 1 -- Fetch all open work items

Retrieve the full set of open, unconsolidated items from the configured provider.

**GitHub:**

```bash
gh issue list --state open --json number,title,body,labels,assignees,createdAt --limit 200 --jq '[.[] | select(.labels | map(.name) | any(. == "consolidated") | not)]'
```

**Azure DevOps:**

```bash
az boards query --wiql "SELECT [System.Id], [System.Title], [System.Description], [System.Tags], [System.AssignedTo], [System.CreatedDate], [System.State] FROM WorkItems WHERE [System.State] <> 'Closed' AND [System.State] <> 'Removed' AND NOT [System.Tags] CONTAINS 'consolidated' ORDER BY [System.CreatedDate] ASC" --output json
```

Store the result set as `$ITEMS`. Record the count for the summary report. If the count is below 5, halt with a message explaining that manual review is more efficient at this scale.

### Step 2 -- Semantic grouping

Analyze all fetched items and group by semantic similarity. Apply these grouping heuristics in order:

1. **Title and description overlap.** Compare normalized tokens across titles and bodies. Pairs exceeding 0.6 similarity are candidates.
2. **Label and tag affinity.** Items sharing two or more non-trivial labels (excluding `triaged`, `needs-refinement`, `team:*`) are candidates.
3. **Root-cause convergence.** Items that describe different symptoms of the same underlying problem, identified by shared code paths, error messages, or affected modules.
4. **Sub-task aggregation.** Items that are individually small but collectively describe a larger untracked concern.

A group must contain at least 2 items. Single items are never consolidated.

Present proposed groupings in this format:

```
Group 1: "Authentication session management" (3 items)
  - #12: "Fix login timeout on slow connections"
  - #15: "Session token refresh fails after 24h"
  - #23: "Auth middleware stores tokens incorrectly"
  Rationale: All three address authentication session lifecycle -- timeout
             handling, token refresh, and storage. A single consolidated task
             can define the session management contract holistically.

Group 2: "API response schema standardization" (2 items)
  - #8: "GET /users returns different format than POST"
  - #31: "Error responses missing error_code field"
  Rationale: Both address inconsistent API response shapes. Consolidating
             enables a single schema-first approach across all endpoints.

Ungrouped: 31 items (no consolidation candidates found)
```

### Step 3 -- User confirmation

Present each group individually and wait for explicit confirmation. Accepted responses:

| Response | Action |
|----------|--------|
| **CONFIRM** | Proceed with consolidation for this group |
| **SPLIT** | Break the group into smaller sub-groups (re-present for confirmation) |
| **SKIP** | Leave all items in this group as-is |
| **MERGE** | Combine this group with another named group |

No mutations occur until every group has a disposition. If all groups are skipped, halt with a clean summary and zero mutations.

### Step 4 -- Create consolidated task

For each confirmed group, create one new work item. The body is structured as a draft brainstorm input so that `/ai-brainstorm` can refine it directly into a spec.

**GitHub:**

```bash
gh issue create \
  --title "[consolidated] <group_title>" \
  --body "## Problem Statement
<Synthesized from all original items -- what is the root problem?>

## Requirements
<Extracted from each original item, deduplicated and organized>
- From #12: <requirement>
- From #15: <requirement>
- From #23: <requirement>

## Affected Areas
<Code paths, modules, or systems mentioned across all items>

## Acceptance Criteria (Draft)
- [ ] <criterion 1>
- [ ] <criterion 2>
- [ ] <criterion 3>

## Original Items
- #12: <title> (will be closed, consolidated here)
- #15: <title> (will be closed, consolidated here)
- #23: <title> (will be closed, consolidated here)

## Notes for Brainstorm
<Contradictions, edge cases, or open questions identified during consolidation>" \
  --label "consolidated" \
  --label "$DOMAIN_LABEL_1" --label "$DOMAIN_LABEL_2" ...
```

The `$DOMAIN_LABEL_N` values are the union of domain-specific labels from the grouped originals (e.g., `tech-debt`, `architecture-drift`, `security-finding`). Exclude generic labels (`triaged`, `needs-refinement`, `needs-triage`, `handoff-ai-eng`, `needs-clarification`, `needs-review`, priority labels). This ensures the consolidated issue is discoverable by the dedup handler (`handlers/dedup-check.md`).

**Azure DevOps:**

```bash
az boards work-item create --type Task \
  --title "[consolidated] <group_title>" \
  --description "<body_as_above>" \
  --fields "System.Tags=consolidated;$DOMAIN_TAG_1;$DOMAIN_TAG_2" \
  --area "Project\\TeamName"
```

Record the new item number as `$NEW_NUMBER` for the linking step.

### Step 5 -- Link and close originals

For each original item in the confirmed group, leave an audit trail and close:

**GitHub:**

```bash
# Comment with forward link
gh issue comment "$NUMBER" --body "Consolidated into #$NEW_NUMBER. All requirements have been preserved in the consolidated task.

<!-- consolidate-runbook:linked -->"

# Add label
gh issue edit "$NUMBER" --add-label "consolidated"

# Close
gh issue close "$NUMBER"
```

**Azure DevOps:**

```bash
# Add relation link
az boards work-item relation add --id "$ID" --target-id "$NEW_ID" --relation-type "Related"

# Comment and close
az boards work-item update --id "$ID" \
  --state Closed \
  --fields "System.Tags=consolidated" \
  --discussion "Consolidated into AB#$NEW_ID. All requirements preserved in the consolidated task."
```

### Step 6 -- Generate report

Produce a summary to stdout:

```
=== Work Item Consolidation Report ===
Date:              2026-03-28T00:00:00Z
Items scanned:     45
Groups proposed:   6
Groups confirmed:  4
Groups skipped:    2
Items consolidated: 14
New tasks created:  4
Items unchanged:   31

Mutations used:    18 / 15 (3 deferred to next run)

Confirmed groups:
  1. "Authentication session management" -> #201 (3 items)
  2. "API response schema standardization" -> #202 (2 items)
  3. "CI pipeline reliability" -> #203 (4 items)
  4. "Documentation coverage gaps" -> #204 (5 items)

Skipped groups:
  5. "Logging improvements" (2 items) -- user: SKIP
  6. "Mobile layout issues" (3 items) -- user: SKIP

Deferred mutations (will run next cycle):
  - Close #45: "Flaky test in auth suite"
  - Close #67: "CI timeout on large repos"
  - Close #89: "Pipeline fails on Windows"
```

When the mutation cap is reached mid-group, finish creating the consolidated task but defer the remaining close operations. Report deferred items explicitly so the next run can complete them.

## Output

Summary report to stdout. Consolidated work items created, originals closed with forward links. No local files are written.

## Guardrails

1. **Never deletes items.** Only closes with a forward link to the consolidated task. Recovery is trivial: reopen the original and remove the `consolidated` label.
2. **Always confirms before acting.** Groupings are proposed and require explicit user confirmation. No mutations occur without a CONFIRM response.
3. **Bounded mutations.** Maximum 15 mutations per run. Overflow is reported and deferred to the next cycle. Each close counts as one mutation; each create counts as one mutation.
4. **Protected states.** Items in `closed`, `resolved`, or `removed` state are never touched. Items with labels `pinned`, `p1-critical`, or `security` are excluded from grouping.
5. **Idempotent.** Before creating a consolidated task, search for existing open items with `[consolidated]` in the title covering the same original items. If found, skip creation and report the existing task.
6. **Audit trail.** Every closed item gets a comment linking to the consolidated task. The consolidated task body lists all originals with their titles.
7. **Never modifies existing item content.** Original item titles, bodies, and non-consolidated labels are never changed. The `consolidated` label plus domain-specific labels from grouped originals are added to the new consolidated issue.
8. **Never assigns items.** Assignment is a refinement concern, not a consolidation concern.
