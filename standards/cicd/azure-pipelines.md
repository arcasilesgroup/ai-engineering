# Azure Pipelines Standards

> Conventions for Azure DevOps YAML pipelines, templates, and CI/CD workflows.

---

## Pipeline Structure

### Standard Pipeline Organization

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include: [main, develop]
  paths:
    exclude: ['docs/**', '*.md', '.ai/**']

pr:
  branches:
    include: [main, develop]
  paths:
    exclude: ['docs/**', '*.md']

resources:
  repositories:
    - repository: templates
      type: git
      name: ProjectName/pipeline-templates
      ref: refs/heads/main

variables:
  - group: 'build-variables'
  - template: variables/common.yml
  - name: buildConfiguration
    value: 'Release'

stages:
  - stage: Build
    displayName: 'Build & Test'
    jobs:
      - template: jobs/build-dotnet.yml@templates

  - stage: Quality
    displayName: 'Code Quality'
    dependsOn: Build
    jobs:
      - template: jobs/quality-gates.yml@templates

  - stage: Deploy
    displayName: 'Deploy to Dev'
    dependsOn: Quality
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - template: jobs/deploy.yml@templates
```

---

## Template Patterns

### Extends Template (Pipeline Security)

```yaml
# templates/pipeline-template.yml
parameters:
  - name: buildConfiguration
    type: string
    default: 'Release'
    values: ['Debug', 'Release']
  - name: runTests
    type: boolean
    default: true
  - name: publishArtifacts
    type: boolean
    default: true

stages:
  - stage: Build
    jobs:
      - job: BuildJob
        pool:
          vmImage: 'ubuntu-latest'
        steps:
          - checkout: self
            fetchDepth: 0

          - template: steps/restore.yml
            parameters:
              buildConfiguration: ${{ parameters.buildConfiguration }}

          - template: steps/build.yml
            parameters:
              buildConfiguration: ${{ parameters.buildConfiguration }}

          - ${{ if parameters.runTests }}:
            - template: steps/test.yml

          - ${{ if parameters.publishArtifacts }}:
            - template: steps/publish.yml
```

### Include Template (Reusable Steps)

```yaml
# templates/steps/build-dotnet.yml
parameters:
  - name: buildConfiguration
    type: string
    default: 'Release'
  - name: projects
    type: string
    default: '**/*.csproj'

steps:
  - task: UseDotNet@2
    displayName: 'Install .NET SDK'
    inputs:
      version: '8.x'
      includePreviewVersions: false

  - script: dotnet restore
    displayName: 'Restore NuGet packages'

  - script: |
      dotnet build ${{ parameters.projects }} \
        --configuration ${{ parameters.buildConfiguration }} \
        --no-restore \
        -p:TreatWarningsAsErrors=true
    displayName: 'Build solution'
```

---

## Variable Management

### Variable Groups

```yaml
# Reference variable groups from Library
variables:
  - group: 'common-variables'        # Shared across pipelines
  - group: 'env-$(environment)'      # Environment-specific
  - group: 'secrets-$(environment)'  # Key Vault linked
```

### Variable Templates

```yaml
# variables/common.yml
variables:
  solution: '**/*.sln'
  buildPlatform: 'Any CPU'
  buildConfiguration: 'Release'
  DOTNET_CLI_TELEMETRY_OPTOUT: true
  DOTNET_SKIP_FIRST_TIME_EXPERIENCE: true
  NUGET_PACKAGES: $(Pipeline.Workspace)/.nuget/packages

# variables/environments/dev.yml
variables:
  environment: 'dev'
  resourceGroup: 'rg-project-dev-weu'
  appServiceName: 'app-project-dev-weu'
```

### Runtime vs Compile-time Variables

```yaml
# Compile-time (template expressions) - resolved before pipeline runs
${{ variables.buildConfiguration }}
${{ parameters.environment }}

# Runtime (macro syntax) - resolved during pipeline run
$(Build.BuildId)
$(System.AccessToken)

# Runtime (template expression) - for conditions
$[variables.isMain]
```

---

## Stage Patterns

### Multi-Environment Deployment

```yaml
stages:
  - stage: Build
    jobs:
      - job: Build
        steps:
          - template: steps/build.yml

  - stage: DeployDev
    displayName: 'Deploy to Dev'
    dependsOn: Build
    variables:
      - template: variables/environments/dev.yml
    jobs:
      - deployment: Deploy
        environment: 'project-dev'
        strategy:
          runOnce:
            deploy:
              steps:
                - template: steps/deploy.yml

  - stage: DeployStaging
    displayName: 'Deploy to Staging'
    dependsOn: DeployDev
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    variables:
      - template: variables/environments/staging.yml
    jobs:
      - deployment: Deploy
        environment: 'project-staging'
        strategy:
          runOnce:
            deploy:
              steps:
                - template: steps/deploy.yml

  - stage: DeployProd
    displayName: 'Deploy to Production'
    dependsOn: DeployStaging
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    variables:
      - template: variables/environments/prod.yml
    jobs:
      - deployment: Deploy
        environment: 'project-prod'  # Requires approval
        strategy:
          runOnce:
            deploy:
              steps:
                - template: steps/deploy.yml
```

---

## Job Patterns

### Matrix Strategy

```yaml
jobs:
  - job: Test
    strategy:
      matrix:
        Linux:
          vmImage: 'ubuntu-latest'
        Windows:
          vmImage: 'windows-latest'
        macOS:
          vmImage: 'macos-latest'
    pool:
      vmImage: $(vmImage)
    steps:
      - script: dotnet test
```

### Parallel Jobs

```yaml
jobs:
  - job: UnitTests
    pool:
      vmImage: 'ubuntu-latest'
    steps:
      - script: dotnet test --filter Category=Unit

  - job: IntegrationTests
    pool:
      vmImage: 'ubuntu-latest'
    steps:
      - script: dotnet test --filter Category=Integration

  - job: E2ETests
    pool:
      vmImage: 'ubuntu-latest'
    steps:
      - script: npm run test:e2e
```

---

## Best Practices

### Caching

```yaml
steps:
  # NuGet cache
  - task: Cache@2
    displayName: 'Cache NuGet packages'
    inputs:
      key: 'nuget | "$(Agent.OS)" | **/packages.lock.json'
      restoreKeys: |
        nuget | "$(Agent.OS)"
      path: $(NUGET_PACKAGES)

  # npm cache
  - task: Cache@2
    displayName: 'Cache npm packages'
    inputs:
      key: 'npm | "$(Agent.OS)" | package-lock.json'
      restoreKeys: |
        npm | "$(Agent.OS)"
      path: $(npm_config_cache)
```

### Artifact Publishing

```yaml
steps:
  - task: PublishBuildArtifacts@1
    displayName: 'Publish Build Artifacts'
    inputs:
      PathtoPublish: '$(Build.ArtifactStagingDirectory)'
      ArtifactName: 'drop'
      publishLocation: 'Container'

  # Or use Pipeline Artifacts (faster)
  - task: PublishPipelineArtifact@1
    displayName: 'Publish Pipeline Artifacts'
    inputs:
      targetPath: '$(Build.ArtifactStagingDirectory)'
      artifact: 'drop'
```

### Conditional Execution

```yaml
steps:
  # Run only on main branch
  - script: echo "Main branch only"
    condition: eq(variables['Build.SourceBranch'], 'refs/heads/main')

  # Run only on PR
  - script: echo "PR only"
    condition: eq(variables['Build.Reason'], 'PullRequest')

  # Run even if previous step failed
  - script: echo "Always run"
    condition: always()

  # Run only if previous steps succeeded
  - script: echo "On success"
    condition: succeeded()
```

---

## Security

### Secure Variables

```yaml
variables:
  # Never log secret values
  - name: mySecret
    value: $(SECRET_FROM_LIBRARY)

steps:
  # Use secrets securely
  - script: |
      echo "Using secret..."
      # Never: echo $(mySecret)
    env:
      MY_SECRET: $(mySecret)  # Pass as environment variable
```

### Service Connections

```yaml
# Use service connections for Azure resources
- task: AzureCLI@2
  inputs:
    azureSubscription: 'ServiceConnection-Prod'
    scriptType: 'bash'
    scriptLocation: 'inlineScript'
    inlineScript: |
      az webapp deploy --name $(appName) --resource-group $(resourceGroup)
```

---

## File Organization

```
pipelines/
├── azure-pipelines.yml           # Main pipeline
├── azure-pipelines-pr.yml        # PR validation
├── templates/
│   ├── stages/
│   │   ├── build.yml
│   │   ├── test.yml
│   │   └── deploy.yml
│   ├── jobs/
│   │   ├── build-dotnet.yml
│   │   ├── build-node.yml
│   │   └── quality-gates.yml
│   └── steps/
│       ├── restore.yml
│       ├── build.yml
│       ├── test.yml
│       └── publish.yml
└── variables/
    ├── common.yml
    └── environments/
        ├── dev.yml
        ├── staging.yml
        └── prod.yml
```
