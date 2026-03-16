---
id: "054"
slug: "pipeline-skill-v2"
status: "draft"
created: "2026-03-16"
size: "L"
tags: ["cicd", "pipeline", "github-actions", "azure-pipelines", "dependabot", "skill"]
branch: "spec/054-pipeline-skill-v2"
pipeline: "full"
decisions:
  - id: "DEC-054-01"
    decision: "SHA pinning is the default action version strategy"
    rationale: "Tags are mutable — SHA provides immutable, auditable references. Tag comment preserved for readability."
  - id: "DEC-054-02"
    decision: "Azure Pipelines gets full parity with GitHub Actions in the skill"
    rationale: "User confirmed; enterprise-grade template composition patterns should be codified as first-class guidance."
  - id: "DEC-054-03"
    decision: "Dependabot fixes are Phase 0 prerequisite, not a separate spec"
    rationale: "Operational cleanup is prerequisite to validating the new skill — keeps scope coherent."
  - id: "DEC-054-04"
    decision: "Skill produces a template library (composite actions + reusable workflows) not just a single ci.yml"
    rationale: "Composability enables project-level customization while enforcing framework gates."
  - id: "DEC-054-05"
    decision: "Enterprise CICD patterns adopted as architectural influence"
    rationale: "Industry-standard manager/template composition patterns adopted for Azure Pipelines guidance."
  - id: "DEC-054-06"
    decision: "Single ci-result gate job replaces per-job Branch Protection checks"
    rationale: "Conditional jobs (code-only, PR-only, optional) cause skip/pending states that block merge. A context-aware ci-result job aggregates results and is the only required check in Branch Protection."
---

# Spec 054 — Pipeline Skill v2: Enterprise CI/CD Generation

## Problem

The current `pipeline` skill (v1) is a procedural guide that generates CI/CD workflows but lacks:

1. **Dependabot integration** — No guidance for `dependabot.yml` generation, no auto-lock workflow for `uv.lock` regeneration, no SHA pinning strategy. Current Dependabot PRs fail because of lock desync and duplicated individual PRs superseded by grouping.
2. **Template library** — Generates monolithic workflow files instead of composable building blocks (composite actions, reusable workflows with `workflow_call`).
3. **Action version security** — No SHA pinning guidance. Current workflows use mutable tags (`@v4`, `@v5`) vulnerable to supply-chain attacks.
4. **Azure Pipelines parity** — Mentions Azure Pipelines but has no real guidance for template composition, `@resource` references, variable groups, environment gates, or the manager pattern.
5. **Missing CI patterns** — No concurrency control, no path-based triggering strategy, no timeout enforcement, no artifact retention policy, no cache strategy codification, no merge queue support.
6. **No workflow validation** — `actionlint` is mentioned but not codified as a mandatory generation step.
7. **No environment/deployment gates** — No GitHub Environment protection rules or Azure DevOps approval gates.
8. **No status badge generation** — Workflows don't produce README badges.
9. **No self-hosted runner guidance** — Only GitHub-hosted runners considered.
10. **Branch Protection vs. conditional jobs conflict** — ~20 individual checks in `ci.yml` are required by Branch Protection, but many are conditional (`code == true`, PR-only, token-dependent). Skipped jobs show as "Expected/Pending" and block merge for docs-only PRs, Dependabot PRs, and external contributions.

Additionally, 4 Dependabot PRs are stuck:
- 2 individual pip PRs (`pytest`, `pytest-cov`) are superseded by the grouped PR
- The grouped pip PR needs rebase for the gate trailer exemption
- The GitHub Actions PR bumps to potentially non-existent major versions (`checkout@v6`, `setup-uv@v7`, `upload-artifact@v7`)

## Solution

### Phase 0: Dependabot Triage + CI Result Gate

1. Close superseded individual Dependabot PRs
2. Create `dependabot-auto-lock.yml` workflow for automatic `uv.lock` regeneration
3. Validate and merge/close the GitHub Actions version bump PR
4. Update `dependabot.yml` with version constraints
5. Add context-aware `ci-result` gate job to `ci.yml` — the single required check for Branch Protection
6. Update Branch Protection to require only `CI Result` instead of ~20 individual checks

### Phase 1: Pipeline Skill v2 Rewrite

Rewrite the `pipeline` skill as a comprehensive CI/CD generation guide covering:

**GitHub Actions** (full depth):
- Reusable workflows (`workflow_call`) for test, security, release
- Composite actions for setup, scan, deploy
- SHA pinning with tag comments
- Concurrency groups, path-based triggers, timeouts
- Matrix strategies, caching, artifact management
- Dependabot config generation with auto-lock
- Merge queue support
- Environment protection rules
- Status badge generation

**Azure Pipelines** (full parity):
- Template composition with `@resource` references (external template repos)
- Manager pattern: build-manager, deploy-manager, artifact-manager, security-manager
- Stage/job/step templates for reusability
- Variable groups and KeyVault integration
- Environment approval gates and deployment strategies (rolling, canary, blue-green)
- SonarCloud integration as reusable template
- Branch-conditional deployment (develop → INT, release → ACC, main → PRO)
- Artifact promotion model (build once, deploy many)
- Self-hosted agent pool guidance

**Cross-Platform** (shared):
- Workflow validation (actionlint for GH, schema validation for Azure)
- Security-first defaults (minimal permissions, OIDC, SHA pinning)
- Cache strategy per stack
- Timeout and retry policies
- Artifact retention policies
- Monorepo-aware triggering

### Phase 2: CICD Standards Update

Update `standards/framework/cicd/core.md` with:
- Action version pinning policy
- Dependabot management contract
- Azure Pipelines standards
- Reusable workflow/template library contract
- Environment protection requirements

### Phase 3: Mirror Sync

Propagate the new skill to all IDE mirrors and project templates.

## Scope

### In Scope

- Pipeline skill rewrite (`.agents/skills/pipeline/SKILL.md`)
- All IDE mirrors (`.claude/skills/ai-pipeline/SKILL.md`, `.github/prompts/ai-pipeline.prompt.md`)
- Project template mirrors (`src/ai_engineering/templates/project/...`)
- CICD standards (`standards/framework/cicd/core.md` + template mirror)
- `dependabot.yml` updates
- New `dependabot-auto-lock.yml` workflow
- Dependabot PR triage (close/merge)

### Out of Scope

- Rewriting existing CI workflows (ci.yml, release.yml, etc.) — the skill describes how to generate; existing workflows are updated separately
- Creating actual composite actions or reusable workflows for this repo — the skill describes the pattern
- Azure DevOps pipeline files for this repo (GitHub-only project)
- Deployment platform changes (Railway, Vercel, etc. — covered by existing skill sections)

## Acceptance Criteria

1. Pipeline skill v2 has dedicated sections for GitHub Actions AND Azure Pipelines with equal depth
2. GitHub Actions section covers: reusable workflows, composite actions, SHA pinning, concurrency, path triggers, matrix, caching, environments, badges, merge queue, Dependabot
3. Azure Pipelines section covers: template composition with resources, manager pattern, variable groups, KeyVault, environment gates, deployment strategies, SonarCloud templates, artifact promotion, conditional deployment
4. CICD standards updated with action pinning policy, Dependabot contract, Azure Pipelines standards
5. `dependabot-auto-lock.yml` workflow exists and handles `uv.lock` regeneration
6. `dependabot.yml` has proper version constraints and grouping
7. All IDE mirrors are in sync (agents, claude, github, project templates)
8. `actionlint` passes on all workflow files
9. Mirror sync integrity check passes
10. `ci.yml` has a context-aware `ci-result` gate job that is the sole required Branch Protection check
11. `ci-result` enforces: always-required jobs must pass; code-conditional jobs must pass when `code == true`; PR-only jobs must pass when applicable; optional jobs may skip but not fail
12. Docs-only PRs, Dependabot PRs, and external contributor PRs all pass CI cleanly when their relevant checks succeed

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Skill becomes too large (token budget) | Medium | Split into sub-sections with progressive loading; keep procedure concise, move reference tables to appendix |
| Azure Pipelines guidance becomes stale | Low | Mark as "reference pattern" — the skill generates, projects maintain |
| SHA pinning creates update friction | Low | Dependabot auto-updates SHAs; document the `# vN.M.P` comment convention |
| ci-result hides individual failures | Low | ci-result reports which jobs failed; individual job statuses remain visible in PR checks UI |

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| DEC-054-01 | SHA pinning as default action version strategy | Tags are mutable; SHAs are immutable and auditable |
| DEC-054-02 | Azure Pipelines gets full parity | User confirmed; enterprise adoption requires it |
| DEC-054-03 | Dependabot fixes bundled as Phase 0 | Operational prerequisite for validating the new skill |
| DEC-054-04 | Template library approach (composite + reusable) | Composability > monolithic; enables project customization |
| DEC-054-05 | Enterprise CICD patterns as architectural influence | Industry-standard manager/template composition patterns adopted |
| DEC-054-06 | Single ci-result gate replaces per-job Branch Protection | Conditional jobs cause skip states that block merge; one aggregated check solves this without reducing enforcement |
