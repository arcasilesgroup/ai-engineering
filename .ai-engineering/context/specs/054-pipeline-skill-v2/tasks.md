# Tasks — Spec 054: Pipeline Skill v2

## Phase 0: Dependabot Triage + CI Result Gate

- [ ] 0.1 Close superseded individual Dependabot PRs → **MANUAL**: close #143 (pytest) and #145 (pytest-cov) via GitHub UI — superseded by grouped #150
- [ ] 0.2 Validate GitHub Actions version bump PR #151 → **MANUAL**: verify tag existence for checkout@v6, setup-uv@v7, upload-artifact@v7, download-artifact@v8, paths-filter@v4, sonarqube-scan-action@v7; close if phantom
- [x] 0.3 Create `.github/workflows/dependabot-auto-lock.yml` (uv lock regeneration)
- [x] 0.4 Update `.github/dependabot.yml` (commit-message prefix with conventional commits)
- [ ] 0.5 Rebase grouped pip PR #150 onto main → **MANUAL**: rebase via GitHub UI after superseded PRs closed
- [x] 0.6 Add context-aware `ci-result` gate job to `ci.yml` — categories: always-required, code-conditional, PR-only, optional
- [x] 0.7 `build` job retains full dependency chain; `ci-result` is the new aggregator
- [ ] 0.8 Update Branch Protection → **MANUAL**: Settings > Branches > require only `CI Result` + `install-smoke` as status checks

## Phase 1: Pipeline Skill v2 Rewrite

- [ ] 1.1 Write SKILL.md header (frontmatter, metadata, updated token estimate)
- [ ] 1.2 Write Procedure section (platform detect → stack detect → dispatch → validate → report)
- [ ] 1.3 Write GitHub Actions Generation section
  - [ ] 1.3.1 Workflow structure (CI layout, job ordering, dependencies)
  - [ ] 1.3.2 CI Result Gate Job pattern (context-aware aggregation, Branch Protection strategy)
  - [ ] 1.3.3 Reusable workflows (`workflow_call` patterns)
  - [ ] 1.3.4 Composite actions (setup-project, security-scan)
  - [ ] 1.3.5 SHA pinning policy
  - [ ] 1.3.6 Concurrency & path triggers
  - [ ] 1.3.7 Matrix strategies
  - [ ] 1.3.8 Caching strategy (per-stack)
  - [ ] 1.3.9 Environment protection (GitHub Environments)
  - [ ] 1.3.10 Merge queue support
  - [ ] 1.3.11 Status badges
  - [ ] 1.3.12 Dependabot integration (config + auto-lock + grouping)
- [ ] 1.4 Write Azure Pipelines Generation section
  - [ ] 1.4.1 Pipeline structure (stages/jobs/steps)
  - [ ] 1.4.2 Template composition with `@resource` references
  - [ ] 1.4.3 Manager pattern (build/deploy/artifact/security managers)
  - [ ] 1.4.4 Stage/job/step templates
  - [ ] 1.4.5 Variable groups & KeyVault integration
  - [ ] 1.4.6 Environment approval gates
  - [ ] 1.4.7 Deployment strategies (rolling, canary, blue-green)
  - [ ] 1.4.8 SonarCloud integration templates
  - [ ] 1.4.9 Artifact promotion model
  - [ ] 1.4.10 Branch-conditional deployment
  - [ ] 1.4.11 Self-hosted agent guidance
- [ ] 1.5 Write Cross-Platform Standards section
- [ ] 1.6 Write Output Contract, Governance Notes, References

## Phase 2: CICD Standards Update

- [x] 2.1 Add "Action Version Pinning Policy" to `cicd/core.md`
- [x] 2.2 Add "Dependabot Management Contract" to `cicd/core.md`
- [x] 2.3 Add "Azure Pipelines Standards" to `cicd/core.md`
- [x] 2.4 Add "Reusable Components Contract" to `cicd/core.md`
- [x] 2.5 Add "Environment Protection Requirements" to `cicd/core.md`
- [x] 2.6 Add "Concurrency & Performance" to `cicd/core.md`
- [x] 2.7 Add "Required Check Strategy" to `cicd/core.md` (ci-result pattern, Branch Protection)

## Phase 3: Mirror Sync + Validation

- [ ] 3.1 Sync to `.claude/skills/ai-pipeline/SKILL.md`
- [ ] 3.2 Sync to `.github/prompts/ai-pipeline.prompt.md`
- [ ] 3.3 Sync to `src/ai_engineering/templates/project/.agents/skills/pipeline/SKILL.md`
- [ ] 3.4 Sync to `src/ai_engineering/templates/project/.claude/skills/ai-pipeline/SKILL.md`
- [x] 3.5 Sync `cicd/core.md` to `src/ai_engineering/templates/.ai-engineering/standards/framework/cicd/core.md`
- [x] 3.6 Run `sync_command_mirrors.py --check` ✓ PASS (288 files, 0 drift)
- [x] 3.7 Run workflow policy check ✓ PASS (13 workflow files, YAML valid)
- [x] 3.8 Content integrity ✓ PASS (manifest OK, 38 skills valid)
- [ ] 3.9 Run full test suite → **BLOCKED**: PyPI returning 403 (VPN/proxy); `uv sync` cannot resolve deps

## Audit Fixes (added by spec-054 audit)

- [x] A.1 Fix ci-result: add change-scope failure detection
- [x] A.2 Fix ci-result: remove snyk-security from build needs (aligns with DEC-009)
- [x] A.3 Expand paths-filter code scope (add scripts/**, uv.lock)
- [x] A.4 Add timeout-minutes to all jobs across all 13 workflow files
- [x] A.5 Add concurrency group to ci.yml
- [x] A.6 SHA-pin astral-sh/setup-uv@d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86 (v5.4.2), dorny/paths-filter@d1c1ffe (v3.0.3), pypa/gh-action-pypi-publish@76f52bc (v1.12.4)
- [x] A.7 Add timeout-minutes to dependabot-auto-lock.yml, install-smoke.yml, and all ai-eng-* workflows
- [x] A.8 Extend check_workflow_policy.py (timeout, concurrency, SHA pinning checks) — all 13 workflows pass
- [x] A.9 Document install-smoke as second required Branch Protection check in cicd/core.md

## Progress

| Phase | Tasks | Done | Status |
|-------|-------|------|--------|
| 0 | 8 | 4 | in-progress (4 manual) |
| 1 | 29 | 0 | not started (rewrite needed) |
| 2 | 7 | 7 | done |
| 3 | 9 | 4 | in-progress (mirrors need re-sync after rewrite) |
| Audit | 9 | 9 | done |
| **Total** | **62** | **24** | **in-progress** |
