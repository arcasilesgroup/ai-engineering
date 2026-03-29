---
name: triage
description: "Scan open issues and backlog, classify by type and priority, detect duplicates, discard noise, label triaged items for refinement"
type: intake
cadence: daily
---

# Triage Runbook

## Objetivo

Scan all open issues and backlog items across GitHub and Azure DevOps, classify each by type and priority, detect duplicates, discard noise, and label triaged items for refinement. Mutations are applied automatically. It runs daily on any of the four registered hosts.

## Precondiciones

- Authenticated CLI session: `gh auth status` (GitHub) or `az account show` (Azure DevOps).
- Repository cloned locally with issue-tracker access (issues:write permission for GitHub, Work Items Read & Write for Azure DevOps).
- Labels `bug`, `feature`, `enhancement`, `question`, `chore`, `p1-critical`, `p2-high`, `p3-normal`, `p4-low`, `triaged`, `needs-refinement`, and `duplicate` exist in the issue tracker.

## Procedimiento

### Step 1 -- Fetch open issues

**GitHub:**

```bash
gh issue list --state open --limit 500 --json number,title,body,labels,createdAt,author,comments --jq '.[] | select(.labels | map(.name) | any(. == "triaged", startswith("p1-"), startswith("p2-"), startswith("p3-"), startswith("p4-")) | not)'
```

**Azure DevOps:**

```bash
az boards query --wiql "SELECT [System.Id], [System.Title], [System.Description], [System.Tags], [System.CreatedDate], [System.CreatedBy], [System.State] FROM WorkItems WHERE [System.State] = 'New' AND [System.Tags] NOT CONTAINS 'triaged' ORDER BY [System.CreatedDate] ASC" --output json
```

Store the result set as `$ISSUES`. Record the count for the summary report.

### Step 2 -- Classify each issue by type

For each issue in `$ISSUES`, inspect the title, body, and existing labels. Assign exactly one type:

| Type | Signal keywords / patterns |
|------|---------------------------|
| bug | error, crash, fail, broken, regression, stack trace, unexpected |
| feature | add, new, support, implement, introduce, enable |
| enhancement | improve, optimize, refactor, update, better, upgrade |
| question | how, why, what, docs, clarify, explain, confused |
| chore | ci, deps, bump, config, cleanup, housekeeping, lint |

Apply the type label:

```bash
# GitHub -- apply type label
gh issue edit "$NUMBER" --add-label "$TYPE"
```

```bash
# Azure DevOps -- apply tag
az boards work-item update --id "$ID" --fields "System.Tags=$TYPE"
```

### Step 3 -- Assign priority

Score each issue 1-4 using these weighted signals:

| Signal | Weight | Rule |
|--------|--------|------|
| Existing labels | 3 | `p1-critical` or `security` already set: keep, skip scoring |
| Keywords in title/body | 2 | urgent, blocker, production, data loss, security -> p1; regression, broken -> p2 |
| Issue age | 2 | Over `max_age_untriaged_days` (7d): bump +1 priority level |
| Reporter | 1 | Org member or maintainer: bump +1 |

Map final score to label:

| Score | Label |
|-------|-------|
| >= 7 | p1-critical |
| 5-6 | p2-high |
| 3-4 | p3-normal |
| 1-2 | p4-low |

```bash
# GitHub
gh issue edit "$NUMBER" --add-label "$PRIORITY"
```

```bash
# Azure DevOps
az boards work-item update --id "$ID" --fields "Microsoft.VSTS.Common.Priority=$PRIORITY_NUM"
```

### Step 4 -- Detect duplicates

Compare each issue title and body against all other open issues. Use normalized token overlap as the similarity metric. Flag pairs exceeding the `duplicate_similarity` threshold (0.8).

For each duplicate pair, keep the older issue and comment on the newer one:

```bash
# GitHub
gh issue comment "$NEWER_NUMBER" --body "Likely duplicate of #$OLDER_NUMBER (similarity: ${SCORE}). Marking for review.

<!-- triage-runbook:duplicate -->"
gh issue edit "$NEWER_NUMBER" --add-label "duplicate"
```

```bash
# Azure DevOps
az boards work-item update --id "$NEWER_ID" --fields "System.Tags=duplicate" --discussion "Likely duplicate of #$OLDER_ID (similarity: ${SCORE}). Marking for review."
```

### Step 5 -- Identify and discard noise

Match issues against `noise_keywords` (test, wip, scratch, tmp). Also flag issues with empty bodies and no comments after 48 hours.

```bash
# GitHub -- comment rationale then close
gh issue comment "$NUMBER" --body "Closing: this issue matches noise pattern (\`$MATCHED_KEYWORD\`) and appears to be a test or scratch item. Reopen if this was filed intentionally.

<!-- triage-runbook:noise -->"
gh issue close "$NUMBER" --reason "not planned"
```

```bash
# Azure DevOps
az boards work-item update --id "$ID" --fields "System.State=Removed" --discussion "Closing: noise pattern ($MATCHED_KEYWORD). Reopen if intentional."
```

### Step 6 -- Apply triage labels

For every issue that passed steps 2-5 without being closed or flagged as duplicate, apply the `triaged` label and the handoff marker `needs-refinement`:

```bash
# GitHub
gh issue edit "$NUMBER" --add-label "triaged,needs-refinement"
```

```bash
# Azure DevOps
az boards work-item update --id "$ID" --fields "System.Tags=triaged; needs-refinement"
```

### Step 7 -- Comment classification rationale

Leave a structured comment on each triaged issue explaining the classification:

```bash
# GitHub
gh issue comment "$NUMBER" --body "## Triage Summary

- **Type:** $TYPE
- **Priority:** $PRIORITY
- **Duplicate:** $DUPLICATE_STATUS
- **Age:** $AGE_DAYS days
- **Next step:** refinement

<!-- triage-runbook:classified -->"
```

```bash
# Azure DevOps
az boards work-item update --id "$ID" --discussion "## Triage Summary\n\n- **Type:** $TYPE\n- **Priority:** $PRIORITY\n- **Duplicate:** $DUPLICATE_STATUS\n- **Age:** $AGE_DAYS days\n- **Next step:** refinement"
```

### Step 8 -- Done

No report is generated. The mutations applied (labels, comments, closures) are the sole output. Stop after step 7.

## Output

No local files. Mutations (labels, comments, closures) are the sole output.

## Guardrails

- **Never** closes issues labeled `p1-critical`, `pinned`, or `security` -- these are protected labels.
- **Never** modifies issues in `closed` or `resolved` state -- these are protected states.
- **Never** assigns issues to people -- assignment is a refinement concern, not triage.
- **Never** creates pull requests, branches, or code changes -- this is an intake runbook.
- **Never** modifies feature work items or hierarchy items such as epics and features.
- **Never** exceeds 50 mutations per run. Once the cap is reached, it halts execution and reports remaining items.
- **Never** removes existing labels -- it only adds labels. Relabeling is a refinement concern.
- **Mutations enabled by default.** All qualifying labels and comments are applied automatically.
