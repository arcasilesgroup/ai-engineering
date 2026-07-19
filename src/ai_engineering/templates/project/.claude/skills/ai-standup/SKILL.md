---
name: ai-standup
description: "Generates standup notes and status updates from actual git commits and PRs — never reconstructed from memory. Trigger for 'write my standup', 'what did I do today', 'what did I ship this week', 'status update', 'handoff notes', 'end of day summary'. Not for pitch or blog content; use /ai-prose instead. Not for sprint retrospectives; use /ai-sprint instead."
effort: cheap
argument-hint: "--days N|--author [name]"
---


# Standup

Generate copy-paste-ready standup notes from actual PR + commit activity grouped by status, emitted as markdown to stdout for Slack/Teams/standup tools with one link per item. For sprint-level summaries use `/ai-sprint retro`; for incident timelines use `/ai-postmortem`.

```
/ai-standup                   # today's standup (1 working day)
/ai-standup --days 3          # last 3 days (covers a long weekend)
/ai-standup --author @alice   # standup for a specific team member
```

## Pre-conditions (MANDATORY)

1. Read `manifest.yml` `work_items` section.
2. Read `.ai-engineering/reference/gather-activity-data.md` for canonical git log, PR query, and work-item commands.
3. Use the active provider to gather work-item data; include status when available.

## Workflow

Principles: §10.4 DRY (single `gather-activity-data.md` source for all activity queries).

1. **Determine lookback** — default 1 working day; override `--days N`; skip weekends unless `--days` covers them.
2. **Collect activity** via `gather-activity-data.md` commands: (a) local commits (git log, author filter); (b) PRs (provider query); (c) active spec tasks from `.ai-engineering/specs/spec.md` + `plan.md`.
3. **Classify** into three groups:

   | Group | Criteria |
   |-------|----------|
   | **Shipped** | Merged PRs, completed spec tasks |
   | **In Progress** | Open PRs, branches with recent commits, active spec tasks |
   | **Blocked** | PRs with review pending 24h+, tasks marked blocked |

4. **Resolve author** — if `--author` absent, detect from `git config user.name` or `gh api user`.
5. **Format** — markdown to stdout, one link per item:

```markdown
## Standup — YYYY-MM-DD

### Shipped
- Merged PR #123: Add secret scanning to commit hook [link]
- spec-054: Task 2.1 -- hook installation complete

### In Progress
- PR #125: Telemetry event schema (awaiting review) [link]

### Blocked
- PR #120: Dependency update blocked on upstream release
```

## Examples

User: "what did I ship this week?"

```
/ai-standup --days 7
```

Scans commits + PRs over a 7-day window, groups into Shipped / In Progress / Blocked, includes links per item, formats for Slack copy-paste.

## Integration

Called by: user directly. Calls: `git log`, `gh pr list`, `az repos pr list`. See also: `/ai-sprint` (full sprint view), `/ai-prose content sprint-review`, `/ai-note`.

$ARGUMENTS
