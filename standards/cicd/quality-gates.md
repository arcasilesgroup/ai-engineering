# Quality Gates Standards

> Thresholds and configurations for SonarQube, Snyk, and other quality tools.

---

## SonarQube / SonarCloud

### Default Quality Gate ("Sonar Way")

| Metric | Operator | Threshold | Scope |
|--------|----------|-----------|-------|
| Coverage | ≥ | 80% | New Code |
| Duplicated Lines | ≤ | 3% | New Code |
| Maintainability Rating | ≤ | A | New Code |
| Reliability Rating | ≤ | A | New Code |
| Security Rating | ≤ | A | New Code |
| Security Hotspots Reviewed | = | 100% | New Code |
| New Issues | = | 0 | New Code |

### Rating Scale

| Rating | Technical Debt Ratio |
|--------|---------------------|
| A | ≤ 5% |
| B | 6% - 10% |
| C | 11% - 20% |
| D | 21% - 50% |
| E | > 50% |

### Azure Pipeline Integration

```yaml
# templates/jobs/sonar-analysis.yml
parameters:
  - name: sonarProjectKey
    type: string
  - name: sonarOrganization
    type: string

jobs:
  - job: SonarAnalysis
    displayName: 'SonarCloud Analysis'
    pool:
      vmImage: 'ubuntu-latest'
    steps:
      - task: SonarCloudPrepare@2
        displayName: 'Prepare SonarCloud'
        inputs:
          SonarCloud: 'SonarCloud-ServiceConnection'
          organization: '${{ parameters.sonarOrganization }}'
          scannerMode: 'MSBuild'
          projectKey: '${{ parameters.sonarProjectKey }}'
          projectName: '${{ parameters.sonarProjectKey }}'
          extraProperties: |
            sonar.cs.opencover.reportsPaths=$(Agent.TempDirectory)/**/coverage.opencover.xml
            sonar.cs.vstest.reportsPaths=$(Agent.TempDirectory)/**/*.trx
            sonar.coverage.exclusions=**/*Tests*/**,**/Program.cs

      - script: dotnet build --configuration Release
        displayName: 'Build'

      - script: |
          dotnet test --configuration Release \
            --collect:"XPlat Code Coverage" \
            --results-directory $(Agent.TempDirectory) \
            -- DataCollectionRunSettings.DataCollectors.DataCollector.Configuration.Format=opencover
        displayName: 'Run Tests with Coverage'

      - task: SonarCloudAnalyze@2
        displayName: 'Run SonarCloud Analysis'

      - task: SonarCloudPublish@2
        displayName: 'Publish Quality Gate Result'
        inputs:
          pollingTimeoutSec: '300'
```

### sonar-project.properties

```properties
# Project identification
sonar.projectKey=organization_project-name
sonar.organization=organization

# Source configuration
sonar.sources=src
sonar.tests=tests
sonar.sourceEncoding=UTF-8

# Language-specific settings
sonar.cs.opencover.reportsPaths=**/coverage.opencover.xml
sonar.cs.vstest.reportsPaths=**/*.trx

# Exclusions
sonar.exclusions=**/Migrations/**,**/obj/**,**/bin/**
sonar.coverage.exclusions=**/*Tests*/**,**/Program.cs,**/Startup.cs
sonar.cpd.exclusions=**/Migrations/**

# Quality settings
sonar.qualitygate.wait=true
```

---

## Snyk Security Scanning

### Severity Thresholds

| Severity | Block Pipeline | Action Required |
|----------|----------------|-----------------|
| Critical | ✅ Yes | Immediate fix |
| High | ✅ Yes | Fix before merge |
| Medium | ⚠️ Warning | Fix within sprint |
| Low | ℹ️ Info | Track in backlog |

### Azure Pipeline Integration

```yaml
# templates/steps/snyk-scan.yml
parameters:
  - name: severityThreshold
    type: string
    default: 'high'
    values: ['low', 'medium', 'high', 'critical']
  - name: failOnIssues
    type: boolean
    default: true

steps:
  # .NET dependency scan
  - task: SnykSecurityScan@1
    displayName: 'Snyk Security Scan (.NET)'
    inputs:
      serviceConnectionEndpoint: 'Snyk-ServiceConnection'
      testType: 'app'
      targetFile: '**/*.sln'
      severityThreshold: '${{ parameters.severityThreshold }}'
      failOnIssues: ${{ parameters.failOnIssues }}
      monitorWhen: 'always'
      additionalArguments: '--all-projects'

  # Container scan
  - task: SnykSecurityScan@1
    displayName: 'Snyk Container Scan'
    inputs:
      serviceConnectionEndpoint: 'Snyk-ServiceConnection'
      testType: 'container'
      dockerImageName: '$(containerRegistry)/$(imageName):$(Build.BuildId)'
      dockerfilePath: 'Dockerfile'
      severityThreshold: '${{ parameters.severityThreshold }}'
      failOnIssues: ${{ parameters.failOnIssues }}

  # IaC scan (Terraform)
  - task: SnykSecurityScan@1
    displayName: 'Snyk IaC Scan'
    inputs:
      serviceConnectionEndpoint: 'Snyk-ServiceConnection'
      testType: 'code'
      codeScanType: 'iac'
      targetFile: 'infrastructure/'
      severityThreshold: '${{ parameters.severityThreshold }}'
      failOnIssues: ${{ parameters.failOnIssues }}
```

### .snyk Policy File

```yaml
# .snyk
version: v1.25.0

# Ignore specific vulnerabilities
ignore:
  SNYK-DOTNET-ABORTERRORFCN-1234567:
    - '*':
        reason: 'No direct usage, will fix in next sprint'
        expires: 2024-03-01T00:00:00.000Z
        created: 2024-01-15T00:00:00.000Z

# Patch vulnerabilities
patch:
  SNYK-DOTNET-DEPENDENCY-1234567:
    - dependency > sub-dependency:
        patched: 2024-01-15T00:00:00.000Z

# Exclude paths from scanning
exclude:
  global:
    - tests/**
    - samples/**
```

---

## Code Coverage

### Minimum Thresholds

| Metric | Threshold | Enforcement |
|--------|-----------|-------------|
| Line Coverage | ≥ 80% | Quality Gate |
| Branch Coverage | ≥ 70% | Warning |
| New Code Coverage | ≥ 80% | Quality Gate |

### Azure Pipeline Coverage Collection

```yaml
# .NET Coverage with Coverlet
- script: |
    dotnet test \
      --configuration Release \
      --collect:"XPlat Code Coverage" \
      --results-directory $(Agent.TempDirectory)/coverage \
      --logger "trx;LogFileName=test-results.trx" \
      -- DataCollectionRunSettings.DataCollectors.DataCollector.Configuration.Format=cobertura,opencover
  displayName: 'Run Tests with Coverage'

- task: PublishCodeCoverageResults@2
  displayName: 'Publish Coverage Results'
  inputs:
    summaryFileLocation: '$(Agent.TempDirectory)/coverage/**/coverage.cobertura.xml'
    failIfCoverageEmpty: true

# TypeScript/JavaScript Coverage with Jest
- script: npm run test:coverage
  displayName: 'Run Tests with Coverage'

- task: PublishCodeCoverageResults@2
  inputs:
    summaryFileLocation: 'coverage/cobertura-coverage.xml'
```

---

## Static Analysis

### .NET Analyzers

```xml
<!-- Directory.Build.props -->
<Project>
  <PropertyGroup>
    <AnalysisLevel>latest-recommended</AnalysisLevel>
    <AnalysisMode>Recommended</AnalysisMode>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <Nullable>enable</Nullable>
  </PropertyGroup>
  
  <ItemGroup>
    <PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" Version="8.*">
      <PrivateAssets>all</PrivateAssets>
      <IncludeAssets>runtime; build; native; contentfiles; analyzers</IncludeAssets>
    </PackageReference>
  </ItemGroup>
</Project>
```

### ESLint in Pipeline

```yaml
- script: |
    npm ci
    npm run lint -- --format stylish --output-file eslint-report.txt
    npm run lint -- --format json --output-file eslint-report.json
  displayName: 'Run ESLint'
  continueOnError: true

- task: PublishPipelineArtifact@1
  inputs:
    targetPath: 'eslint-report.json'
    artifact: 'eslint-results'
```

---

## Combined Quality Pipeline

```yaml
# templates/stages/quality.yml
parameters:
  - name: sonarProjectKey
    type: string
  - name: snykSeverity
    type: string
    default: 'high'

stages:
  - stage: Quality
    displayName: 'Code Quality & Security'
    jobs:
      # Parallel quality jobs
      - job: Lint
        displayName: 'Linting'
        steps:
          - script: dotnet format --verify-no-changes --verbosity diagnostic
            displayName: '.NET Format Check'
          - script: npm run lint
            displayName: 'ESLint Check'

      - job: Sonar
        displayName: 'SonarCloud Analysis'
        steps:
          - template: ../steps/sonar-analysis.yml
            parameters:
              projectKey: ${{ parameters.sonarProjectKey }}

      - job: Security
        displayName: 'Security Scanning'
        steps:
          - template: ../steps/snyk-scan.yml
            parameters:
              severityThreshold: ${{ parameters.snykSeverity }}

      - job: Dependencies
        displayName: 'Dependency Check'
        steps:
          - script: dotnet list package --vulnerable --include-transitive
            displayName: 'Check Vulnerable NuGet Packages'
          - script: npm audit --audit-level=high
            displayName: 'Check Vulnerable npm Packages'
```

---

## Quality Gate Decision Matrix

| Check | Pass Criteria | Action on Fail |
|-------|---------------|----------------|
| Build | Compiles without errors | ❌ Block |
| Unit Tests | 100% pass | ❌ Block |
| Coverage | ≥ 80% new code | ❌ Block |
| SonarQube | Quality Gate passed | ❌ Block |
| Snyk (High/Critical) | 0 issues | ❌ Block |
| Snyk (Medium) | 0 new issues | ⚠️ Warning |
| Lint | 0 errors | ❌ Block |
| Lint (warnings) | Tracked | ℹ️ Info |
