---
name: stale-issues
description: "Detect and label stale issues — open issues with no activity for 14+ days — and auto-close after 21 days with grace period"
type: operational
cadence: daily
---

# Stale Issues

## Objetivo

Detect open issues with no activity for 14+ days, label them `stale`, and auto-close after a 7-day grace period (21 days total).
Exempt issues are never touched. Mutations are applied automatically.

## Precondiciones

- Work item provider configured in `manifest.yml` field `work_items.provider` (GitHub or Azure DevOps).
- CLI tools available: `gh` (GitHub) or `az` (Azure DevOps) authenticated for the target repository.
- Labels `stale`, `p1-critical`, `pinned`, and `security` exist in the issue tracker.

## Procedimiento

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


## Exemptions

The following issues are never marked stale and never auto-closed:

| Rule | Condition |
|------|-----------|
| Protected label | Issue carries `p1-critical`, `pinned`, or `security` |
| Milestoned | Issue is assigned to any milestone |
| Protected state | Issue is already `closed` or `resolved` |

Exemption checks run before any label or state mutation. An issue that gains a protected label or milestone while labeled `stale` will be reactivated on the next run.

## Output

No local files. Mutations (stale labels, grace period comments, closures) are the sole output.

## Guardrails

- **Mutation cap**: Maximum 30 label additions, label removals, and issue closures combined per run. If the cap is reached, stop processing.
- **Mutations enabled by default.** All label, comment, and close operations are applied automatically.
- **Protected labels**: Issues carrying `p1-critical`, `pinned`, or `security` are unconditionally skipped. No label is added, no comment is posted, no state is changed.
- **Protected states**: Issues already in `closed` or `resolved` state are never re-processed.
- **Bot-activity filtering**: Only non-bot updates reset the staleness clock. Bot comments (from the stale label automation itself) do not count as activity.
- **Idempotent**: Running the procedure multiple times on the same day produces the same result. Issues already labeled `stale` are not re-labeled or re-commented.
- **Rollback**: To undo a run, filter issues by the `stale` label, remove the label, and delete the bot comment. No state is irrecoverable since closed issues can be reopened.
