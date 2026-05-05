---
name: ai-standup
description: "Use when generating standup notes, daily status updates, or recent-activity summaries from actual git commits and PRs. Trigger for 'write my standup', 'what did I do today', 'what did I ship this week', 'status update', 'handoff notes', 'end of day summary'. Reads real commit and PR history — accurate, not reconstructed from memory."
effort: medium
argument-hint: "--days N|--author <name>"
---


# Standup

## Purpose

Generate standup notes from actual PR and commit activity. Produces concise, copy-paste-ready summaries grouped by status. Eliminates manual standup preparation.

## Trigger

- Command: `/ai-standup`
- Context: preparing for daily standup, team sync, or async status update.

## When to Use

- Before daily standup meetings
- Async status updates for Slack/Teams channels
- End-of-day summaries
- Handoff notes between sessions

## When NOT to Use

- **Sprint-level summaries** -- use `/ai-sprint retro`
- **Incident timelines** -- use `/ai-postmortem`

## Pre-conditions (MANDATORY)

1. Read `.ai-engineering/manifest.yml` — `work_items` section.
2. Read `.ai-engineering/contexts/gather-activity-data.md` for the canonical git log, PR query, and work item commands.
3. Use the active provider to gather work item data and include status in standup notes when available.

## Procedure

1. **Determine lookback** -- default: 1 working day. Override with `--days N`. Skip weekends unless `--days` explicitly covers them.

2. **Collect activity** -- use the commands from `.ai-engineering/contexts/gather-activity-data.md` to scan:
   a. Local commits (git log with author filter)
   b. PRs (provider-specific query)
   c. Active spec tasks from `.ai-engineering/specs/spec.md` and `.ai-engineering/specs/plan.md` -- current work

3. **Classify items** into three groups:

   | Group | Criteria |
   |-------|----------|
   | **Shipped** | Merged PRs, completed spec tasks |
   | **In Progress** | Open PRs, branches with recent commits, active spec tasks |
   | **Blocked** | PRs with review requests pending 24h+, tasks marked blocked |

4. **Format output** -- markdown to stdout:

```markdown
## Standup — YYYY-MM-DD

### Shipped
- Merged PR #123: Add secret scanning to commit hook [link]
- spec-054: Task 2.1 -- hook installation complete

### In Progress
- PR #125: Telemetry event schema (awaiting review) [link]
- spec-054: Task 3.2 -- guard event integration

### Blocked
- PR #120: Dependency update blocked on upstream release
```

5. **Author resolution** -- if `--author` not specified, detect from `git config user.name` or `gh api user`.

## Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--days N` | 1 | Lookback period in working days |
| `--author <name>` | current user | Filter by author name or GitHub handle |

## Quick Reference

```
/ai-standup                   # today's standup
/ai-standup --days 3          # last 3 days (covers a long weekend)
/ai-standup --author @alice   # standup for a specific team member
```

## Output

- Markdown to stdout (not saved to file)
- Designed for copy-paste into Slack, Teams, or standup tools
- Each item includes a link when available

## Integration

- **See also**: `/ai-sprint` (full sprint view -- standup covers daily slice)

$ARGUMENTS
