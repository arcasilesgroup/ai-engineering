---
name: stale-issues
schedule: "0 9 * * *"
environment: worktree
layer: triage
requires: [gh]
---

# Stale Issue Detection

## Prompt

Detect and label stale issues — open issues with no activity for 14+ days.

1. Fetch all open issues: `gh issue list --state open --json number,title,labels,updatedAt --limit 200`.
2. For each issue:
   - Calculate days since last update.
   - If >= 14 days and not labeled `stale`:
     - Add label `stale`.
     - Post comment: "This issue has had no activity for 14+ days. It will be closed in 7 days if no further activity occurs. Remove the `stale` label to keep it open."
   - If >= 21 days and labeled `stale` with no activity since stale comment:
     - Close the issue with comment: "Closing due to inactivity. Reopen if still relevant."
   - If labeled `stale` but has recent activity (< 14 days):
     - Remove `stale` label.
3. Report: count of newly stale, auto-closed, and reactivated.

## Context

- Uses: work-item skill.
- 14-day threshold matches stale detection in triage mode.

## Safety

- Only adds/removes `stale` label and posts comments.
- Auto-close only after 21 days (14 stale + 7 grace period).
- Do NOT close issues labeled `p1-critical` or `pinned`.
- Do NOT close issues with milestone assigned.
- Maximum 30 label changes per run.
