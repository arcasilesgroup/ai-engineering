---
name: ai-triage
version: 2.0.0
description: "Work-item management with sync and triage modes. Sync: bidirectional with GitHub Issues/Azure Boards. Triage: auto-prioritize backlog."
argument-hint: "sync|triage"
mode: agent
tags: [work-items, github-issues, azure-boards, sync, triage, prioritization]
---


# Work Item

## Purpose

Work-item management covering bidirectional sync with external trackers and automated backlog triage. Consolidates work-item and triage skills. Modes: sync (create/update/link work items) and triage (auto-prioritize backlog).

## Trigger

- Command: `/ai-triage [sync|triage]`
- Context: work-item creation, sync with external trackers, backlog prioritization.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"triage"}'` at skill start. Fail-open — skip if ai-eng unavailable.

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

1. Read manifest `work_items` for sources and sync settings.
2. Resolve VCS provider via factory.
3. For each spec in `context/specs/` (excluding `_active.md`, `archive/`):
   a. **Find**: query by `spec-NNN` label (GitHub) or tag (Azure DevOps).
   b. **Create** (if not found): title `[spec-NNN] <Title>`, body from Problem section.
   c. **Close** (if `done.md` exists): close linked issue.
4. Report: created / found / closed / errors.

### CLI

- `ai-eng work-item sync` — sync all specs.
- `ai-eng work-item sync --dry-run` — preview only.

### Triage

1. Scan sources: GitHub Issues + Azure Boards (labels: "ready", "needs-triage").
2. Classify using severity hierarchy.
3. Apply RICE scoring for same-tier tie-breaking.
4. Assign p1/p2/p3 labels.
5. Report: prioritized backlog + stale/blocked/duplicate detection.

## Issue Definition Standard

Every issue (bug, feature, task) MUST include:

### Required Fields

| Field               | Description                                                                           |
| ------------------- | ------------------------------------------------------------------------------------- |
| Title               | `[type] Brief summary` — e.g., `[bug] Installer fails on Windows with spaces in path` |
| Description         | Clear problem or task statement                                                       |
| Priority            | One of: `p1-critical`, `p2-high`, `p3-normal`                                         |
| Size                | One of: `XS` (< 30min), `S` (< 1h), `M` (1-4h), `L` (4-8h), `XL` (> 8h)               |
| Acceptance Criteria | Numbered, verifiable conditions for "done"                                            |

### Optional Fields

| Field    | Description                                                |
| -------- | ---------------------------------------------------------- |
| Spec     | Spec identifier (e.g., `036-platform-runbooks`)            |
| Labels   | `agent-ready`, `ready`, `needs-triage`, `stale`, `blocked` |
| Assignee | GitHub username or `agent` for AI-driven tasks             |

### Priority Mapping

| Severity                | Label         | SLA         |
| ----------------------- | ------------- | ----------- |
| P0 — Outage / data loss | `p1-critical` | Same day    |
| P1 — Blocking workflow  | `p2-high`     | 3 days      |
| P2 — Normal enhancement | `p3-normal`   | Next sprint |

### Size Guide

| Size | Effort     | Examples                                     |
| ---- | ---------- | -------------------------------------------- |
| XS   | < 30 min   | Typo fix, config tweak                       |
| S    | < 1 hour   | Config change, single-file update            |
| M    | 1-4 hours  | New skill adaptor, test coverage improvement |
| L    | 4-8 hours  | New skill, installer feature, CI pipeline    |
| XL   | > 8 hours  | Multi-phase spec, architecture change        |

### Project Fields (Source of Truth)

> `source_of_truth: project_fields` — Project fields are authoritative. Labels exist for compatibility and search only.

| Field       | Type          | Description                                           |
| ----------- | ------------- | ----------------------------------------------------- |
| Status      | Single select | Board column: Backlog, Ready, In progress, In review, Done |
| Priority    | Single select | P0, P1, P2 (maps to labels via `priority_mapping`)    |
| Size        | Single select | XS, S, M, L, XL                                       |
| Estimate    | Number        | Fibonacci: 1, 2, 3, 5, 8, 13, 21                      |
| Start date  | Date          | Required when moving to In progress                    |
| Target date | Date          | Required on issue creation                             |

### Board Transitions

| From        | To          | Trigger                                |
| ----------- | ----------- | -------------------------------------- |
| Backlog     | Ready       | Triage assigns priority + size         |
| Ready       | In progress | Work begins; `start_date` set          |
| In progress | In review   | PR opened                              |
| In review   | Done        | PR merged + acceptance criteria met    |
| Any         | Backlog     | Blocked or deprioritized               |

### Milestone Mapping

- Active spec: milestone = `Spec NNN` (e.g., `Spec 036`)
- Release: milestone = `vX.Y.Z`
- Unplanned: no milestone

### Relationships

- **Parent/child**: Spec issue → sub-task issues (via task list or sub-issues)
- **Blocks/blocked by**: Explicit dependency tracking via issue references
- **Closes**: PR → issue link via `Closes #N` in PR description

### Spec URL Format

When an issue references a spec, use a clickeable URL:

- GitHub: `https://github.com/<owner>/<repo>/blob/main/.ai-engineering/context/specs/<spec>/spec.md`
- Azure DevOps: `https://dev.azure.com/<org>/<project>/_git/<repo>?path=/.ai-engineering/context/specs/<spec>/spec.md&version=GBmain`
