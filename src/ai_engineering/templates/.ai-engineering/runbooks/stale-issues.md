---
name: stale-issues
description: "Detect and label stale issues — open issues with no activity for 14+ days — and auto-close after 21 days with grace period"
type: operational
cadence: daily
---

# Stale Issues

## Purpose

Detect open issues with no activity for 14+ days, label them `stale`, and auto-close after a 7-day grace period (21 days total).
Exempt issues are never touched. Mutations are applied automatically.

## Procedure

### Step 1 -- Fetch all open issues

Retrieve the full set of open issues with the fields needed for staleness calculation.

**GitHub:**

```bash
gh issue list --state open \
  --json number,title,labels,updatedAt,milestone \
  --limit 200
```

**Azure DevOps:**

```bash
az boards work-item query \
  --wiql "SELECT [System.Id],[System.Title],[System.ChangedDate],[System.Tags],[System.IterationPath] FROM WorkItems WHERE [System.State] = 'Active'" \
  --output json
```

### Step 2 -- Calculate staleness

For each issue, compute the number of days since the last update:

```
days_inactive = (current_date - updatedAt).days
```

Skip any issue that matches an exemption rule (see Exemptions below).

### Step 3 -- Label newly stale issues (>= 14 days, no `stale` label)

For each non-exempt issue where `days_inactive >= 14` and the `stale` label is not present:

```bash
gh issue edit <NUMBER> --add-label "stale"

gh issue comment <NUMBER> \
  --body "This issue has had no activity for 14+ days. It will be closed in 7 days if no further activity occurs. Remove the \`stale\` label to keep it open."
```

### Step 4 -- Auto-close stale issues (>= 21 days)

For each issue labeled `stale` where `days_inactive >= 21` and no non-bot activity has occurred since the stale comment:

```bash
gh issue close <NUMBER> \
  --comment "Closing due to inactivity. Reopen if still relevant."
```

### Step 5 -- Reactivate issues with recent activity

For each issue labeled `stale` where a non-bot update occurred within the last 14 days:

```bash
gh issue edit <NUMBER> --remove-label "stale"
```

This covers cases where a human commented or pushed a linked commit after the stale label was applied.

### Step 6 -- Generate summary report

After processing all issues, produce a summary:

```
Stale Issues Run - <DATE>
  Newly stale:   <N>
  Auto-closed:   <N>
  Reactivated:   <N>
  Exempt skipped: <N>
  Total scanned: <N>
```

Emit the summary to stdout. Hosts may route it to a Slack channel, PR comment, or log sink.

## Exemptions

The following issues are never marked stale and never auto-closed:

| Rule | Condition |
|------|-----------|
| Protected label | Issue carries `p1-critical`, `pinned`, or `security` |
| Milestoned | Issue is assigned to any milestone |
| Protected state | Issue is already `closed` or `resolved` |

Exemption checks run before any label or state mutation. An issue that gains a protected label or milestone while labeled `stale` will be reactivated on the next run.

## Provider Notes

| Provider | Tool | Issue fetch | Label mutation | Close mutation |
|----------|------|-------------|----------------|----------------|
| GitHub | `gh` | `gh issue list --json ...` | `gh issue edit --add-label` / `--remove-label` | `gh issue close --comment` |
| Azure DevOps | `az` | `az boards work-item query --wiql ...` | `az boards work-item update --fields System.Tags=...` | `az boards work-item update --fields System.State=Closed` |

Azure DevOps uses tags instead of labels. The `stale` tag is appended to or removed from `System.Tags`. Milestone exemption maps to `System.IterationPath` being non-empty.

## Host Notes

| Host | Considerations |
|------|---------------|
| `codex-app-automation` | Runs as a scheduled Codex task. Authenticate via `GITHUB_TOKEN` environment variable. Output the summary to stdout for capture by the task runner. |
| `claude-scheduled-tasks` | Invoked on a daily cron. The runbook is loaded as context and executed step-by-step. Mutations enabled by default. |
| `github-agents` | Runs inside a GitHub Actions workflow. Use `${{ secrets.GITHUB_TOKEN }}` for authentication. Emit the summary as a step output for downstream jobs. |
| `azure-foundry` | Authenticate with `az login --identity` for managed identity. Use `az` CLI for all mutations. Map label operations to tag field updates. |

All hosts must enforce the `max_mutations` guardrail and never exceed 30 label or state changes per run regardless of the number of stale issues found.

## Safety

- **Mutation cap**: Maximum 30 label additions, label removals, and issue closures combined per run. If the cap is reached, stop processing and report the remaining unprocessed issues.
- **Mutations enabled by default.** All label, comment, and close operations are applied automatically.
- **Protected labels**: Issues carrying `p1-critical`, `pinned`, or `security` are unconditionally skipped. No label is added, no comment is posted, no state is changed.
- **Protected states**: Issues already in `closed` or `resolved` state are never re-processed.
- **Bot-activity filtering**: Only non-bot updates reset the staleness clock. Bot comments (from the stale label automation itself) do not count as activity.
- **Idempotent**: Running the procedure multiple times on the same day produces the same result. Issues already labeled `stale` are not re-labeled or re-commented.
- **Rollback**: To undo a run, filter issues by the `stale` label, remove the label, and delete the bot comment. No state is irrecoverable since closed issues can be reopened.
