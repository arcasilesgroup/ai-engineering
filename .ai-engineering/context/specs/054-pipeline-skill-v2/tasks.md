# Tasks — Spec 054: Pipeline Skill v2

## Phase 0: Dependabot Triage + CI Result Gate

- [ ] 0.1 Close superseded individual Dependabot PRs (pytest #?, pytest-cov #?)
- [ ] 0.2 Validate GitHub Actions version bump PR — check if v6/v7/v8 tags exist; close if phantom
- [ ] 0.3 Create `.github/workflows/dependabot-auto-lock.yml` (uv lock regeneration)
- [ ] 0.4 Update `.github/dependabot.yml` (commit-message prefix, version constraints)
- [ ] 0.5 Rebase grouped pip PR onto main; verify CI passes
- [ ] 0.6 Add context-aware `ci-result` gate job to `ci.yml`
- [ ] 0.7 Update `build` job dependency chain for ci-result compatibility
- [ ] 0.8 Update Branch Protection: require only `CI Result` as sole required check

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

- [ ] 2.1 Add "Action Version Pinning Policy" to `cicd/core.md`
- [ ] 2.2 Add "Dependabot Management Contract" to `cicd/core.md`
- [ ] 2.3 Add "Azure Pipelines Standards" to `cicd/core.md`
- [ ] 2.4 Add "Reusable Components Contract" to `cicd/core.md`
- [ ] 2.5 Add "Environment Protection Requirements" to `cicd/core.md`
- [ ] 2.6 Add "Concurrency & Performance" to `cicd/core.md`
- [ ] 2.7 Add "Required Check Strategy" to `cicd/core.md` (ci-result pattern, Branch Protection)

## Phase 3: Mirror Sync + Validation

- [ ] 3.1 Sync to `.claude/skills/ai-pipeline/SKILL.md`
- [ ] 3.2 Sync to `.github/prompts/ai-pipeline.prompt.md`
- [ ] 3.3 Sync to `src/ai_engineering/templates/project/.agents/skills/pipeline/SKILL.md`
- [ ] 3.4 Sync to `src/ai_engineering/templates/project/.claude/skills/ai-pipeline/SKILL.md`
- [ ] 3.5 Sync `cicd/core.md` to `src/ai_engineering/templates/.ai-engineering/standards/framework/cicd/core.md`
- [ ] 3.6 Run `sync_command_mirrors.py --check`
- [ ] 3.7 Run `actionlint` on all workflows
- [ ] 3.8 Run `ai-eng validate`
- [ ] 3.9 Run full test suite

## Progress

| Phase | Tasks | Done | Status |
|-------|-------|------|--------|
| 0 | 8 | 0 | pending |
| 1 | 19 | 0 | pending |
| 2 | 7 | 0 | pending |
| 3 | 9 | 0 | pending |
| **Total** | **43** | **0** | **draft** |
