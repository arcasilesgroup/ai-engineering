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
### Azure Pipelines: Manager Pattern

Organize reusable templates into domain-specific managers. Each manager owns one concern and is composed from the central template repository.

```yaml
# templates/managers/build-manager.yml
parameters:
  - name: buildConfiguration
    type: string
    default: Release
  - name: projects
    type: string
    default: '**/*.csproj'
  - name: pool
    type: string
    default: ubuntu-latest

stages:
  - stage: Build
    pool:
      vmImage: ${{ parameters.pool }}
    jobs:
      - job: BuildJob
        steps:
          - task: UseDotNet@2
            inputs:
              packageType: sdk
              version: '8.x'
          - task: DotNetCoreCLI@2
            displayName: Restore
            inputs:
              command: restore
              projects: ${{ parameters.projects }}
          - task: DotNetCoreCLI@2
            displayName: Build
            inputs:
              command: build
              projects: ${{ parameters.projects }}
              arguments: '--configuration ${{ parameters.buildConfiguration }} --no-restore'
          - task: DotNetCoreCLI@2
            displayName: Test
            inputs:
              command: test
              projects: '**/*Tests.csproj'
              arguments: '--configuration ${{ parameters.buildConfiguration }} --collect:"XPlat Code Coverage"'
          - publish: $(Build.ArtifactStagingDirectory)
            artifact: drop
            displayName: Publish Artifact
```

```yaml
# templates/managers/deploy-manager.yml
parameters:
  - name: environment
    type: string
  - name: serviceConnection
    type: string
  - name: appName
    type: string
  - name: resourceGroup
    type: string
  - name: dependsOn
    type: object
    default: []

stages:
  - stage: Deploy_${{ parameters.environment }}
    dependsOn: ${{ parameters.dependsOn }}
    jobs:
      - deployment: DeployJob
        environment: ${{ parameters.environment }}
        strategy:
          runOnce:
            deploy:
              steps:
                - download: current
                  artifact: drop
                - task: AzureWebApp@1
                  displayName: 'Deploy to ${{ parameters.environment }}'
                  inputs:
                    azureSubscription: ${{ parameters.serviceConnection }}
                    appName: ${{ parameters.appName }}
                    resourceGroupName: ${{ parameters.resourceGroup }}
                    package: '$(Pipeline.Workspace)/drop/**/*.zip'
```

```yaml
# templates/managers/artifact-manager.yml
parameters:
  - name: artifactName
    type: string
    default: drop
  - name: feedName
    type: string
    default: ''

stages:
  - stage: Artifact
    jobs:
      - job: PublishArtifact
        steps:
          - download: current
            artifact: ${{ parameters.artifactName }}
          - ${{ if ne(parameters.feedName, '') }}:
            - task: UniversalPackages@0
              displayName: Publish to Feed
              inputs:
                command: publish
                feedsToUse: internal
                publishDirectory: '$(Pipeline.Workspace)/${{ parameters.artifactName }}'
                vstsFeedPublish: ${{ parameters.feedName }}
                packagePublishDescription: 'Build $(Build.BuildNumber)'
```

```yaml
# templates/managers/security-manager.yml
parameters:
  - name: scanners
    type: object
    default: [credential-scan, dependency-check]

stages:
  - stage: Security
    jobs:
      - job: SecurityScan
        steps:
          - ${{ if containsValue(parameters.scanners, 'credential-scan') }}:
            - task: CredScan@3
              displayName: Credential Scan
          - ${{ if containsValue(parameters.scanners, 'dependency-check') }}:
            - task: DependencyCheck@0
              displayName: OWASP Dependency Check
              inputs:
                projectName: '$(Build.Repository.Name)'
                scanPath: '$(Build.SourcesDirectory)'
                format: 'HTML,JSON'
          - task: PublishTestResults@2
            displayName: Publish Security Results
            condition: always()
            inputs:
              testResultsFormat: JUnit
              testResultsFiles: '**/dependency-check-junit.xml'
```

Compose managers in a project pipeline:

```yaml
# azure-pipelines.yml -- composing managers
resources:
  repositories:
    - repository: templates
      type: git
      name: MyOrg/pipeline-templates
      ref: refs/tags/v2.0

trigger:
  branches:
    include: [main, develop, release/*]

stages:
  - template: managers/build-manager.yml@templates
    parameters:
      buildConfiguration: Release

  - template: managers/security-manager.yml@templates
    parameters:
      scanners: [credential-scan, dependency-check]

  - template: managers/deploy-manager.yml@templates
    parameters:
      environment: INT
      serviceConnection: azure-int
      appName: myapp-int
      resourceGroup: rg-int
      dependsOn: [Build, Security]
```

### Azure Pipelines: SonarCloud Template

Reusable SonarCloud analysis template for Azure Pipelines. Uses the three-task pattern: Prepare, Analyze, Publish.

```yaml
# templates/steps/sonarcloud.yml
parameters:
  - name: sonarOrganization
    type: string
  - name: sonarProjectKey
    type: string
  - name: sonarProjectName
    type: string
  - name: extraProperties
    type: string
    default: ''

steps:
  - task: SonarCloudPrepare@3
    displayName: SonarCloud Prepare
    inputs:
      SonarCloud: 'SonarCloudServiceConnection'
      organization: ${{ parameters.sonarOrganization }}
      scannerMode: 'MSBuild'
      projectKey: ${{ parameters.sonarProjectKey }}
      projectName: ${{ parameters.sonarProjectName }}
      extraProperties: |
        sonar.coverage.exclusions=**/Tests/**
        sonar.cs.opencover.reportsPaths=$(Agent.TempDirectory)/**/coverage.opencover.xml
        ${{ parameters.extraProperties }}

  # Build and test steps run here (caller inserts between Prepare and Analyze)

  - task: SonarCloudAnalyze@3
    displayName: SonarCloud Analyze
    condition: succeeded()

  - task: SonarCloudPublish@3
    displayName: SonarCloud Publish
    condition: succeeded()
    inputs:
      pollingTimeoutSec: 300
```

Usage in a pipeline:

```yaml
# azure-pipelines.yml -- SonarCloud integration
stages:
  - stage: Build
    jobs:
      - job: BuildAndAnalyze
        pool:
          vmImage: ubuntu-latest
        steps:
          - checkout: self
            fetchDepth: 0

          - template: steps/sonarcloud.yml@templates
            parameters:
              sonarOrganization: my-org
              sonarProjectKey: my-org_my-project
              sonarProjectName: My Project

          - task: DotNetCoreCLI@2
            displayName: Build
            inputs:
              command: build
              arguments: '--configuration Release'

          - task: DotNetCoreCLI@2
            displayName: Test with Coverage
            inputs:
              command: test
              arguments: '--configuration Release --collect:"XPlat Code Coverage" -- DataCollectionRunSettings.DataCollectors.DataCollector.Configuration.Format=opencover'

          - task: SonarCloudAnalyze@3
            displayName: SonarCloud Analyze

          - task: SonarCloudPublish@3
            displayName: SonarCloud Publish
            inputs:
              pollingTimeoutSec: 300
```

For Python projects, use the CLI scanner mode instead of MSBuild:

```yaml
# templates/steps/sonarcloud-cli.yml
parameters:
  - name: sonarOrganization
    type: string
  - name: sonarProjectKey
    type: string
  - name: sonarProjectName
    type: string

steps:
  - task: SonarCloudPrepare@3
    displayName: SonarCloud Prepare
    inputs:
      SonarCloud: 'SonarCloudServiceConnection'
      organization: ${{ parameters.sonarOrganization }}
      scannerMode: 'CLI'
      configMode: 'manual'
      cliProjectKey: ${{ parameters.sonarProjectKey }}
      cliProjectName: ${{ parameters.sonarProjectName }}
      extraProperties: |
        sonar.python.coverage.reportPaths=coverage.xml
        sonar.sources=src/
        sonar.tests=tests/

  - task: SonarCloudAnalyze@3
    displayName: SonarCloud Analyze

  - task: SonarCloudPublish@3
    displayName: SonarCloud Publish
    inputs:
      pollingTimeoutSec: 300
```

### Azure Pipelines: Build-Once-Deploy-Many (Artifact Promotion)

Build the artifact once, then promote the same binary through INT, ACC, and PRO environments. Uses pipeline artifacts and deployment jobs with environment approvals.

```yaml
# azure-pipelines.yml -- Build Once, Deploy Many
trigger:
  branches:
    include: [main, develop, release/*]

variables:
  - group: app-settings-common
  - name: buildConfiguration
    value: Release

stages:
  # Stage 1: Build and publish artifact (runs once)
  - stage: Build
    jobs:
      - job: BuildJob
        pool:
          vmImage: ubuntu-latest
        steps:
          - task: DotNetCoreCLI@2
            displayName: Restore
            inputs:
              command: restore
          - task: DotNetCoreCLI@2
            displayName: Build
            inputs:
              command: build
              arguments: '--configuration $(buildConfiguration) --no-restore'
          - task: DotNetCoreCLI@2
            displayName: Test
            inputs:
              command: test
              arguments: '--configuration $(buildConfiguration) --no-build'
          - task: DotNetCoreCLI@2
            displayName: Publish
            inputs:
              command: publish
              arguments: '--configuration $(buildConfiguration) --output $(Build.ArtifactStagingDirectory)'
              zipAfterPublish: true
          - publish: $(Build.ArtifactStagingDirectory)
            artifact: drop
            displayName: Publish Pipeline Artifact

  # Stage 2: Deploy to INT (automatic on develop)
  - stage: Deploy_INT
    dependsOn: Build
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/develop'))
    variables:
      - group: app-settings-INT
    jobs:
      - deployment: DeployINT
        environment: INT
        strategy:
          runOnce:
            deploy:
              steps:
                - download: current
                  artifact: drop
                - task: AzureWebApp@1
                  inputs:
                    azureSubscription: 'azure-int'
                    appName: '$(appName)-int'
                    package: '$(Pipeline.Workspace)/drop/**/*.zip'

  # Stage 3: Deploy to ACC (requires 1 approval, on release branches)
  - stage: Deploy_ACC
    dependsOn: Build
    condition: and(succeeded(), startsWith(variables['Build.SourceBranch'], 'refs/heads/release/'))
    variables:
      - group: app-settings-ACC
    jobs:
      - deployment: DeployACC
        environment: ACC  # configure 1 approval in Azure DevOps
        strategy:
          runOnce:
            deploy:
              steps:
                - download: current
                  artifact: drop
                - task: AzureWebApp@1
                  inputs:
                    azureSubscription: 'azure-acc'
                    appName: '$(appName)-acc'
                    package: '$(Pipeline.Workspace)/drop/**/*.zip'

  # Stage 4: Deploy to PRO (requires 2 approvals, main only)
  - stage: Deploy_PRO
    dependsOn: Deploy_ACC
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    variables:
      - group: app-settings-PRO
    jobs:
      - deployment: DeployPRO
        environment: PRO  # configure 2 approvals + business hours in Azure DevOps
        strategy:
          runOnce:
            deploy:
              steps:
                - download: current
                  artifact: drop
                - task: AzureWebApp@1
                  inputs:
                    azureSubscription: 'azure-pro'
                    appName: '$(appName)-pro'
                    package: '$(Pipeline.Workspace)/drop/**/*.zip'
```

Key principles:
- **Same artifact** -- every environment deploys the exact binary produced in the Build stage via `download: current`.
- **Environment gates** -- approvals are configured on the Azure DevOps Environment resource, not in YAML.
- **Variable groups per environment** -- each stage loads its own `app-settings-<ENV>` variable group for connection strings, feature flags, and URLs.

### Azure Pipelines: Deployment Strategies

Azure Pipelines deployment jobs support three strategies: rolling, canary, and blue-green. Configure these in the `strategy` block of a `deployment` job.

**Rolling Deployment** -- deploy to instances in batches, reducing blast radius:

```yaml
# Rolling: update instances in batches
jobs:
  - deployment: RollingDeploy
    environment:
      name: PRO
      resourceType: VirtualMachine  # requires VM resource in environment
    strategy:
      rolling:
        maxParallel: 25%  # deploy to 25% of targets at a time
        preDeploy:
          steps:
            - script: echo "Validating pre-deployment health"
            - task: AzureCLI@2
              displayName: Health Check Pre-Deploy
              inputs:
                azureSubscription: 'azure-pro'
                scriptType: bash
                scriptLocation: inlineScript
                inlineScript: |
                  az webapp show --name $(appName) --query state -o tsv
        deploy:
          steps:
            - download: current
              artifact: drop
            - task: AzureWebApp@1
              inputs:
                azureSubscription: 'azure-pro'
                appName: '$(appName)'
                package: '$(Pipeline.Workspace)/drop/**/*.zip'
        routeTraffic:
          steps:
            - script: echo "Routing traffic to updated instances"
        postRouteTraffic:
          steps:
            - task: AzureCLI@2
              displayName: Smoke Test
              inputs:
                azureSubscription: 'azure-pro'
                scriptType: bash
                scriptLocation: inlineScript
                inlineScript: |
                  response=$(curl -s -o /dev/null -w "%{http_code}" https://$(appName).azurewebsites.net/health)
                  if [ "$response" != "200" ]; then
                    echo "##vso[task.logissue type=error]Health check failed with status $response"
                    exit 1
                  fi
        on:
          failure:
            steps:
              - script: echo "Rolling deployment failed -- initiating rollback"
          success:
            steps:
              - script: echo "Rolling deployment completed successfully"
```

**Canary Deployment** -- route a percentage of traffic to the new version before full rollout:

```yaml
# Canary: incremental traffic shifting
jobs:
  - deployment: CanaryDeploy
    environment: PRO
    strategy:
      canary:
        increments: [10, 50, 100]  # shift 10%, then 50%, then 100%
        preDeploy:
          steps:
            - script: echo "Preparing canary deployment"
        deploy:
          steps:
            - download: current
              artifact: drop
            - task: AzureWebApp@1
              inputs:
                azureSubscription: 'azure-pro'
                appName: '$(appName)'
                package: '$(Pipeline.Workspace)/drop/**/*.zip'
                deployToSlotOrASE: true
                slotName: canary
        routeTraffic:
          steps:
            - task: AzureAppServiceManage@0
              displayName: 'Route $(strategy.increment)% traffic to canary'
              inputs:
                azureSubscription: 'azure-pro'
                resourceGroupName: '$(resourceGroup)'
                webAppName: '$(appName)'
                action: 'Set Traffic Routing'
                trafficRoutingMethod: percentage
                percentage: $(strategy.increment)
        postRouteTraffic:
          steps:
            - task: AzureCLI@2
              displayName: Validate Canary Health
              inputs:
                azureSubscription: 'azure-pro'
                scriptType: bash
                scriptLocation: inlineScript
                inlineScript: |
                  echo "Validating canary at $(strategy.increment)% traffic"
                  response=$(curl -s -o /dev/null -w "%{http_code}" https://$(appName)-canary.azurewebsites.net/health)
                  if [ "$response" != "200" ]; then
                    echo "##vso[task.logissue type=error]Canary health check failed"
                    exit 1
                  fi
        on:
          failure:
            steps:
              - task: AzureAppServiceManage@0
                displayName: Rollback -- Route 100% to production
                inputs:
                  azureSubscription: 'azure-pro'
                  resourceGroupName: '$(resourceGroup)'
                  webAppName: '$(appName)'
                  action: 'Set Traffic Routing'
                  trafficRoutingMethod: percentage
                  percentage: 0
          success:
            steps:
              - task: AzureAppServiceManage@0
                displayName: Swap canary to production
                inputs:
                  azureSubscription: 'azure-pro'
                  resourceGroupName: '$(resourceGroup)'
                  webAppName: '$(appName)'
                  action: 'Swap Slots'
                  sourceSlot: canary
```

**Blue-Green Deployment** -- deploy to a staging slot, validate, then swap:

```yaml
# Blue-Green: deploy to staging slot, swap after validation
jobs:
  - deployment: BlueGreenDeploy
    environment: PRO
    strategy:
      runOnce:
        deploy:
          steps:
            - download: current
              artifact: drop

            # Deploy to staging slot (green)
            - task: AzureWebApp@1
              displayName: Deploy to Staging Slot
              inputs:
                azureSubscription: 'azure-pro'
                appName: '$(appName)'
                package: '$(Pipeline.Workspace)/drop/**/*.zip'
                deployToSlotOrASE: true
                slotName: staging

            # Validate staging slot
            - task: AzureCLI@2
              displayName: Validate Staging Slot
              inputs:
                azureSubscription: 'azure-pro'
                scriptType: bash
                scriptLocation: inlineScript
                inlineScript: |
                  echo "Running smoke tests against staging slot"
                  response=$(curl -s -o /dev/null -w "%{http_code}" https://$(appName)-staging.azurewebsites.net/health)
                  if [ "$response" != "200" ]; then
                    echo "##vso[task.logissue type=error]Staging validation failed with status $response"
                    exit 1
                  fi

            # Swap staging to production
            - task: AzureAppServiceManage@0
              displayName: Swap Staging to Production
              inputs:
                azureSubscription: 'azure-pro'
                resourceGroupName: '$(resourceGroup)'
                webAppName: '$(appName)'
                action: 'Swap Slots'
                sourceSlot: staging
                targetSlot: production

            # Verify production after swap
            - task: AzureCLI@2
              displayName: Post-Swap Verification
              inputs:
                azureSubscription: 'azure-pro'
                scriptType: bash
                scriptLocation: inlineScript
                inlineScript: |
                  echo "Verifying production after swap"
                  response=$(curl -s -o /dev/null -w "%{http_code}" https://$(appName).azurewebsites.net/health)
                  if [ "$response" != "200" ]; then
                    echo "##vso[task.logissue type=error]Post-swap verification failed -- consider swap-back"
                    exit 1
                  fi
```

| Strategy | Use Case | Rollback | Traffic Control |
|----------|----------|----------|-----------------|
| Rolling | VM-based workloads, batch updates | Automatic on failure | By instance batch |
| Canary | Gradual validation, risk-sensitive releases | Route traffic to 0% canary | Percentage-based increments |
| Blue-Green | Zero-downtime, instant rollback needed | Swap back to previous slot | Slot swap (instant) |

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
