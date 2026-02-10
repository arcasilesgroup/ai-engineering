---
spec: "004"
total: 30
completed: 30
last_session: "2026-02-11"
next_session: "Done — pending pytest run when PyPI unblocked"
---

# Tasks — Hygiene & Risk Governance

## Phase 0: Scaffold [S]

- [x] 0.1 Create spec branch `feat/004-hygiene-risk-governance`
- [x] 0.2 Create spec.md, plan.md, tasks.md
- [x] 0.3 Update `_active.md` to point to 004

## Phase 1: Git Helpers Refactor + Schema Evolution [M]

- [x] 1.1 Create `src/ai_engineering/git/__init__.py`
- [x] 1.2 Create `src/ai_engineering/git/operations.py` with shared helpers
- [x] 1.3 Refactor `workflows.py` to import from `git.operations`
- [x] 1.4 Refactor `gates.py` to import from `git.operations`
- [x] 1.5 Add risk enums and fields to `Decision` model in `models.py`
- [x] 1.6 Add `DecisionStore.risk_decisions()` helper method
- [x] 1.7 Extend `manifest.yml` risk_acceptance config

## Phase 2: Decision Logic Enhancement [M]

- [x] 2.1 Add `default_expiry_for_severity()` function
- [x] 2.2 Add `list_expired_decisions()` function
- [x] 2.3 Add `list_expiring_soon()` function
- [x] 2.4 Add `create_risk_acceptance()` function
- [x] 2.5 Add `renew_decision()` function
- [x] 2.6 Add `revoke_decision()` and `mark_remediated()` functions

## Phase 3: Risk Lifecycle Skills [M]

- [x] 3.1 Create `accept-risk.md` skill
- [x] 3.2 Create `resolve-risk.md` skill
- [x] 3.3 Create `renew-risk.md` skill
- [x] 3.4 Create mirrors in templates directory
- [x] 3.5 Register skills in all 6 instruction files

## Phase 4: Branch Cleanup Module [M]

- [x] 4.1 Create `src/ai_engineering/maintenance/branch_cleanup.py`
- [x] 4.2 Create `pre-implementation.md` workflow skill
- [x] 4.3 Create mirror and register pre-implementation skill

## Phase 5: Gate Enforcement [M]

- [x] 5.1 Add `_check_expiring_risk_acceptances()` to gates.py (pre-commit warn)
- [x] 5.2 Add `_check_expired_risk_acceptances()` to gates.py (pre-push block)
- [x] 5.3 Add `ai-eng gate risk-check` CLI command

## Phase 6: Pipeline Compliance [L]

- [x] 6.1 Create `src/ai_engineering/pipeline/compliance.py`
- [x] 6.2 Create `src/ai_engineering/pipeline/injector.py`
- [x] 6.3 Create pipeline templates (GitHub + Azure DevOps)
- [x] 6.4 Add `ai-eng maintenance pipeline-compliance` CLI command

## Phase 7: CLI & Reporting [M]

- [x] 7.1 Add `ai-eng maintenance branch-cleanup` command
- [x] 7.2 Add `ai-eng maintenance risk-status` command
- [x] 7.3 Extend `MaintenanceReport` with risk and branch data
- [x] 7.4 Register all new commands in `cli_factory.py`

## Phase 8: Audit & Governance Docs [S]

- [x] 8.1 Update AGENTS.md, copilot-instructions.md, CLAUDE.md
- [x] 8.2 Update CHANGELOG.md
- [x] 8.3 Update product-contract.md skill count

## Phase 9: Testing [L]

- [x] 9.1 Create `tests/unit/test_git_operations.py`
- [x] 9.2 Create `tests/unit/test_branch_cleanup.py`
- [x] 9.3 Create `tests/unit/test_risk_lifecycle.py`
- [x] 9.4 Create `tests/unit/test_pipeline_compliance.py`
- [x] 9.5 Extend `test_gates.py` with risk gate tests
- [x] 9.6 Extend `test_state.py` with backward compat tests
