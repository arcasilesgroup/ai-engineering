---
name: triage
description: "Scan open issues and backlog, classify by type and priority, detect duplicates, discard noise, label triaged items for refinement"
type: intake
cadence: daily
---

# Triage Runbook

## Purpose

Scan all open issues and backlog items across GitHub and Azure DevOps, classify each by type and priority, detect duplicates, discard noise, and label triaged items for refinement. Mutations are applied automatically. It runs daily on any of the four registered hosts.

## Procedure

### Step 1 -- Fetch open issues

**GitHub:**

```bash
gh issue list --state open --limit 500 --json number,title,body,labels,createdAt,author,comments --jq '.[] | select(.labels | map(.name) | any(startswith("triaged"), startswith("priority/")) | not)'
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

Apply the label `type/<classified>`:

```bash
# GitHub -- apply type label
gh issue edit "$NUMBER" --add-label "type/$TYPE"
```

```bash
# Azure DevOps -- apply tag
az boards work-item update --id "$ID" --fields "System.Tags=type/$TYPE"
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
| >= 7 | priority/p1 |
| 5-6 | priority/p2 |
| 3-4 | priority/p3 |
| 1-2 | priority/p4 |

```bash
# GitHub
gh issue edit "$NUMBER" --add-label "priority/$PRIORITY"
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

### Step 8 -- Generate summary report

Produce a summary to stdout (or write to `state/triage-report.json` if persistence is configured):

```bash
echo "=== Triage Report $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "Total scanned:     $TOTAL_SCANNED"
echo "Classified:        $TOTAL_CLASSIFIED"
echo "  bug:             $COUNT_BUG"
echo "  feature:         $COUNT_FEATURE"
echo "  enhancement:     $COUNT_ENHANCEMENT"
echo "  question:        $COUNT_QUESTION"
echo "  chore:           $COUNT_CHORE"
echo "Duplicates found:  $COUNT_DUPLICATES"
echo "Noise discarded:   $COUNT_NOISE"
echo "Triaged (ready):   $COUNT_TRIAGED"
echo "Priority breakdown:"
echo "  p1:              $COUNT_P1"
echo "  p2:              $COUNT_P2"
echo "  p3:              $COUNT_P3"
echo "  p4:              $COUNT_P4"
echo "Mutations applied: $MUTATION_COUNT / 50"
```

## Provider Notes

| Concern | GitHub (`gh`) | Azure DevOps (`az boards`) |
|---------|---------------|---------------------------|
| Fetch issues | `gh issue list --json` with `--jq` filter | `az boards query --wiql` with OData-style WHERE |
| Add label | `gh issue edit --add-label` | `az boards work-item update --fields "System.Tags=..."` |
| Comment | `gh issue comment --body` | `az boards work-item update --discussion` |
| Close | `gh issue close --reason` | Update `System.State` to `Removed` or `Closed` |
| Priority field | Custom label `priority/pN` | Built-in `Microsoft.VSTS.Common.Priority` (1-4) |
| Duplicate | Label `duplicate` + comment | Tag `duplicate` + discussion entry |
| Auth | `GH_TOKEN` env var or `gh auth login` | `az login` or service principal via `AZURE_DEVOPS_EXT_PAT` |
| Pagination | `--limit` flag (max 500 per call, paginate with `--cursor`) | WIQL `TOP` clause or `--top` flag |

## Host Notes

- **codex-app-automation** -- Runs as a Codex background task. Ensure `GH_TOKEN` or Azure PAT is injected via repository secrets. Codex enforces a network sandbox; all API calls must go through `gh` or `az` CLI (no raw HTTP). Timeout budget is 10 minutes.
- **claude-scheduled-tasks** -- Runs via scheduled Claude sessions. The agent must read this runbook from the filesystem at invocation. Output goes to stdout; persist the report to `state/triage-report.json` if write access is available. Respect the `max_mutations` guardrail since session cost is metered.
- **github-agents** -- Runs as a GitHub Actions workflow or GitHub Copilot agent. Authenticate with `${{ secrets.GITHUB_TOKEN }}`. Label creation requires the `issues: write` permission in the workflow YAML. Azure DevOps commands are unavailable in this host.
- **azure-foundry** -- Runs as an Azure AI Foundry agent or Azure Automation runbook. Authenticate via managed identity or service principal. GitHub commands require a PAT stored in Key Vault. Use `az extension add --name azure-devops` if the extension is not pre-installed.

## Safety

This runbook enforces strict guardrails to prevent unintended side effects:

- **Never** closes issues labeled `p1-critical`, `pinned`, or `security` -- these are protected labels.
- **Never** modifies issues in `closed` or `resolved` state -- these are protected states.
- **Never** assigns issues to people -- assignment is a refinement concern, not triage.
- **Never** creates pull requests, branches, or code changes -- this is an intake runbook.
- **Never** modifies feature work items or hierarchy items such as epics and features.
- **Never** exceeds 50 mutations per run. Once the cap is reached, it halts execution and reports remaining items.
- **Never** removes existing labels -- it only adds labels. Relabeling is a refinement concern.
- **Mutations enabled by default.** All qualifying labels and comments are applied automatically.
