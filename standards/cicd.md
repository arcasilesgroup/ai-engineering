# CI/CD Standards

> Standards for continuous integration and continuous deployment using GitHub Actions and Azure Pipelines. Covers pipeline-as-code patterns, reusable workflows/templates, environment promotion, artifact management, and release gating.

---

## 1. General Principles

- **Pipeline as Code**: All CI/CD definitions live in version control alongside the application code.
- **Immutable Artifacts**: Build once, deploy everywhere. Never rebuild for different environments.
- **Fail Fast**: Run cheapest checks first (lint → build → unit tests → integration → security → quality gate).
- **Minimal Permissions**: CI/CD runners use least-privilege access. Never use admin credentials.
- **Reproducible Builds**: Pin dependency versions, tool versions, and base images.
- **Secret Management**: Never hardcode secrets. Use platform-native secret stores (GitHub Secrets, Azure Key Vault).

---

## 2. GitHub Actions Standards

### Workflow Structure

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read       # Minimal permissions
  pull-requests: write # Only if needed

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup
        uses: actions/setup-node@v4  # Pin to major version
        with:
          node-version-file: '.nvmrc'  # Version from file, not hardcoded
          cache: 'npm'
      - run: npm ci           # ci, not install
      - run: npm run lint
      - run: npm test
      - run: npm run build
```

### Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Workflow files | `kebab-case.yml` | `ci.yml`, `security-scan.yml` |
| Job names | `kebab-case` | `build-and-test` |
| Step names | Sentence case | `Run unit tests` |
| Environment names | lowercase | `development`, `staging`, `production` |
| Secret names | `UPPER_SNAKE_CASE` | `SONAR_TOKEN`, `SNYK_TOKEN` |

### Reusable Workflows

Extract common patterns into reusable workflows:

```yaml
# .github/workflows/reusable-build.yml
on:
  workflow_call:
    inputs:
      node-version:
        required: false
        type: string
        default: '20'
    secrets:
      NPM_TOKEN:
        required: false
```

Call with:

```yaml
jobs:
  build:
    uses: ./.github/workflows/reusable-build.yml
    with:
      node-version: '20'
    secrets: inherit
```

### Caching

Always cache dependencies:

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.nuget/packages
    key: ${{ runner.os }}-nuget-${{ hashFiles('**/*.csproj') }}
    restore-keys: |
      ${{ runner.os }}-nuget-
```

### Anti-Patterns

| Anti-Pattern | Correct Pattern |
|-------------|----------------|
| `npm install` | `npm ci` (deterministic) |
| Hardcoded versions in workflow | Version files (`.nvmrc`, `global.json`) |
| `actions/checkout@master` | `actions/checkout@v4` (pinned) |
| `permissions: write-all` | Specific minimal permissions |
| Secrets in workflow logs | Mask with `::add-mask::` |
| Single monolithic workflow | Split by concern (ci, security, deploy) |

---

## 3. Azure Pipelines Standards

### Pipeline Structure

```yaml
trigger:
  branches:
    include: [main]

pr:
  branches:
    include: [main]

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: 'common-variables'  # Variable groups, not inline secrets

stages:
  - stage: Build
    jobs:
      - job: BuildAndTest
        steps:
          - task: UseDotNet@2
            inputs:
              packageType: 'sdk'
              useGlobalJson: true  # Version from global.json
          - script: dotnet build
          - script: dotnet test
```

### Reusable Templates

Extract common patterns into templates in `pipelines/templates/`:

```yaml
# pipelines/templates/dotnet-build.yml
parameters:
  - name: solution
    type: string
    default: '**/*.sln'
  - name: buildConfiguration
    type: string
    default: 'Release'

steps:
  - task: UseDotNet@2
    inputs:
      useGlobalJson: true
  - script: dotnet restore ${{ parameters.solution }}
  - script: dotnet build ${{ parameters.solution }} -c ${{ parameters.buildConfiguration }}
  - script: dotnet test ${{ parameters.solution }} -c ${{ parameters.buildConfiguration }} --no-build
```

Reference with:

```yaml
steps:
  - template: templates/dotnet-build.yml
    parameters:
      solution: 'src/MyProject.sln'
```

### Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Pipeline files | `kebab-case.yml` | `ci.yml`, `security.yml` |
| Stage names | `PascalCase` | `Build`, `DeployStaging` |
| Job names | `PascalCase` | `BuildAndTest` |
| Variable groups | `kebab-case` | `common-variables` |
| Service connections | `kebab-case` | `azure-subscription-prod` |

---

## 4. Environment Promotion Strategy

```
Feature Branch → PR → main → Staging → Production
    │              │      │        │          │
    │              │      │        │          └── Manual approval + gates
    │              │      │        └── Auto-deploy after quality gates
    │              │      └── CI: build + test + security + quality
    │              └── PR checks must pass
    └── Developer runs /ship, /test, verify-app agent
```

### Environment Gates

| Environment | Gates | Approval |
|-------------|-------|----------|
| Development | Build + unit tests | Automatic |
| Staging | All CI checks + integration tests | Automatic |
| Production | All staging gates + performance tests | Manual approval required |

---

## 5. Artifact Management

- **Build artifacts**: Store build outputs for deployment (not rebuilding).
- **Test results**: Publish as pipeline artifacts for visibility.
- **Coverage reports**: Upload to SonarQube and publish as artifacts.
- **Security reports**: Store scan results as artifacts for audit trail.

```yaml
# GitHub Actions
- uses: actions/upload-artifact@v4
  with:
    name: build-output
    path: dist/
    retention-days: 30

# Azure Pipelines
- task: PublishBuildArtifacts@1
  inputs:
    pathToPublish: '$(Build.ArtifactStagingDirectory)'
    artifactName: 'build-output'
```

---

## 6. Security in CI/CD

### Secret Management

| Platform | Secret Store | Usage |
|----------|-------------|-------|
| GitHub | Repository/Organization Secrets | `${{ secrets.SECRET_NAME }}` |
| Azure DevOps | Variable Groups + Key Vault | `$(SECRET_NAME)` or Key Vault task |

### Required Security Checks in CI

1. **Secret scanning**: gitleaks (every PR)
2. **Dependency scanning**: Snyk or OWASP Dependency-Check (every PR)
3. **SAST**: CodeQL (GitHub) or SonarQube (both platforms) (every PR)
4. **License compliance**: Check dependency licenses (weekly)

### Pipeline Security

- Never echo secrets or tokens in logs.
- Use `--quiet` flags where possible to reduce log noise.
- Pin action/task versions to SHA or major version.
- Restrict who can modify pipeline definitions.
- Use branch protection rules / branch policies.

---

## 7. Monitoring and Alerting

- **Build duration**: Alert if build time increases > 50% from baseline.
- **Flaky tests**: Track and quarantine tests that fail intermittently.
- **Security scan results**: Alert on new critical/high vulnerabilities.
- **Quality gate trends**: Track quality metrics over time.
