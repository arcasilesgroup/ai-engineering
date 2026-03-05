---
name: weekly-report
schedule: "0 9 * * 1"
environment: worktree
layer: reporting
requires: [gh, uv]
---

# Weekly Report

## Prompt

Generate a weekly health and velocity report. Create a GitHub Issue with the report.

1. **DORA Metrics** (last 7 days):
   - Deployment frequency: count of merged PRs.
   - Lead time: average time from first commit to PR merge.
   - Change failure rate: merged PRs that required follow-up fixes / total merged.
   - Mean time to restore: average time to close `p1-critical` issues.

2. **Issue Velocity**:
   - Opened this week vs closed this week.
   - Current open count by priority.
   - Backlog trend: growing, stable, or shrinking.

3. **Quality Metrics**:
   - Run `ai-eng observe health` and capture results.
   - Test coverage % (from last CI run).
   - Open scan findings count by severity.

4. **AI Agent Metrics**:
   - PRs created by agents this week.
   - Issues resolved by agents.
   - CI fix success rate.

5. Create a GitHub Issue:
   - Title: `[report] Weekly Health — YYYY-MM-DD`
   - Labels: `report`, `weekly`
   - Body: formatted Markdown with all sections above.
   - Close previous week's report issue.

## Context

- Uses: observe skill (health, dora, team modes).
- Reads: GitHub API for PR/issue data.
- Reads: `state/audit-log.ndjson` for event history.

## Safety

- Read-only data collection + single issue creation.
- Do NOT modify code or configuration.
- Close only previous `[report] Weekly Health` issues, nothing else.
