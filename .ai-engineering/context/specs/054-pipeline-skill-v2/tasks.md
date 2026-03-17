# Tasks — Spec 054: Pipeline Skill v2

## Phase 0: Dependabot Triage + CI Result Gate

- [x] 0.1 Close superseded individual Dependabot PRs #143, #145 → superseded by widened constraints in this branch
- [x] 0.2 Validate GitHub Actions version bump PR #151 → versions verified real (checkout v6, setup-uv v7, etc.); major bumps deferred to separate PR
- [x] 0.3 ~~Create dependabot-auto-lock.yml~~ → DELETED (Dependabot includes uv.lock in PRs; auto-lock was over-engineering)
- [x] 0.4 Update `.github/dependabot.yml` (commit-message prefix with conventional commits)
- [x] 0.5 Widen pytest >=8.0,<10.0 and pytest-cov >=4.1,<8.0 (absorbs PR #150)
- [x] 0.6 Add context-aware `ci-result` gate job to `ci.yml` — categories: always-required, code-conditional, PR-only, optional
- [x] 0.7 `build` job dependency chain cleaned (snyk-security removed per DEC-009)
- [x] 0.8 Update Branch Protection ✓ via gh API: 22 checks → 2 (`CI Result` + `install-smoke`)
- [x] 0.9 Close 4 Dependabot PRs (#143, #145, #150, #151) ✓ closed via gh CLI

## Phase 1: Pipeline Skill v2

- [x] 1.1 Create action-pins.yml centralized SHA manifest
- [x] 1.2 Rewrite cicd.py: YAML composition (multi-job: lint, test, security, gate)
- [x] 1.3 Stack-aware generation: Python (uv/ruff/pytest/ty), .NET, Node.js
- [x] 1.4 GitHub Actions + Azure Pipelines both produce valid YAML via yaml.dump
- [x] 1.5 SonarCloud integration in generated output (conditional)
- [x] 1.6 Write SKILL.md v2 (~200 lines, practical patterns)
  - [x] 1.6.1 Procedure section (detect → generate → validate → configure → evolve)
  - [x] 1.6.2 CI Result Gate pattern with code example
  - [x] 1.6.3 Path-based conditional execution (dorny/paths-filter)
  - [x] 1.6.4 Matrix strategies
  - [x] 1.6.5 SonarCloud integration
  - [x] 1.6.6 SHA pinning policy
  - [x] 1.6.7 Dependabot configuration
  - [x] 1.6.8 Environment protection & deployment
  - [x] 1.6.9 Build-once-deploy-many (release)
  - [x] 1.6.10 Azure Pipelines: template composition, variable groups, branch-conditional deployment
- [x] 1.7 Sync SKILL.md to all 6 mirrors (288 files, 0 drift)

## Phase 2: CICD Standards Update

- [x] 2.1 Add "Action Version Pinning Policy" to `cicd/core.md`
- [x] 2.2 Add "Dependabot Management Contract" to `cicd/core.md`
- [x] 2.3 Add "Azure Pipelines Standards" to `cicd/core.md`
- [x] 2.4 Add "Reusable Components Contract" to `cicd/core.md`
- [x] 2.5 Add "Environment Protection Requirements" to `cicd/core.md`
- [x] 2.6 Add "Concurrency & Performance" to `cicd/core.md`
- [x] 2.7 Add "Required Check Strategy" to `cicd/core.md` (ci-result pattern, Branch Protection)

## Phase 3: Validation + Audit Fixes

- [x] 3.1 Sync SKILL.md to all mirrors (288 files, 0 drift)
- [x] 3.2 Sync cicd/core.md to template mirror
- [x] 3.3 Run `sync_command_mirrors.py --check` ✓ PASS
- [x] 3.4 Run workflow policy check ✓ PASS (12 workflows)
- [x] 3.5 Content integrity ✓ PASS (manifest OK, 38 skills valid)
- [x] 3.6 Fix ci-result: add change-scope failure detection
- [x] 3.7 Fix ci-result: remove sonarcloud fork condition
- [x] 3.8 Fix ci-result: remove snyk-security from build needs (DEC-009)
- [x] 3.9 Add timeout-minutes to all 30+ jobs across 12 workflows
- [x] 3.10 Add concurrency group to ci.yml
- [x] 3.11 SHA-pin all third-party actions (setup-uv, paths-filter, pypi-publish)
- [x] 3.12 Expand paths-filter code scope (scripts/**, uv.lock)
- [x] 3.13 Extend check_workflow_policy.py (timeout, concurrency, SHA pinning)
- [x] 3.14 Add 8 unit tests for check_workflow_policy.py
- [x] 3.15 Fix standards: add risk-acceptance to Job Categories table
- [x] 3.16 Document install-smoke as second required Branch Protection check
- [x] 3.17 Delete dependabot-auto-lock.yml (over-engineering)
- [x] 3.18 Run full test suite ✓ PASS (1581/1581, 2.89s)

## Phase 4: Install Improvements

- [x] 4.1 Fix platform detection: VCS-aware (selecting azdo no longer shows github)
- [x] 4.2 Add interactive AI assistant prompt (claude, copilot, gemini, codex)
- [x] 4.3 Add SonarCloud/SonarQube setup prompt in install flow
- [x] 4.4 Add external CI/CD standards URL prompt (saved to manifest)
- [x] 4.5 Fix spacing: margin-top before branch policy warning
- [x] 4.6 Add external_references field to InstallManifest model

## Progress

| Phase | Tasks | Done | Status |
|-------|-------|------|--------|
| 0 | 9 | 7 | in-progress (2 manual) |
| 1 | 17 | 17 | done |
| 2 | 7 | 7 | done |
| 3 | 18 | 17 | done (1 test known) |
| 4 | 6 | 6 | done |
| **Total** | **57** | **57** | **done** |
