---
id: "039"
slug: "observe-enrichment-phase-1"
status: "in-progress"
created: "2026-03-09"
size: "L"
tags: []
branch: "feat/039-observe-enrichment-phase-1"
pipeline: "full"
decisions: []
---

# Spec 039 — Observe Enrichment Phase 1

## Problem

The observability subsystem implements ~20% of the observe agent spec. Audit events lack VCS context (branch, commit, repo). 4/5 emitters are dead code. `workflows.py` is orphaned (not wired to CLI). Release orchestrator bypasses standard emitters. `audit-log.ndjson` is gitignored, losing data across sessions.

## Solution

Enrich AuditEntry with VCS context, wire orphaned modules, expand 5 dashboards with data computable from existing sources (audit-log, decision-store.json, install-manifest.json, git log, checkpoint files), and track audit-log in git.

## Scope

### In Scope
- VCS context enrichment (repo_context.py, git/context.py)
- AuditEntry extension (7 optional fields)
- Inject context in _emit() + 6 write sites
- Workflow CLI wiring (3 commands)
- Release orchestrator standardization with emit_deploy_event
- 8 new signal aggregators in signals.py
- 5 dashboard expansions in observe.py
- .gitignore simplification + audit-log reset
- 6 new test files

### Out of Scope (deferred to Phase 2+)
- Wire emit_scan_event/emit_build_event/emit_session_event to actual agents
- Skill/agent tracking (needs new event types)
- MTTR (needs issue tracker integration)
- Standards drift, noise ratio, escalation rate
- 4-week trend analysis

## Acceptance Criteria

1. TODO

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| — | — | — |
