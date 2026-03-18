---
name: pipeline
version: 2.0.0
description: Generate and evolve CI/CD pipelines for GitHub Actions and Azure Pipelines with stack-aware quality and security checks.
tags: [ci-cd, github-actions, azure-pipelines, automation]
---

# CI/CD Pipeline Generation & Evolution

## Purpose

Generate stack-aware CI/CD workflows and guide engineers in evolving them. The generator produces a solid baseline (lint, test, security, gate). This skill teaches the advanced patterns needed for production-grade pipelines.

## Procedure

1. **Detect context** — read `install-manifest.json` for stacks, VCS provider, Sonar config, and `externalReferences.cicd_standards` for team CI/CD docs.
2. **Generate baseline** — run `ai-eng cicd regenerate`. Produces multi-job CI with lint, test, security, and gate jobs. SHA-pinned actions from action-pins.yml (in templates/pipeline/).
3. **Validate** — run `actionlint` on generated files. Run `python scripts/check_workflow_policy.py` to verify timeout, concurrency, and SHA pinning compliance.
4. **Configure Branch Protection** — manual: require `CI Result` (or `ci` job) + `install-smoke` as status checks.
5. **Evolve** — apply advanced patterns below based on project maturity and team CI/CD standards.

## What the Generator Produces

| Provider | Files | Content |
|----------|-------|---------|
| GitHub Actions | `ci.yml`, `ai-pr-review.yml`, `ai-eng-gate.yml` | Multi-job: lint, test, security, gate. Stack-aware. Concurrency, timeouts, SHA pinning. |
| Azure Pipelines | `ci.yml`, `ai-pr-review.yml`, `ai-eng-gate.yml` | Single-stage: stack checks, security. Proper triggers and pool config. |

Stack support: Python (uv/ruff/pytest/ty), .NET (dotnet build/test/format), Node.js (npm/eslint/vitest).

## Advanced Patterns

### CI Result Gate (GitHub Actions)

Single aggregator job that replaces 20+ individual Branch Protection checks. Handles conditional jobs (docs-only PRs, Dependabot, fork contributions) without blocking merge.

```yaml
ci-result:
  name: CI Result
  if: always()
  timeout-minutes: 5
  needs: [change-scope, lint, test, security, build, sonarcloud, verify-trailers]
  runs-on: ubuntu-latest
  steps:
    - name: Evaluate
      run: |
        # Categories: always-required, code-conditional, pr-only, optional
        # always-required: MUST succeed
        # code-conditional: MUST succeed when code changed, skip OK otherwise
        # pr-only: MUST succeed on non-Dependabot PRs
        # optional: may skip but MUST NOT fail

        CODE="${{ needs.change-scope.outputs.code }}"
        IS_PR="${{ github.event_name == 'pull_request' }}"

        # Validate change-scope succeeded (prevents bypass)
        if [[ "${{ needs.change-scope.result }}" != "success" ]]; then
          echo "::error::change-scope failed"; exit 1
        fi

        # Evaluate each category...
        for entry in "${always_required[@]}"; do
          # result must be "success"
        done
        for entry in "${code_conditional[@]}"; do
          # if CODE==true: must be "success"; else: "failure" is error
        done
```

Branch Protection: require only `CI Result` as status check.

### Path-Based Conditional Execution

Use `dorny/paths-filter` to skip expensive jobs on docs-only changes:

```yaml
change-scope:
  runs-on: ubuntu-latest
  outputs:
    code: ${{ steps.filter.outputs.code }}
  steps:
    - uses: actions/checkout@v4
      with: { fetch-depth: 0 }
    - uses: dorny/paths-filter@SHA  # pin from action-pins.yml
      id: filter
      with:
        filters: |
          code:
            - 'src/**'
            - 'tests/**'
            - 'scripts/**'
            - '**/*.py'
            - '**/*.toml'
            - 'uv.lock'

lint:
  needs: [change-scope]
  if: needs.change-scope.outputs.code == 'true'
```

### Matrix Strategy

Multi-OS, multi-version testing:

```yaml
test:
  strategy:
    fail-fast: false
    matrix:
      os: [ubuntu-latest, windows-latest, macos-latest]
      python-version: ["3.11", "3.12", "3.13"]
  runs-on: ${{ matrix.os }}
  steps:
    - uses: astral-sh/setup-uv@SHA
    - run: uv python install ${{ matrix.python-version }}
    - run: uv sync --dev
    - run: uv run pytest tests/ -v -n auto
```

### SonarCloud Integration

Add after test jobs to analyze coverage:

```yaml
sonarcloud:
  needs: [test]
  if: needs.change-scope.outputs.code == 'true'
  steps:
    - uses: actions/checkout@v4
      with: { fetch-depth: 0 }
    - uses: actions/download-artifact@v4
      with: { pattern: "coverage-*", merge-multiple: true }
    - uses: SonarSource/sonarqube-scan-action@SHA
      env: { SONAR_TOKEN: "${{ secrets.SONAR_TOKEN }}" }
      with:
        args: >
          -Dsonar.python.coverage.reportPaths=coverage.xml
```

### SHA Pinning Policy

All third-party actions must use SHA pins. First-party (`actions/*`) may use major tags.

```yaml
# Correct — SHA-pinned with tag comment
- uses: astral-sh/setup-uv@d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86 # v5.4.2

# Acceptable — first-party
- uses: actions/checkout@v4

# Prohibited — mutable tag
- uses: some-org/some-action@v2
```

Centralized pins: action-pins.yml (in templates/pipeline/). Dependabot updates SHAs automatically.

### Dependabot Configuration

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule: { interval: "weekly", day: "monday" }
    commit-message: { prefix: "chore(deps)", prefix-development: "chore(deps-dev)" }
    groups:
      python-dependencies: { patterns: ["*"] }
    open-pull-requests-limit: 5
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule: { interval: "weekly", day: "monday" }
    commit-message: { prefix: "ci(deps)" }
    groups:
      github-actions: { patterns: ["*"] }
```

### Environment Protection & Deployment

```yaml
# GitHub Environments — configure in Settings > Environments
deploy-staging:
  environment:
    name: staging
  steps:
    - run: deploy --target staging

deploy-production:
  needs: [deploy-staging]
  environment:
    name: production  # requires approval reviewers
    url: https://app.example.com
  steps:
    - run: deploy --target production
```

### Build-Once-Deploy-Many (Release)

```yaml
# CI builds artifact → Release downloads same artifact → Publishes
publish:
  needs: [verify-ci]
  steps:
    - uses: actions/download-artifact@v4
      with:
        name: dist
        run-id: ${{ needs.verify-ci.outputs.ci-run-id }}
    - uses: pypa/gh-action-pypi-publish@SHA
```

### Reusable Workflows (`workflow_call`)

Create shared CI logic consumed by multiple repositories or workflows:

```yaml
# .github/workflows/reusable-test.yml — Callee
name: Reusable Test Suite
on:
  workflow_call:
    inputs:
      python-version:
        type: string
        default: "3.12"
    secrets:
      SONAR_TOKEN:
        required: true
    outputs:
      coverage:
        description: "Coverage percentage"
        value: ${{ jobs.test.outputs.cov }}

jobs:
  test:
    runs-on: ubuntu-latest
    outputs:
      cov: ${{ steps.cov.outputs.pct }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@SHA
      - run: uv run pytest --cov --cov-report=xml
      - id: cov
        run: echo "pct=$(coverage report --format=total)" >> "$GITHUB_OUTPUT"
```

```yaml
# .github/workflows/ci.yml — Caller
jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      python-version: "3.12"
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

  # Cross-repo reusable workflow
  lint:
    uses: org/shared-workflows/.github/workflows/lint.yml@main
    secrets: inherit
```

Constraints: max 4 levels of nesting; `secrets: inherit` passes all caller secrets.

### Composite Actions

Bundle multi-step logic into a single reusable action:

```yaml
# .github/actions/setup-python-env/action.yml
name: "Setup Python Environment"
description: "Install Python, uv, and project dependencies"
inputs:
  python-version:
    description: "Python version"
    required: false
    default: "3.12"
outputs:
  cache-hit:
    description: "Whether cache was hit"
    value: ${{ steps.cache.outputs.cache-hit }}
runs:
  using: composite
  steps:
    - uses: actions/setup-python@v5
      with:
        python-version: ${{ inputs.python-version }}
    - uses: astral-sh/setup-uv@SHA
    - id: cache
      uses: actions/cache@v4
      with:
        path: .cache/uv
        key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
    - run: uv sync --frozen
      shell: bash  # required for composite actions
```

Usage: `- uses: ./.github/actions/setup-python-env` (local) or `- uses: org/repo/.github/actions/setup-python-env@SHA` (cross-repo).

### Caching Strategies

Use `actions/cache` with stack-specific paths and key patterns:

```yaml
# Python (uv)
- uses: actions/cache@v4
  with:
    path: .cache/uv
    key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
    restore-keys: uv-${{ runner.os }}-

# Node.js (npm)
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: npm-${{ runner.os }}-${{ hashFiles('package-lock.json') }}
    restore-keys: npm-${{ runner.os }}-

# .NET (NuGet)
- uses: actions/cache@v4
  with:
    path: ~/.nuget/packages
    key: nuget-${{ runner.os }}-${{ hashFiles('**/*.csproj') }}
    restore-keys: nuget-${{ runner.os }}-

# Rust (cargo)
- uses: actions/cache@v4
  with:
    path: |
      ~/.cargo/registry
      ~/.cargo/git
      target/
    key: cargo-${{ runner.os }}-${{ hashFiles('Cargo.lock') }}
    restore-keys: cargo-${{ runner.os }}-
```

Key pattern: `<tool>-<os>-<lockfile-hash>`. Always provide `restore-keys` for partial cache hits.

### Status Badges

Add CI status badges to README:

```markdown
![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)
![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg?branch=main)
![Release](https://github.com/OWNER/REPO/actions/workflows/release.yml/badge.svg?event=release)
```

Pattern: `https://github.com/{owner}/{repo}/actions/workflows/{workflow}.yml/badge.svg` with optional `?branch=` or `?event=` query params.

### Merge Queue

Enable merge queue with `merge_group` event trigger:

```yaml
on:
  pull_request:
    branches: [main]
  merge_group:       # Triggered when PR enters merge queue
    types: [checks_requested]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: uv run pytest
```

Setup: Settings > Branch protection > Require merge queue. The queue batches PRs, runs CI on the merged result, and merges only if checks pass. Use `merge_group` alongside `pull_request` so the same workflow validates both PR checks and queue checks.

### Azure Pipelines: Template Composition

Central template repository with `resources.repositories`:

```yaml
# Project pipeline
resources:
  repositories:
    - repository: templates
      type: git
      name: MyOrg/pipeline-templates
      ref: refs/tags/v2.0

stages:
  - template: stages/ci.yml@templates
    parameters:
      buildConfiguration: Release
      pool: ubuntu-latest

  - template: stages/deploy.yml@templates
    parameters:
      environment: production
      serviceConnection: azure-prod
```

### Azure Pipelines: Variable Groups & KeyVault

```yaml
variables:
  - group: app-settings-$(Environment)  # INT, ACC, PRO
  - name: buildConfiguration
    value: Release

# KeyVault-linked variable group (configured in Azure DevOps UI)
# Secrets: ConnectionString, ApiKey, Certificate
```

### Azure Pipelines: Branch-Conditional Deployment

| Branch | Environment | Approval |
|--------|-------------|----------|
| `develop` | Integration (INT) | None |
| `release/*` | Acceptance (ACC) | 1 reviewer |
| `main` | Production (PRO) | 2 reviewers + business hours |

## What Requires Manual Setup

- **Branch Protection** — Settings > Branches: require `CI Result` + `install-smoke`
- **GitHub Environments** — protection rules, required reviewers, deployment branches
- **Azure DevOps Environments** — approval gates, exclusive locks
- **Secrets** — `SONAR_TOKEN`, `SNYK_TOKEN`, deployment credentials (use OIDC when possible)
- **Self-hosted runners** — configure runner groups and labels
- **Deployment targets** — Railway, Vercel, Cloudflare, Netlify (platform-specific config)

## Output Contract

- Generated workflow files in `.github/workflows/` or `.azure-pipelines/`
- `dependabot.yml` configuration
- Validation report (actionlint results)
- Branch Protection recommendations

## Governance Notes

- Generated workflows are **project-managed** — the generator produces once, the project evolves.
- Workflows must replicate local gate checks per `standards/framework/cicd/core.md`.
- Secret values must use platform secrets, never hardcoded.
- If team has external CI/CD standards (`externalReferences.cicd_standards` in manifest), incorporate those requirements.

## References

- `standards/framework/cicd/core.md` — CI/CD standards (pinning, Dependabot, Azure, environments, ci-result pattern)
- action-pins.yml (in templates/pipeline/) — centralized SHA pins
- `manifest.yml` — per-stack enforcement check definitions
- `standards/framework/stacks/python.md` — Python check details
- `standards/framework/stacks/dotnet.md` — .NET check details
- `standards/framework/stacks/nextjs.md` — Next.js check details
- `standards/framework/stacks/azure.md` — Azure Pipelines patterns
