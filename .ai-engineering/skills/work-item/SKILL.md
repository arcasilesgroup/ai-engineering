---
name: work-item
description: "Work-item management with sync and triage modes. Sync: bidirectional with GitHub Issues/Azure Boards. Triage: auto-prioritize backlog."
metadata:
  version: 2.0.0
  tags: [work-items, github-issues, azure-boards, sync, triage, prioritization]
  ai-engineering:
    scope: read-write
    token_estimate: 1200
    gating:
      anyBins: [gh, az]
---

# Work Item

## Purpose

Work-item management covering bidirectional sync with external trackers and automated backlog triage. Consolidates work-item and triage skills. Modes: sync (create/update/link work items) and triage (auto-prioritize backlog).

## Trigger

- Command: `/ai:work-item [sync|triage]`
- Context: work-item creation, sync with external trackers, backlog prioritization.

## Modes

### sync — Bidirectional work-item sync
Create, update, link work items between local specs and GitHub Issues / Azure Boards.
- Spec created -> auto-create linked issue
- Issue labeled "ready" -> surface for plan agent
- Spec closed -> auto-close linked issue

### triage — Auto-prioritize backlog
Scan pending work items, classify priority, and manage backlog flow.
- Priority: p1 (critical) > p2 (high) > p3 (normal)
- Hierarchy: security > bugs > features > performance > tests > architecture > DX
- Tie-breaking: RICE scoring (Reach x Impact x Confidence / Effort)
- Throttle: warn at 10+ open, halt non-p1 at 20+
- Detect: stale (14+ days), blocked, duplicates

## Procedure

### Sync
1. Read manifest for configured sources and sync settings.
2. Scan local specs and remote work items.
3. Create/update/link as needed per sync rules.
4. Report sync status with created/updated/linked counts.

### Triage
1. Scan sources: GitHub Issues + Azure Boards (labels: "ready", "needs-triage").
2. Classify using severity hierarchy.
3. Apply RICE scoring for same-tier tie-breaking.
4. Assign p1/p2/p3 labels.
5. Report: prioritized backlog + stale/blocked/duplicate detection.

## Issue Definition Standard

Every issue (bug, feature, task) MUST include:

### Required Fields

| Field | Description |
|-------|-------------|
| Title | `[type] Brief summary` — e.g., `[bug] Installer fails on Windows with spaces in path` |
| Description | Clear problem or task statement |
| Priority | One of: `p1-critical`, `p2-high`, `p3-normal` |
| Size | One of: `S` (< 1h), `M` (1-4h), `L` (4-8h), `XL` (> 8h) |
| Acceptance Criteria | Numbered, verifiable conditions for "done" |

### Optional Fields

| Field | Description |
|-------|-------------|
| Spec | Spec identifier (e.g., `036-platform-runbooks`) |
| Labels | `agent-ready`, `ready`, `needs-triage`, `stale`, `blocked` |
| Assignee | GitHub username or `agent` for AI-driven tasks |

### Priority Mapping

| Severity | Label | SLA |
|----------|-------|-----|
| P0 — Outage / data loss | `p1-critical` | Same day |
| P1 — Blocking workflow | `p2-high` | 3 days |
| P2 — Normal enhancement | `p3-normal` | Next sprint |

### Size Guide

| Size | Effort | Examples |
|------|--------|----------|
| S | < 1 hour | Typo fix, config change, single-file update |
| M | 1-4 hours | New skill adaptor, test coverage improvement |
| L | 4-8 hours | New skill, installer feature, CI pipeline |
| XL | > 8 hours | Multi-phase spec, architecture change |

### Spec URL Format

When an issue references a spec, use a clickeable URL:
- GitHub: `https://github.com/<owner>/<repo>/blob/main/.ai-engineering/context/specs/<spec>/spec.md`
- Azure DevOps: `https://dev.azure.com/<org>/<project>/_git/<repo>?path=/.ai-engineering/context/specs/<spec>/spec.md&version=GBmain`

