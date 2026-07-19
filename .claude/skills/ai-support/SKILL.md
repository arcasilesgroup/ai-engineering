---
name: ai-support
description: "Investigates customer-reported issues with structure: reproduces, traces to code, documents resolution, builds a searchable knowledge base organized by ticket ID. Trigger for 'a user is reporting that', 'customer complaint', 'support ticket', 'investigate this bug report', 'search past support cases'. Not for production incidents; use /ai-postmortem instead. Not for internal dev bugs; use /ai-debug instead. Not for feature requests; open a GitHub Issue with the enhancement label."
effort: mid
argument-hint: "start [ticket-id]|find [query]"
---


# Support

Structured customer-support investigation: organize findings by ticket, link to code + PRs, build a searchable knowledge base of resolved issues. Storage: `.ai-engineering/support/{YYYY-MM-DD}/{ticket-id}/investigation.md` (date-organized for chronological browsing).

```
/ai-support start TICKET-4521    # start investigation (any ID format)
/ai-support find timeout         # search past investigations
/ai-support find                 # list all investigations
```

## Modes

### start <ticket-id> — new investigation

1. **Check existing** — if a `{ticket-id}` directory exists under `.ai-engineering/support/`, resume it instead of duplicating.
2. **Create** — `.ai-engineering/support/{date}/{ticket-id}/`.
3. **Scaffold** `investigation.md` from template:

```markdown
# {ticket-id}: {title}

**Date**: YYYY-MM-DD
**Customer**: {name/org if known}
**Status**: investigating | resolved | escalated
**Priority**: p1 | p2 | p3

## Issue
{Customer's description -- verbatim or summarized}

## Environment
- Product version:
- OS/Platform:
- Configuration:

## Steps to Reproduce
1. {Step}
2. {Expected vs actual behavior}

## Findings
{Root cause analysis}

## Resolution
{Fix applied, workaround, or escalation path}

## Related
- Code: {file paths}
- PR: {links}
- Notes: {links to /ai-note entries}
```

4. **Investigate + update** — explore relevant code paths, check recent changes and error patterns; keep `investigation.md` current as findings emerge.

### find [query] — search investigations

1. **Search** — scan `.ai-engineering/support/` for matching content.
2. **Rank** — recency, then relevance.
3. **Present** — ticket-id, date, title, status, resolution summary.

## Workflow

Principles: §10.4 DRY (one investigation template + knowledge base, no per-ticket ad-hoc format).

1. **Reproduce** — attempt to reproduce locally using the reported steps.
2. **Isolate** — narrow to the specific code path, configuration, or data condition.
3. **Root cause** — identify why (bug, misconfiguration, edge case, expected behavior).
4. **Resolve** — one of: **Fix** (open a PR via `/ai-pr`, link it), **Workaround** (document steps), **Escalate** (mark `escalated` + reason + target team), **Won't fix** (document rationale).

## Examples

User: "a user is reporting timeouts on TICKET-4521, investigate"

```
/ai-support start TICKET-4521
```

Scaffolds `.ai-engineering/support/2026-05-08/TICKET-4521/investigation.md`, attempts to reproduce, traces affected code paths, documents findings.

## Integration

Called by: user directly when triaging a customer report. Calls: `/ai-pr` (when fixing requires a code change). See also: `/ai-postmortem` (production incidents), `/ai-debug` (internal-only bugs), `/ai-note` (cross-link findings).

$ARGUMENTS
