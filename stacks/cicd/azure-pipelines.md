# Azure Pipelines Standards

These standards govern how an AI coding assistant writes, maintains, and optimizes Azure Pipelines. Follow these patterns for every Azure Pipeline you create or modify.

---

## YAML Pipeline Structure

### Basic Structure

```yaml
trigger:
  branches:
    include:
      - main
  paths:
    exclude:
      - '*.md'
      - 'docs/**'

pr:
  branches:
    include:
      - main

pool:
  vmImage: 'ubuntu-latest'

variables:
  - name: nodeVersion
    value: '20'

stages:
  - stage: Build
    displayName: 'Build and Test'
    jobs:
      - job: Build
        displayName: 'Build Application'
        timeoutInMinutes: 15
        steps:
          - task: NodeTool@0
            displayName: 'Install Node.js'
            inputs:
              versionSpec: $(nodeVersion)
          - script: npm ci
            displayName: 'Install dependencies'
          - script: npm run build
            displayName: 'Build'
```

### Structure Rules

- Always use YAML pipelines. Never use the classic (GUI) editor for new pipelines.
- Set `timeoutInMinutes` on every job.
- Give every stage, job, and step a descriptive `displayName`.
- Use `stages` for logical groups (Build, Test, Deploy). Use `jobs` for parallelizable units within a stage. Use `steps` for sequential operations within a job.
- Place the pipeline YAML file in the repository root as `azure-pipelines.yml` or in a dedicated directory like `.azure-pipelines/`.

---

## Template System

Templates are the primary mechanism for reusing pipeline logic across projects. Use them aggressively.

### Step Templates

Extract common step sequences into templates.

```yaml
# templates/steps/setup-node.yml
parameters:
  - name: nodeVersion
    type: string
    default: '20'

steps:
  - task: NodeTool@0
    displayName: 'Install Node.js ${{ parameters.nodeVersion }}'
    inputs:
      versionSpec: ${{ parameters.nodeVersion }}

  - task: Cache@2
    displayName: 'Cache npm packages'
    inputs:
      key: 'npm | "$(Agent.OS)" | package-lock.json'
      restoreKeys: |
        npm | "$(Agent.OS)"
      path: $(npm_config_cache)

  - script: npm ci
    displayName: 'Install dependencies'
```

### Job Templates

```yaml
# templates/jobs/test.yml
parameters:
  - name: nodeVersion
    type: string
    default: '20'
  - name: workingDirectory
    type: string
    default: '.'

jobs:
  - job: Test
    displayName: 'Run Tests'
    timeoutInMinutes: 15
    steps:
      - template: ../steps/setup-node.yml
        parameters:
          nodeVersion: ${{ parameters.nodeVersion }}

      - script: npm test -- --coverage
        displayName: 'Run tests'
        workingDirectory: ${{ parameters.workingDirectory }}

      - task: PublishTestResults@2
        displayName: 'Publish test results'
        condition: succeededOrFailed()
        inputs:
          testResultsFormat: 'JUnit'
          testResultsFiles: '**/junit.xml'
          mergeTestResults: true

      - task: PublishCodeCoverageResults@2
        displayName: 'Publish code coverage'
        condition: succeededOrFailed()
        inputs:
          summaryFileLocation: '**/coverage/cobertura-coverage.xml'
```

### Stage Templates

```yaml
# templates/stages/deploy.yml
parameters:
  - name: environment
    type: string
  - name: serviceConnection
    type: string
  - name: appName
    type: string
  - name: dependsOn
    type: object
    default: []

stages:
  - stage: Deploy_${{ parameters.environment }}
    displayName: 'Deploy to ${{ parameters.environment }}'
    dependsOn: ${{ parameters.dependsOn }}
    condition: succeeded()
    jobs:
      - deployment: Deploy
        displayName: 'Deploy ${{ parameters.appName }}'
        timeoutInMinutes: 15
        environment: ${{ parameters.environment }}
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureWebApp@1
                  displayName: 'Deploy to Azure Web App'
                  inputs:
                    azureSubscription: ${{ parameters.serviceConnection }}
                    appName: ${{ parameters.appName }}
                    package: '$(Pipeline.Workspace)/drop/**/*.zip'
```

### Using Templates

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
      - main

stages:
  - stage: Build
    displayName: 'Build'
    jobs:
      - job: Build
        timeoutInMinutes: 15
        steps:
          - template: templates/steps/setup-node.yml
            parameters:
              nodeVersion: '20'
          - script: npm run build
            displayName: 'Build application'
          - publish: $(System.DefaultWorkingDirectory)/dist
            artifact: drop

  - template: templates/stages/deploy.yml
    parameters:
      environment: staging
      serviceConnection: 'azure-staging'
      appName: 'myapp-staging'
      dependsOn: ['Build']

  - template: templates/stages/deploy.yml
    parameters:
      environment: production
      serviceConnection: 'azure-production'
      appName: 'myapp-production'
      dependsOn: ['Deploy_staging']
```

### Template Rules

- Store templates in a `templates/` directory organized by type: `templates/steps/`, `templates/jobs/`, `templates/stages/`.
- Every template parameter must have a `type` declaration.
- Provide sensible `default` values for optional parameters.
- Use a central template repository for organization-wide templates and reference it with `resources.repositories`.
- Templates must be self-contained. Do not rely on variables defined outside the template unless they are passed as parameters.

---

## Variable Groups and Library

### Defining Variables

```yaml
variables:
  # Inline variables
  - name: buildConfiguration
    value: 'Release'

  # Variable group from Azure DevOps Library
  - group: 'common-variables'

  # Template expression variable
  - name: isMain
    value: ${{ eq(variables['Build.SourceBranch'], 'refs/heads/main') }}
```

### Variable Group Best Practices

- Use variable groups for environment-specific configuration (connection strings, feature flags).
- Link variable groups to Azure Key Vault for secrets.
- Name variable groups consistently: `{project}-{environment}-variables` (e.g., `myapp-production-variables`).
- Never store secrets as plain-text pipeline variables. Always use Key Vault-linked variable groups or secret variables.
- Scope variable groups to specific pipelines and environments using security settings.

```yaml
variables:
  - group: 'myapp-common'
  - ${{ if eq(variables['Build.SourceBranch'], 'refs/heads/main') }}:
    - group: 'myapp-production'
  - ${{ else }}:
    - group: 'myapp-staging'
```

---

## Pipeline Triggers

### CI Triggers

```yaml
trigger:
  branches:
    include:
      - main
      - release/*
    exclude:
      - feature/experimental/*
  paths:
    include:
      - src/**
      - package.json
      - package-lock.json
    exclude:
      - '**/*.md'
      - docs/**
  tags:
    include:
      - v*
```

### PR Triggers

```yaml
pr:
  branches:
    include:
      - main
      - release/*
  paths:
    include:
      - src/**
    exclude:
      - '**/*.md'
  drafts: false  # Do not trigger on draft PRs
```

### Scheduled Triggers

```yaml
schedules:
  - cron: '0 2 * * 1-5'  # Weekdays at 2 AM UTC
    displayName: 'Nightly build'
    branches:
      include:
        - main
    always: false  # Only run if there are changes since the last run
```

### Trigger Rules

- Always set path filters to avoid running pipelines when only documentation or unrelated files change.
- Set `drafts: false` on PR triggers to skip draft pull requests.
- Use `always: false` on scheduled triggers to avoid unnecessary runs.
- Disable CI triggers on feature branches if PR triggers cover validation.

---

## Agent Pools

### Microsoft-Hosted Agents

```yaml
pool:
  vmImage: 'ubuntu-latest'  # Preferred default
```

Use Microsoft-hosted agents unless you need:
- Access to internal network resources.
- Specialized hardware or software.
- Longer build times (Microsoft-hosted agents have time limits).
- Lower costs at high volume.

### Self-Hosted Agents

```yaml
pool:
  name: 'MyAgentPool'
  demands:
    - Agent.OS -equals Linux
    - docker
```

### Self-Hosted Agent Rules

- Use agent pools to organize self-hosted agents by capability.
- Use demands to ensure jobs run on agents with the required capabilities.
- Keep self-hosted agents up to date with the latest agent software.
- Use ephemeral agents (scale set agents) when possible to ensure clean build environments.
- Never install sensitive credentials on self-hosted agents. Use service connections and variable groups instead.

---

## Service Connections

Service connections provide authenticated access to external services.

- Create service connections in Azure DevOps project settings, not inline in pipelines.
- Use workload identity federation (OIDC) service connections instead of secret-based connections where supported.
- Name service connections consistently: `{provider}-{environment}` (e.g., `azure-production`, `aws-staging`).
- Restrict service connection access to specific pipelines using security settings.
- Use separate service connections for each environment to enforce least privilege.

```yaml
- task: AzureCLI@2
  displayName: 'Run Azure CLI command'
  inputs:
    azureSubscription: 'azure-production'  # Service connection name
    scriptType: 'bash'
    scriptLocation: 'inlineScript'
    inlineScript: |
      az webapp list --output table
```

---

## Environments and Approvals

### Environment Configuration

Define environments in Azure DevOps for deployment tracking and approval gates.

```yaml
jobs:
  - deployment: DeployToProduction
    displayName: 'Deploy to Production'
    environment: production
    strategy:
      runOnce:
        deploy:
          steps:
            - script: echo "Deploying to production"
```

### Approval Gates

Configure these in the Azure DevOps environment settings:

- **Pre-deployment approvals**: Require manual approval before deploying to staging or production.
- **Branch control**: Restrict which branches can deploy to an environment.
- **Business hours**: Limit deployments to specific hours.
- **Exclusive lock**: Prevent concurrent deployments to the same environment.

### Environment Rules

- Create separate environments for each deployment target: `dev`, `staging`, `production`.
- Require at least one approval for production deployments.
- Use exclusive locks on production to prevent concurrent deployments.
- Configure branch policies to allow only the main branch to deploy to production.

---

## Multi-Stage Deployments

```yaml
stages:
  - stage: Build
    displayName: 'Build'
    jobs:
      - job: Build
        timeoutInMinutes: 15
        steps:
          - script: npm ci && npm run build
            displayName: 'Build'
          - publish: $(System.DefaultWorkingDirectory)/dist
            artifact: drop
            displayName: 'Publish artifact'

  - stage: DeployStaging
    displayName: 'Deploy to Staging'
    dependsOn: Build
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: Deploy
        environment: staging
        timeoutInMinutes: 10
        strategy:
          runOnce:
            deploy:
              steps:
                - download: current
                  artifact: drop
                - script: ./deploy.sh staging
                  displayName: 'Deploy to staging'
            postRouteTraffic:
              steps:
                - script: ./smoke-test.sh staging
                  displayName: 'Smoke test staging'

  - stage: DeployProduction
    displayName: 'Deploy to Production'
    dependsOn: DeployStaging
    condition: succeeded()
    jobs:
      - deployment: Deploy
        environment: production
        timeoutInMinutes: 10
        strategy:
          runOnce:
            deploy:
              steps:
                - download: current
                  artifact: drop
                - script: ./deploy.sh production
                  displayName: 'Deploy to production'
            postRouteTraffic:
              steps:
                - script: ./smoke-test.sh production
                  displayName: 'Smoke test production'
            on:
              failure:
                steps:
                  - script: ./rollback.sh production
                    displayName: 'Rollback production'
```

---

## Template Expressions and Conditions

### Compile-Time Expressions

Use `${{ }}` for expressions evaluated when the pipeline is compiled.

```yaml
parameters:
  - name: environment
    type: string
    values:
      - dev
      - staging
      - production

stages:
  - ${{ each env in parameters.environment }}:
    - stage: Deploy_${{ env }}
      displayName: 'Deploy to ${{ env }}'
```

### Runtime Expressions

Use `$[ ]` for expressions evaluated at runtime.

```yaml
variables:
  - name: deployTag
    value: $[format('{0}-{1}', variables['Build.BuildId'], variables['Build.SourceVersion'])]
```

### Conditions

```yaml
# Run only on main branch
condition: eq(variables['Build.SourceBranch'], 'refs/heads/main')

# Run on success of previous stage
condition: succeeded()

# Run even if previous stage failed (for cleanup)
condition: always()

# Run only if previous stage failed (for rollback)
condition: failed()

# Compound condition
condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'), ne(variables['Build.Reason'], 'PullRequest'))
```

### Expression Rules

- Use compile-time expressions (`${{ }}`) for structural decisions (which stages or jobs to include).
- Use runtime expressions (`$[ ]`) for values that depend on runtime state.
- Use `condition` on stages, jobs, and steps to control execution flow.
- Always include `succeeded()` in compound conditions unless you explicitly want to run on failure.

---

## Pipeline Caching

```yaml
variables:
  npm_config_cache: $(Pipeline.Workspace)/.npm

steps:
  - task: Cache@2
    displayName: 'Cache npm packages'
    inputs:
      key: 'npm | "$(Agent.OS)" | package-lock.json'
      restoreKeys: |
        npm | "$(Agent.OS)"
      path: $(npm_config_cache)

  - script: npm ci
    displayName: 'Install dependencies'
```

### Cache Patterns by Ecosystem

```yaml
# Python pip
- task: Cache@2
  inputs:
    key: 'pip | "$(Agent.OS)" | requirements.txt'
    restoreKeys: |
      pip | "$(Agent.OS)"
    path: $(PIP_CACHE_DIR)

# .NET NuGet
- task: Cache@2
  inputs:
    key: 'nuget | "$(Agent.OS)" | **/packages.lock.json'
    restoreKeys: |
      nuget | "$(Agent.OS)"
    path: $(NUGET_PACKAGES)

# Docker layers
- task: Cache@2
  inputs:
    key: 'docker | "$(Agent.OS)" | Dockerfile'
    path: $(Pipeline.Workspace)/docker-cache
    cacheHitVar: DOCKER_CACHE_RESTORED
```

### Caching Rules

- Always include `Agent.OS` in the cache key for OS-specific dependencies.
- Use the lock file hash as the primary cache key discriminator.
- Provide `restoreKeys` for partial cache hits when the exact key does not match.
- Cache the package manager cache directory, not `node_modules` or `venv` directly (these are OS- and architecture-specific).

---

## Artifact Feeds (Azure Artifacts)

### Publishing to Azure Artifacts

```yaml
# npm
- task: Npm@1
  displayName: 'Publish to Azure Artifacts'
  inputs:
    command: 'publish'
    publishRegistry: 'useFeed'
    publishFeed: 'MyProject/my-npm-feed'

# NuGet
- task: NuGetCommand@2
  displayName: 'Push NuGet package'
  inputs:
    command: 'push'
    packagesToPush: '$(Build.ArtifactStagingDirectory)/**/*.nupkg'
    publishVstsFeed: 'MyProject/my-nuget-feed'

# Universal Packages
- task: UniversalPackages@0
  displayName: 'Publish universal package'
  inputs:
    command: 'publish'
    publishDirectory: '$(Build.ArtifactStagingDirectory)'
    feedsToUsePublish: 'internal'
    vstsFeedPublish: 'MyProject/my-universal-feed'
    vstsFeedPackagePublish: 'my-package'
    versionOption: 'patch'
```

### Artifact Feed Rules

- Use project-scoped feeds, not organization-scoped, unless packages are shared across projects.
- Configure upstream sources to proxy public registries (npmjs, NuGet.org) through Azure Artifacts.
- Use feed views (Release, Prerelease) to manage package promotion.
- Set retention policies on feeds to manage storage costs.

---

## Release Gates and Approvals

### Gate Types

Configure these in the environment settings:

- **Manual approval**: A designated approver must approve before deployment proceeds.
- **Azure Monitor alerts**: Deployment proceeds only if specified alerts are not firing.
- **REST API check**: Call an external API to validate readiness.
- **Azure Function check**: Execute a function that returns pass or fail.
- **Business hours**: Allow deployments only during specified time windows.

### Gate Configuration Best Practices

- Use a minimum of two approvers for production deployments.
- Set a timeout on approval gates so stale deployments do not block the pipeline.
- Use Azure Monitor gates to check system health before deploying.
- Combine manual approval with automated health checks for defense in depth.

---

## Security

### Service Principal Authentication

```yaml
- task: AzureCLI@2
  displayName: 'Deploy with service principal'
  inputs:
    azureSubscription: 'azure-production'
    scriptType: 'bash'
    scriptLocation: 'inlineScript'
    inlineScript: |
      az webapp deployment source config-zip \
        --resource-group myapp-rg \
        --name myapp-production \
        --src $(Pipeline.Workspace)/drop/app.zip
```

### Managed Identity

When using self-hosted agents on Azure VMs, prefer managed identity over service principals.

```yaml
- task: AzureCLI@2
  displayName: 'Access Azure resources'
  inputs:
    azureSubscription: 'azure-managed-identity'
    scriptType: 'bash'
    scriptLocation: 'inlineScript'
    inlineScript: |
      az storage blob list --account-name myaccount --container-name data
```

### Security Rules

- Use workload identity federation for service connections when available.
- Never output secrets in pipeline logs. Use `issecret=true` to mask custom secrets.
- Use variable groups linked to Azure Key Vault for secret management.
- Restrict pipeline permissions: do not grant pipelines access to all repositories or service connections.
- Use branch control on environments to prevent unauthorized branches from deploying.
- Audit service connection usage regularly.

```yaml
# Masking a custom secret in logs
- script: |
    echo "##vso[task.setvariable variable=MY_SECRET;issecret=true]$(curl -s https://vault.example.com/secret)"
  displayName: 'Fetch and mask secret'
```

---

## Complete Pipeline Example

```yaml
trigger:
  branches:
    include:
      - main
  paths:
    exclude:
      - '*.md'
      - 'docs/**'

pr:
  branches:
    include:
      - main
  drafts: false

pool:
  vmImage: 'ubuntu-latest'

variables:
  - name: nodeVersion
    value: '20'
  - name: npm_config_cache
    value: $(Pipeline.Workspace)/.npm

stages:
  - stage: Validate
    displayName: 'Validate'
    jobs:
      - job: Lint
        displayName: 'Lint and Type Check'
        timeoutInMinutes: 10
        steps:
          - template: templates/steps/setup-node.yml
            parameters:
              nodeVersion: $(nodeVersion)
          - script: npm run lint
            displayName: 'Lint'
          - script: npm run typecheck
            displayName: 'Type check'

      - job: Test
        displayName: 'Unit Tests'
        timeoutInMinutes: 15
        steps:
          - template: templates/steps/setup-node.yml
            parameters:
              nodeVersion: $(nodeVersion)
          - script: npm test -- --coverage --ci
            displayName: 'Run tests'
          - task: PublishTestResults@2
            condition: succeededOrFailed()
            inputs:
              testResultsFormat: 'JUnit'
              testResultsFiles: '**/junit.xml'
          - task: PublishCodeCoverageResults@2
            condition: succeededOrFailed()
            inputs:
              summaryFileLocation: '**/coverage/cobertura-coverage.xml'

      - job: Security
        displayName: 'Security Scan'
        timeoutInMinutes: 10
        steps:
          - template: templates/steps/setup-node.yml
            parameters:
              nodeVersion: $(nodeVersion)
          - script: npm audit --audit-level=high
            displayName: 'Dependency audit'

  - stage: Build
    displayName: 'Build'
    dependsOn: Validate
    jobs:
      - job: Build
        displayName: 'Build Application'
        timeoutInMinutes: 10
        steps:
          - template: templates/steps/setup-node.yml
            parameters:
              nodeVersion: $(nodeVersion)
          - script: npm run build
            displayName: 'Build'
          - publish: $(System.DefaultWorkingDirectory)/dist
            artifact: drop

  - stage: DeployStaging
    displayName: 'Deploy to Staging'
    dependsOn: Build
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: Deploy
        environment: staging
        timeoutInMinutes: 10
        strategy:
          runOnce:
            deploy:
              steps:
                - download: current
                  artifact: drop
                - task: AzureWebApp@1
                  inputs:
                    azureSubscription: 'azure-staging'
                    appName: 'myapp-staging'
                    package: '$(Pipeline.Workspace)/drop'

  - stage: DeployProduction
    displayName: 'Deploy to Production'
    dependsOn: DeployStaging
    condition: succeeded()
    jobs:
      - deployment: Deploy
        environment: production
        timeoutInMinutes: 10
        strategy:
          runOnce:
            deploy:
              steps:
                - download: current
                  artifact: drop
                - task: AzureWebApp@1
                  inputs:
                    azureSubscription: 'azure-production'
                    appName: 'myapp-production'
                    package: '$(Pipeline.Workspace)/drop'
```
