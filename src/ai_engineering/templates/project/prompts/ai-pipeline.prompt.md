---
name: ai-pipeline
description: "Use when creating or evolving CI/CD pipelines: stack-aware generation for GitHub Actions and Azure Pipelines with security enforcement."
model: opus
effort: high
argument-hint: "generate|evolve|validate|--provider github|azure"
mode: agent
tags: [ci-cd, github-actions, azure-pipelines, enterprise]
---



# CI/CD Pipeline

Router skill for CI/CD pipeline generation. Dispatches to handler files based on sub-command.

## When to Use

- Creating new CI/CD pipelines for a project.
- Evolving existing pipelines with advanced patterns.
- Validating pipeline compliance (SHA pinning, timeouts, concurrency).
- NOT for running pipelines -- that is the CI system's job.

## Routing

| Sub-command | Handler | Purpose |
|-------------|---------|---------|
| `generate` | `handlers/generate.md` | Create new pipeline from project analysis |
| `evolve` | `handlers/evolve.md` | Add advanced patterns to existing pipeline |
| `validate` | `handlers/validate.md` | Check pipeline compliance |

Default (no sub-command): `generate`.

## Quick Reference

```
/ai-pipeline generate                    # new pipeline from project analysis
/ai-pipeline generate --provider azure   # Azure Pipelines specifically
/ai-pipeline evolve                      # add advanced patterns
/ai-pipeline validate                    # check compliance
```

## Shared Rules

- **SHA pinning**: all third-party actions use SHA pins. First-party (`actions/*`) may use major tags.
- **No `*` versions**: explicit version constraints always.
- **OIDC auth**: prefer OIDC over long-lived secrets.
- **Timeouts**: every job must have `timeout-minutes`.
- **Concurrency**: group by branch to prevent parallel runs.

## Integration

- Stack detection: reads `pyproject.toml`, `*.csproj`, `package.json`, `Cargo.toml`.
- Validation: `actionlint` for GitHub Actions.
- Policy: `scripts/check_workflow_policy.py` for SHA pinning and timeout compliance.

## References

- `.ai-engineering/manifest.yml` -- CI/CD standards.
- `.ai-engineering/contexts/` -- per-stack check definitions.
$ARGUMENTS

---

# Handler: evolve

Add advanced patterns to existing CI/CD pipelines.

## Process

1. **Read existing pipeline** -- parse current workflow files.
2. **Assess maturity** -- identify which patterns are already applied.
3. **Recommend patterns** -- based on project needs:

## Available Patterns

### CI Result Gate (GitHub Actions)
Single aggregator job replacing 20+ Branch Protection checks. Handles conditional jobs (docs-only PRs, Dependabot, fork contributions) without blocking merge.

### Path-Based Conditional Execution
Use `dorny/paths-filter` to skip expensive jobs on docs-only changes. Define `change-scope` job with output filtering.

### Matrix Strategy
Multi-OS, multi-version testing with `fail-fast: false`. Combine OS and language version dimensions.

### SonarCloud Integration
Add Sonar analysis after test jobs. Configure coverage report paths per stack.

### Merge Queue
Enable `merge_group` event trigger alongside `pull_request`. Batches PRs, runs CI on merged result.

### Reusable Workflows
Extract shared logic into `workflow_call` workflows. Cross-repo with `secrets: inherit`. Max 4 nesting levels.

### Composite Actions
Bundle multi-step logic into `.github/actions/<name>/action.yml`. Require `shell: bash` for composite steps.

### Caching Strategies
Stack-specific cache paths and key patterns: `<tool>-<os>-<lockfile-hash>`. Always provide `restore-keys`.

### Environment Protection & Deployment
GitHub Environments with approval reviewers. Build-once-deploy-many with artifact promotion.

### Azure Pipelines: Template Composition
Central template repository with `resources.repositories`. Manager pattern: build-manager, deploy-manager, security-manager, artifact-manager.

### Azure Pipelines: Deployment Strategies
Rolling (VM batches), Canary (incremental traffic), Blue-Green (slot swap). Each with health checks and rollback.

## Output

- Updated workflow files with new patterns.
- Validation report (`actionlint`).
- Migration notes for any breaking changes.
# Handler: generate

Create new CI/CD pipeline from project analysis.

## Process

1. **Detect context**:
   - Read project files for stacks: `pyproject.toml` (Python), `*.csproj` (.NET), `package.json` (Node), `Cargo.toml` (Rust).
   - Read `manifest.yml` for VCS provider, Sonar config.
   - Read `externalReferences.cicd_standards` for team CI/CD docs.

2. **Select provider**:
   - `--provider github`: GitHub Actions (`.github/workflows/`).
   - `--provider azure`: Azure Pipelines (`.azure-pipelines/`).
   - Default: detect from `git remote get-url origin`.

3. **Generate baseline** -- run `ai-eng cicd regenerate`. Produces:

   | Provider | Files | Content |
   |----------|-------|---------|
   | GitHub Actions | `ci.yml`, `ai-pr-review.yml` | Multi-job: lint, test, security, gate. Concurrency, timeouts, SHA pinning. |
   | Azure Pipelines | `ci.yml`, `ai-pr-review.yml` | Single-stage: stack checks, security. Triggers and pool config. |

4. **Apply stack checks**:
   - Python: `ruff check`, `ruff format --check`, `pytest`, `pip-audit`, `ty check`.
   - .NET: `dotnet build`, `dotnet test`, `dotnet format --verify-no-changes`.
   - Node: `eslint`, `vitest`, `npm audit`.
   - Rust: `cargo check`, `cargo clippy`, `cargo test`, `cargo audit`.

5. **Apply security**:
   - SHA pin all third-party actions (reference `action-pins.yml`).
   - Add `gitleaks` and `semgrep` jobs.
   - Add `pip-audit` / `npm audit` / `cargo audit` per stack.
   - Configure OIDC for deployment steps where possible.

6. **Apply infrastructure**:
   - `timeout-minutes` on every job.
   - Concurrency group by branch: `group: ${{ github.ref }}`.
   - `dependabot.yml` for automated dependency updates.

7. **Validate** -- `actionlint` on generated files. Fix any issues.

## Output

- Generated workflow files.
- `dependabot.yml` configuration.
- Validation report.
- Branch Protection recommendations.
# Handler: validate

Check CI/CD pipeline compliance against governance standards.

## Process

1. **Lint workflows**:
   - GitHub Actions: `actionlint` on all `.github/workflows/*.yml`.
   - Azure Pipelines: YAML schema validation.

2. **Check SHA pinning**:
   - Run `python scripts/check_workflow_policy.py` (or manual scan).
   - Every third-party action must use SHA pin with tag comment.
   - First-party (`actions/*`) may use major tags.
   - Prohibited: mutable tags like `@v2` on third-party actions.

3. **Check timeouts**:
   - Every job must have `timeout-minutes`.
   - Default should not exceed 30 minutes for standard jobs.

4. **Check concurrency**:
   - Workflows must define `concurrency` group to prevent parallel runs.
   - Typical: `group: ${{ github.workflow }}-${{ github.ref }}`.

5. **Check security**:
   - No hardcoded secrets in workflow files.
   - OIDC preferred over long-lived credentials.
   - `permissions` block is minimal (principle of least privilege).
   - No `permissions: write-all`.

6. **Check environment protection**:
   - Production deployments use protected environments.
   - Approval gates configured for production.

7. **Check stack coverage**:
   - For each declared stack, verify corresponding lint/test/security jobs exist.
   - Cross-reference with `manifest.yml` enforcement checks.

## Output

```markdown
## Pipeline Compliance Report

| Check | Status | Detail |
|-------|--------|--------|
| SHA Pinning | PASS/FAIL | N actions pinned, M unpinned |
| Timeouts | PASS/FAIL | N jobs with timeout, M without |
| Concurrency | PASS/FAIL | Groups defined / missing |
| Security | PASS/FAIL | Hardcoded secrets / OIDC status |
| Stack Coverage | PASS/FAIL | Stacks covered / missing |
| Lint (actionlint) | PASS/FAIL | N warnings, M errors |
```
