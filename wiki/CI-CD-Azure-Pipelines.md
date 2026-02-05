# Azure Pipelines

> CI/CD pipelines for Azure DevOps-hosted projects.

## Included Pipelines

The framework includes pipelines and reusable templates:

| Pipeline | File | Purpose |
|----------|------|---------|
| CI | `azure-pipelines.yml` | Build, test, lint |
| Security | `pipelines/security.yml` | Secret scanning, audits |
| Quality Gate | `pipelines/quality-gate.yml` | SonarCloud analysis |

## Reusable Templates

| Template | Purpose |
|----------|---------|
| `templates/dotnet-build.yml` | .NET build and test |
| `templates/npm-build.yml` | Node.js build and test |
| `templates/security-scan.yml` | Security scanning |
| `templates/sonar-analysis.yml` | SonarCloud integration |
| `templates/deploy-azure.yml` | Azure deployment |
| `templates/terraform-plan.yml` | Terraform planning |

## Main Pipeline

**File:** `azure-pipelines.yml`

```yaml
trigger:
  branches:
    include:
      - main
      - develop

pr:
  branches:
    include:
      - main

pool:
  vmImage: 'ubuntu-latest'

stages:
  - stage: Build
    jobs:
      - job: BuildAndTest
        steps:
          - task: UseDotNet@2
            inputs:
              version: '8.0.x'

          - script: dotnet restore
            displayName: 'Restore'

          - script: dotnet build --no-restore
            displayName: 'Build'

          - script: dotnet test --no-build --verbosity normal
            displayName: 'Test'

          - script: dotnet format --verify-no-changes
            displayName: 'Lint'

  - stage: Security
    dependsOn: Build
    jobs:
      - template: pipelines/templates/security-scan.yml

  - stage: QualityGate
    dependsOn: Build
    jobs:
      - template: pipelines/templates/sonar-analysis.yml
```

## Template: dotnet-build.yml

```yaml
# pipelines/templates/dotnet-build.yml
parameters:
  - name: dotnetVersion
    type: string
    default: '8.0.x'
  - name: projects
    type: string
    default: '**/*.csproj'

steps:
  - task: UseDotNet@2
    inputs:
      version: ${{ parameters.dotnetVersion }}

  - script: dotnet restore ${{ parameters.projects }}
    displayName: 'Restore'

  - script: dotnet build ${{ parameters.projects }} --no-restore
    displayName: 'Build'

  - script: dotnet test ${{ parameters.projects }} --no-build --collect:"XPlat Code Coverage"
    displayName: 'Test'

  - task: PublishCodeCoverageResults@1
    inputs:
      codeCoverageTool: 'Cobertura'
      summaryFileLocation: '$(Agent.TempDirectory)/**/coverage.cobertura.xml'
```

## Template: security-scan.yml

```yaml
# pipelines/templates/security-scan.yml
jobs:
  - job: SecurityScan
    steps:
      - script: |
          wget -O gitleaks.tar.gz https://github.com/gitleaks/gitleaks/releases/download/v8.18.1/gitleaks_8.18.1_linux_x64.tar.gz
          tar -xzf gitleaks.tar.gz
          ./gitleaks detect --source . --no-git --verbose
        displayName: 'Secret Scan'

      - script: |
          if [ -f "package-lock.json" ]; then
            npm audit --audit-level=high
          fi
        displayName: 'npm Audit'
        continueOnError: true

      - script: |
          if [ -f "requirements.txt" ]; then
            pip install pip-audit
            pip-audit -r requirements.txt
          fi
        displayName: 'pip Audit'
        continueOnError: true
```

## Template: sonar-analysis.yml

```yaml
# pipelines/templates/sonar-analysis.yml
jobs:
  - job: SonarAnalysis
    steps:
      - task: SonarCloudPrepare@1
        inputs:
          SonarCloud: 'SonarCloud Connection'
          organization: '$(sonarOrganization)'
          scannerMode: 'MSBuild'
          projectKey: '$(sonarProjectKey)'
          projectName: '$(Build.Repository.Name)'

      - script: dotnet build
        displayName: 'Build'

      - script: dotnet test --collect:"XPlat Code Coverage"
        displayName: 'Test with Coverage'

      - task: SonarCloudAnalyze@1
        displayName: 'Run Analysis'

      - task: SonarCloudPublish@1
        inputs:
          pollingTimeoutSec: '300'
```

## Service Connections

Configure these service connections in Azure DevOps:

| Connection | Type | Purpose |
|------------|------|---------|
| SonarCloud | SonarCloud | Quality analysis |
| Azure Subscription | Azure Resource Manager | Deployment |

## Variable Groups

Create variable groups for secrets:

```yaml
variables:
  - group: 'production-secrets'
  - name: buildConfiguration
    value: 'Release'
```

## Branch Policies

Configure branch policies for `main`:

1. **Require a minimum number of reviewers:** 1
2. **Check for linked work items:** Required
3. **Build validation:**
   - Pipeline: `azure-pipelines.yml`
   - Policy requirement: Required
4. **Status check:**
   - SonarCloud Quality Gate

## Multi-Stage Deployment

```yaml
stages:
  - stage: Build
    # ... build steps

  - stage: DeployDev
    dependsOn: Build
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/develop'))
    jobs:
      - deployment: DeployToDev
        environment: 'Development'
        strategy:
          runOnce:
            deploy:
              steps:
                - template: pipelines/templates/deploy-azure.yml
                  parameters:
                    environment: 'dev'

  - stage: DeployProd
    dependsOn: Build
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: DeployToProd
        environment: 'Production'
        strategy:
          runOnce:
            deploy:
              steps:
                - template: pipelines/templates/deploy-azure.yml
                  parameters:
                    environment: 'prod'
```

---
**See also:** [GitHub Actions](CI-CD-GitHub-Actions) | [Quality Gates](Standards-Quality-Gates)
