# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Contract-compliance skill for clause-by-clause framework contract validation.
- Ownership-audit skill for ownership boundary and updater safety validation.
- Docs-audit skill for documentation and content quality auditing.
- Test-gap-analysis skill for capability-to-test risk mapping.
- Release-gate skill for aggregated release readiness GO/NO-GO verdicts.
- Platform-auditor agent for full-spectrum audit orchestration across all quality dimensions.
- Command contract compliance validation in verify-app agent.
- Feature inventory mode in codebase-mapper agent.
- Architecture drift detection in architect agent.
- Enforcement tamper resistance analysis in security-reviewer agent.
- Module value classification mode in code-simplifier agent.
- Explain skill for Feynman-style code and concept explanations with 3-tier depth.
- Risk acceptance lifecycle: `accept-risk`, `resolve-risk`, `renew-risk` lifecycle skills with severity-based expiry (C=15d/H=30d/M=60d/L=90d) and max 2 renewals.
- Pre-implementation workflow skill for branch hygiene before new implementation work.
- Branch cleanup module (`maintenance/branch_cleanup.py`): fetch, prune, delete merged branches.
- Pipeline compliance module (`pipeline/compliance.py`, `pipeline/injector.py`): scan GitHub Actions and Azure DevOps pipelines for risk governance gates.
- Pipeline risk gate templates for GitHub Actions and Azure DevOps.
- Shared git operations module (`git/operations.py`): `run_git()`, `current_branch()`, `is_branch_pushed()`, `is_on_protected_branch()`.
- Risk governance gate checks: pre-commit warning for expiring acceptances, pre-push blocking for expired acceptances.
- CLI commands: `ai-eng gate risk-check`, `ai-eng maintenance branch-cleanup`, `ai-eng maintenance risk-status`, `ai-eng maintenance pipeline-compliance`.
- Decision model extended with `riskCategory`, `severity`, `acceptedBy`, `followUpAction`, `status`, `renewedFrom`, `renewalCount` fields (all optional, backward compatible).
- `DecisionStore.risk_decisions()` helper method.
- Risk lifecycle functions in `decision_logic.py`: `create_risk_acceptance()`, `renew_decision()`, `revoke_decision()`, `mark_remediated()`, `list_expired_decisions()`, `list_expiring_soon()`.
- `MaintenanceReport` extended with risk acceptance and branch status fields.
- Create-spec skill for spec creation with branch-first workflow.
- Delete-skill skill for safe skill removal with dependency checks.
- Delete-agent skill for safe agent removal with dependency checks.
- Content-integrity skill for governance content validation (6-category check).
- Spec-First Enforcement section in framework core standards.
- Content Integrity Enforcement section in framework core standards.
- Content integrity capability in verify-app agent.
- Create-skill skill for definitive skill authoring and registration procedure.
- Create-agent skill for definitive agent authoring and registration procedure.
- Changelog documentation skill for generating user-friendly changelogs and release notes from git history.
- Doc-writer skill for open-source documentation generation from codebase knowledge.
- Canonical/template mirror contract for `.ai-engineering` governance artifacts.
- Installer coverage for full bundled non-state governance template tree.

### Changed
- Refactored git operations out of `workflows.py` and `gates.py` into shared `git/operations.py`.
- Decision store schema bumped from 1.0 to 1.1 (backward compatible).
- Gate pre-commit now includes risk expiry warnings.
- Gate pre-push now blocks on expired risk acceptances.
- Aligned `.ai-engineering` and `src/ai_engineering/templates/.ai-engineering` non-state content.
- Installer template mapping now discovers bundled governance files dynamically.
- Updated governance metadata versions from `0.1.0-dev` to `0.1.0`.

### Removed
- `poetry.lock` and empty e2e test package placeholder.

## [0.1.0] - TBD

*First MVP release (Phase 1)*
