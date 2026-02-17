# Spec 004: Hygiene & Risk Governance — Done

## Completion Date

2026-02-10

## Summary

Delivered two cohesive operational governance pillars: branch hygiene automation (pre-implementation skill + CLI cleanup command + shared git helpers) and risk acceptance lifecycle (schema evolution, 3 lifecycle skills, gate enforcement, pipeline compliance scanning).

## Changes Delivered

- **Branch hygiene**: `maintenance/branch_cleanup.py` with dry-run/apply modes, `skills/workflows/pre-implementation.md` skill, shared `git/operations.py` module (refactored from duplication in workflows.py and gates.py)
- **Risk lifecycle**: `Decision` model evolved to schema 1.1 (backward compatible) with severity, status, renewal tracking; `state/decision_logic.py` with create/list/renew/revoke/remediate functions; severity-based expiry (C=15d, H=30d, M=60d, L=90d); max 2 renewals
- **Gate enforcement**: expiring-risk warning in pre-commit, expired-risk block in pre-push, `ai-eng gate risk-check` CLI command
- **Pipeline compliance**: `pipeline/compliance.py` scanner for GitHub Actions + Azure DevOps, `pipeline/injector.py` for risk gate injection, CI templates in `templates/pipeline/`
- **Skills**: `accept-risk.md`, `resolve-risk.md`, `renew-risk.md` in `govern/` category
- **CLI commands**: `maintenance branch-cleanup`, `maintenance risk-status`, `maintenance pipeline-compliance`
- **Audit events**: all risk lifecycle transitions logged to audit-log.ndjson

## Quality Gate

- 466-line risk lifecycle test suite (`test_risk_lifecycle.py`)
- Branch cleanup unit tests (`test_branch_cleanup.py`)
- Pipeline compliance tests (`test_pipeline_compliance.py`)
- All 18 acceptance criteria verified
- Schema backward compatibility confirmed

## Decision References

- D-001 through D-010 (spec-local decisions)
- S0-006: Risk lifecycle severity-based expiry defaults
- S0-007: Max 2 renewals per risk acceptance
