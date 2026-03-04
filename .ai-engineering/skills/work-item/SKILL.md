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
