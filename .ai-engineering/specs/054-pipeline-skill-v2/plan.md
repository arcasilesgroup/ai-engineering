# Plan — Spec 054: Pipeline Skill v2

## Session Map

```
Phase 0 (Dependabot Triage)          → build agent
Phase 1 (Skill Rewrite)              → build agent
Phase 2 (CICD Standards Update)      → build agent
Phase 3 (Mirror Sync + Validation)   → build agent + verify agent
```

## Phase 0: Dependabot Triage + CI Result Gate

**Agent**: build
**Scope**: `.github/dependabot.yml`, `.github/workflows/dependabot-auto-lock.yml`, `.github/workflows/ci.yml`, PR management
**Duration**: Small (operational cleanup)

### Tasks

0.1. Close superseded individual Dependabot PRs (pytest, pytest-cov) — they are covered by the grouped PR
0.2. Validate GitHub Actions version bump PR — verify `actions/checkout@v6`, `astral-sh/setup-uv@v7`, `actions/upload-artifact@v7`, `actions/download-artifact@v8`, `dorny/paths-filter@v4`, `SonarSource/sonarqube-scan-action@v7` are real, stable releases. Close if phantom versions.
0.3. Create `dependabot-auto-lock.yml` workflow:
  - Trigger: `pull_request` from `dependabot[bot]` targeting `pyproject.toml`
  - Steps: checkout → setup-uv → `uv lock` → commit & push if changed
  - Permissions: `contents: write`
0.4. Update `dependabot.yml`:
  - Add `commit-message.prefix` for conventional commits
  - Add version constraint comments
  - Verify grouping config is optimal
0.5. Rebase grouped pip PR onto main and verify CI passes
0.6. Add context-aware `ci-result` gate job to `ci.yml`:
  - `if: always()` + `needs: [all jobs]`
  - Logic: always-required jobs (security, content-integrity, workflow-sanity) MUST be success
  - Code-conditional jobs MUST be success when `change-scope.outputs.code == 'true'`, skip accepted otherwise
  - PR-only jobs (verify-gate-trailers) MUST be success when applicable, skip accepted otherwise
  - Optional jobs (snyk-security) may skip but MUST NOT fail
  - Any `failure` result anywhere → `ci-result` fails
0.7. Remove `build` job's dependency on all upstream jobs — `build` should depend on `ci-result` or run independently
0.8. Update Branch Protection rules: require only `CI Result` as the sole required status check

### Gate

- `dependabot-auto-lock.yml` passes `actionlint`
- `ci-result` job correctly evaluates all scenarios (code PR, docs PR, Dependabot PR)
- Superseded PRs closed
- Grouped pip PR CI green

## Phase 1: Pipeline Skill v2 Rewrite

**Agent**: build
**Scope**: `.agents/skills/pipeline/SKILL.md` (canonical source)
**Duration**: Large (comprehensive rewrite)

### Architecture

The skill is restructured into clear sections:

```
SKILL.md
├── Purpose
├── Trigger
├── When NOT to Use
├── Procedure (shared entry point)
│   ├── 1. Platform Detection
│   ├── 2. Stack Detection + Manifest Read
│   ├── 3. Generate → dispatch to platform section
│   ├── 4. Generate Dependabot Config
│   ├── 5. Validate Generated Files
│   └── 6. Report
├── GitHub Actions Generation
│   ├── Workflow Structure
│   ├── CI Result Gate Job Pattern
│   ├── Reusable Workflows (workflow_call)
│   ├── Composite Actions
│   ├── SHA Pinning Policy
│   ├── Concurrency & Path Triggers
│   ├── Matrix Strategies
│   ├── Caching Strategy
│   ├── Environment Protection
│   ├── Merge Queue
│   ├── Status Badges
│   └── Dependabot Integration
├── Azure Pipelines Generation
│   ├── Pipeline Structure
│   ├── Template Composition (@resource)
│   ├── Manager Pattern (build/deploy/artifact/security)
│   ├── Stage/Job/Step Templates
│   ├── Variable Groups & KeyVault
│   ├── Environment Approval Gates
│   ├── Deployment Strategies
│   ├── SonarCloud Templates
│   ├── Artifact Promotion Model
│   ├── Branch-Conditional Deployment
│   └── Self-Hosted Agent Guidance
├── Cross-Platform Standards
│   ├── Security Defaults
│   ├── Timeout & Retry Policy
│   ├── Artifact Retention
│   └── Monorepo-Aware Triggering
├── Output Contract
├── Governance Notes
└── References
```

### Tasks

1.1. Write new SKILL.md header (name, description, metadata, tags, token estimate)
1.2. Write Procedure section (platform detection → stack detection → dispatch → validate → report)
1.3. Write GitHub Actions Generation section:
  - 1.3.1. Workflow structure (CI layout, job ordering, dependencies)
  - 1.3.2. CI Result Gate Job pattern (context-aware aggregation, Branch Protection strategy)
  - 1.3.3. Reusable workflows (`workflow_call` patterns, input/output contracts)
  - 1.3.4. Composite actions (setup-project, security-scan patterns)
  - 1.3.5. SHA pinning policy (format: `uses: owner/action@SHA # vN.M.P`)
  - 1.3.6. Concurrency & path triggers (`concurrency` groups, `paths-filter`)
  - 1.3.7. Matrix strategies (OS × version, fail-fast policy)
  - 1.3.8. Caching strategy (per-stack cache keys, hash-based invalidation)
  - 1.3.9. Environment protection (GitHub Environments, required reviewers, wait timer)
  - 1.3.10. Merge queue support (`merge_group` trigger)
  - 1.3.11. Status badges (format, placement)
  - 1.3.12. Dependabot integration (config generation, auto-lock workflow, grouping)
1.4. Write Azure Pipelines Generation section:
  - 1.4.1. Pipeline structure (stages, jobs, steps hierarchy)
  - 1.4.2. Template composition with `@resource` references (external template repos)
  - 1.4.3. Manager pattern (build-manager, deploy-manager, artifact-manager)
  - 1.4.4. Stage/job/step templates (reusability patterns)
  - 1.4.5. Variable groups & KeyVault integration (secret management)
  - 1.4.6. Environment approval gates (pre-deployment, exclusion locks)
  - 1.4.7. Deployment strategies (rolling, canary, blue-green patterns)
  - 1.4.8. SonarCloud integration templates (prepare/analyze/publish)
  - 1.4.9. Artifact promotion model (build once, promote through environments)
  - 1.4.10. Branch-conditional deployment (develop→INT, release→ACC, main→PRO)
  - 1.4.11. Self-hosted agent guidance (pool selection, capability demands)
1.5. Write Cross-Platform Standards section (security defaults, timeouts, retention, monorepo)
1.6. Write Output Contract, Governance Notes, References

### Gate

- Skill file is valid markdown with correct YAML frontmatter
- Token estimate is updated (expect ~2500-3000 tokens)
- No references to external proprietary implementation details

## Phase 2: CICD Standards Update

**Agent**: build
**Scope**: `.ai-engineering/standards/framework/cicd/core.md`
**Duration**: Medium

### Tasks

2.1. Add "Action Version Pinning Policy" section:
  - SHA pinning required for third-party actions
  - Tag comment format: `# vN.M.P`
  - First-party GitHub actions (actions/*) may use major version tags
  - Dependabot auto-updates SHAs
2.2. Add "Dependabot Management Contract" section:
  - Ecosystem grouping required (pip, github-actions)
  - Auto-lock workflow required for Python projects using `uv`
  - PR grouping to minimize review overhead
  - Version constraints for major bumps
2.3. Add "Azure Pipelines Standards" section:
  - Template composition with central template repo
  - Manager pattern for stage orchestration
  - Variable groups for environment separation
  - KeyVault for secret management (never inline)
  - Environment approval gates for production
  - Artifact promotion (build once, deploy many)
2.4. Add "Reusable Components Contract" section:
  - Composite actions for repeated step sequences
  - Reusable workflows for cross-repo CI patterns
  - Input/output contracts for reusable workflows
  - Versioning strategy for template repos
2.5. Add "Environment Protection Requirements" section:
  - Production environments require approval gate
  - Staging environments require passing CI
  - OIDC preferred over long-lived tokens
2.6. Add "Concurrency & Performance" section:
  - Concurrency groups mandatory for PR workflows
  - Per-job timeout required (no unlimited jobs)
  - Artifact retention policy (30 days default, 90 for releases)
  - Cache strategy per stack
2.7. Add "Required Check Strategy" section:
  - Single `ci-result` gate job as sole required Branch Protection check
  - Context-aware aggregation pattern (always-required, code-conditional, PR-only, optional)
  - Anti-bypass: `paths-filter` patterns must cover all source file extensions
  - Individual jobs remain visible but not required in Branch Protection

### Gate

- Standards file validates (no broken references)
- Template mirror synced
- Content integrity passes

## Phase 3: Mirror Sync + Validation

**Agent**: build + verify
**Scope**: All mirror locations
**Duration**: Small (mechanical)

### Tasks

3.1. Sync canonical skill to Claude mirror (`.claude/skills/ai-pipeline/SKILL.md`)
3.2. Sync canonical skill to Copilot mirror (`.github/prompts/ai-pipeline.prompt.md`)
3.3. Sync canonical skill to project template agents mirror (`src/ai_engineering/templates/project/.agents/skills/pipeline/SKILL.md`)
3.4. Sync canonical skill to project template Claude mirror (`src/ai_engineering/templates/project/.claude/skills/ai-pipeline/SKILL.md`)
3.5. Sync CICD standards to template mirror (`src/ai_engineering/templates/.ai-engineering/standards/framework/cicd/core.md`)
3.6. Run `scripts/sync_command_mirrors.py --check` to verify sync
3.7. Run `actionlint` on all workflow files
3.8. Run `ai-eng validate` for content integrity
3.9. Run full test suite to verify no regressions

### Gate

- Mirror sync check passes
- Content integrity passes
- `actionlint` passes
- Test suite green

## Dependencies

```
Phase 0 ──→ Phase 1 ──→ Phase 2 ──→ Phase 3
(Dependabot)  (Skill)    (Standards)  (Mirrors)
```

Phases are sequential — each depends on the previous.

## Agent Assignments

| Phase | Agent | Skills Used |
|-------|-------|-------------|
| 0 | build | code, pipeline |
| 1 | build | code, pipeline, document |
| 2 | build | code, standards |
| 3 | build + verify | code, governance |

## Risk Mitigation

- **Token budget**: If the skill exceeds ~3000 tokens, split GitHub Actions and Azure Pipelines into separate reference documents linked from the main SKILL.md
- **Staleness**: Azure Pipelines section marked as "reference pattern" — projects maintain their pipeline implementations
- **Validation**: Every phase ends with a gate check before proceeding
