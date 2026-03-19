---
id: "004"
slug: "hygiene-risk-governance"
status: "in-progress"
created: "2026-02-10"
---

# Spec 004 — Hygiene & Risk Governance

## Problem

Two operational governance gaps exist:

1. **Branch hygiene**: AI agents and developers accumulate stale local branches, diverge from the remote, and start implementations on outdated code. There is no automated pre-implementation cleanup, no branch status reporting, and `_PROTECTED_BRANCHES` / `_current_branch` are duplicated across `workflows.py` and `gates.py`.

2. **Risk acceptance lifecycle**: The `decision-store.json` supports `expiresAt` but has no enforcement, no severity classification, no follow-up tracking, no renewal limits, and no pipeline compliance. A team can accept a security risk and forget about it indefinitely. There is no gate that blocks when risk acceptances expire, no visibility into open risks, and no mechanism to ensure release pipelines validate risk status.

## Solution

A unified governance enhancement delivering:

### A — Branch Hygiene

- **Pre-implementation skill** (`pre-implementation.md`) — AI directive to fetch, prune, pull, scan, and clean branches before any implementation.
- **CLI command** `ai-eng maintenance branch-cleanup` — programmatic branch cleanup with dry-run/apply modes.
- **Shared git helpers module** — refactored from duplicated code in `workflows.py` and `gates.py`.

### B — Risk Acceptance Lifecycle

- **Schema evolution** — `Decision` model gains `risk_category`, `severity`, `status`, `accepted_by`, `follow_up_action`, `renewed_from`, `renewal_count`. Schema bumped to 1.1 with backward compatibility.
- **Three lifecycle skills** — `accept-risk.md` (register), `resolve-risk.md` (close after fix), `renew-risk.md` (extend with limit).
- **Gate enforcement** — warning in pre-commit for expiring risks, hard block in pre-push for expired risks.
- **CLI command** `ai-eng gate risk-check` — CI-friendly exit code for pipeline integration.
- **Pipeline compliance** — template + scan + inject for GitHub Actions and Azure DevOps release pipelines.
- **Reporting** — `ai-eng maintenance risk-status` command and integration into `MaintenanceReport`.

## Scope

### In Scope

- Git helpers refactor to shared module (`src/ai_engineering/git/`).
- `Decision` model evolution (schema 1.1, backward compatible).
- Decision logic functions: create risk, list expired, list expiring, renew (max 2), revoke, remediate.
- Severity-based expiry defaults: Critical 15d, High 30d, Medium 60d, Low 90d.
- Branch cleanup module with scan, prune, pull, identify, delete, report.
- Pre-implementation workflow skill.
- Three risk lifecycle skills (`accept-risk`, `resolve-risk`, `renew-risk`) in `lifecycle/`.
- Gate checks: `expiring-risk-warn` (pre-commit), `expired-risk-check` (pre-push).
- CLI command `ai-eng gate risk-check` for CI/pipeline use.
- Pipeline compliance module: scan GitHub Actions + Azure DevOps, inject risk gate, generate templates.
- CLI commands: `maintenance branch-cleanup`, `maintenance risk-status`, `maintenance pipeline-compliance`.
- `MaintenanceReport` extension with risk and branch data.
- Audit events for all risk lifecycle transitions.
- Registration in AGENTS.md, copilot-instructions.md, CLAUDE.md.

### Out of Scope

- Remote skill source validation (covered by existing `sources.lock`).
- Automated remediation (only detection and blocking).
- CI/CD pipeline execution (only template generation and compliance scanning).
- Azure DevOps API integration (template-based, not API-driven).

## Acceptance Criteria

1. `Decision` model accepts schema 1.0 data without errors (backward compatible).
2. `Decision` model supports all new fields: `riskCategory`, `severity`, `acceptedBy`, `followUpAction`, `status`, `renewedFrom`, `renewalCount`.
3. `default_expiry_for_severity()` returns correct timedelta per severity level.
4. `list_expired_decisions()` returns only active decisions with past `expiresAt`.
5. `renew_decision()` fails with error when `renewal_count >= 2`.
6. Pre-commit gate warns (passes) when risk acceptance expires within 7 days.
7. Pre-push gate fails when any active risk acceptance is expired.
8. `ai-eng gate risk-check` exits with code 1 on expired risk acceptances.
9. `ai-eng maintenance branch-cleanup --dry-run` reports cleanable branches without deleting.
10. `ai-eng maintenance branch-cleanup --apply` deletes merged non-protected local branches.
11. `ai-eng maintenance risk-status` displays all risk acceptances with severity, status, days remaining.
12. Pipeline compliance scanner detects release pipelines in `.github/workflows/` and `azure-pipelines*.yml`.
13. Pipeline injector adds risk gate step to detected release pipelines.
14. All risk lifecycle transitions log audit events.
15. Unit test coverage ≥ 90% for governance-critical modules.
16. Protected branches (main/master) are never deleted by branch cleanup.
17. Pre-implementation skill is registered in all 6 instruction files.
18. Three risk lifecycle skills are registered in all 6 instruction files.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D-001 | Single spec for both features | Branch hygiene and risk governance are cohesive operational governance pillars |
| D-002 | `accept-risk` / `resolve-risk` / `renew-risk` naming | Follows lifecycle verb-noun pattern; `resolve` implies fix applied, not just deletion |
| D-003 | Skills in `lifecycle/` category | They manage governance content (decision-store), same as create-spec, create-skill |
| D-004 | Severity-based expiry: C=15d, H=30d, M=60d, L=90d | Proportional urgency; configurable in manifest |
| D-005 | Max 2 renewals per risk acceptance | Forces remediation; prevents indefinite deferral |
| D-006 | Warn pre-commit + block pre-push | Gradual escalation; developer sees warning early, blocked before sharing |
| D-007 | GitHub Actions + Azure DevOps from start | Framework targets both platforms per roadmap |
| D-008 | Pipeline template + scan + inject approach | Covers new projects (template), existing projects (scan+inject), compliance verification |
| D-009 | Backward compatible schema 1.1 | All new fields optional with sensible defaults; existing decision-store.json works unchanged |
| D-010 | Git helpers refactored to `src/ai_engineering/git/` | Eliminates duplication between `workflows.py` and `gates.py` |
