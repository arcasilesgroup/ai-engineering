# Runbook: Daily Triage

## Purpose

Automated daily issue hygiene: detect stale issues, validate labels, and surface items needing attention.

## Schedule

Weekdays (9AM UTC) via `ai-eng-daily-triage` agentic workflow.

## Procedure

1. **List open issues**: Fetch all open issues with metadata (title, labels, updated date, assignees).
2. **Detect stale**: Identify issues not updated in >30 days.
3. **Label stale issues**: Apply `stale` label to issues exceeding the threshold.
4. **Surface unlabeled**: Find issues missing priority labels (`priority-high`, `priority-medium`, `priority-low`).
5. **Close abandoned**: Close issues labeled `stale` that have had no activity for >60 days with a comment explaining the closure.
6. **Report**: Summarize findings — stale count, unlabeled count, closed count.

## Triage Criteria

| Condition | Action |
|-----------|--------|
| No update >30 days | Add `stale` label |
| No priority label | Add `needs-triage` label |
| Stale >60 days + no assignee | Close with comment |
| Has `bug` label + no assignee | Flag for attention |

## Output

Console summary with counts. No issue created (this IS the issue management workflow).
