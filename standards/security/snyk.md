# Snyk Security Integration

> Security scanning configuration for dependencies, containers, and IaC.

---

## Overview

Snyk provides:
- **Open Source (SCA)**: Dependency vulnerability scanning
- **Container**: Docker image scanning
- **Infrastructure as Code**: Terraform, ARM, CloudFormation scanning
- **Code (SAST)**: Static application security testing

---

## Severity Thresholds

| Severity | CVSS Score | Action | Pipeline |
|----------|------------|--------|----------|
| Critical | 9.0 - 10.0 | Immediate fix required | ❌ Block |
| High | 7.0 - 8.9 | Fix before merge | ❌ Block |
| Medium | 4.0 - 6.9 | Fix within sprint | ⚠️ Warning |
| Low | 0.1 - 3.9 | Track in backlog | ℹ️ Info |

---

## CLI Usage

### Installation

```bash
# npm
npm install -g snyk

# Homebrew
brew install snyk
```

### Authentication

```bash
# Authenticate with Snyk
snyk auth

# Or use token (CI/CD)
export SNYK_TOKEN=your-token
```

### Commands

```bash
# Test for vulnerabilities
snyk test

# Test and block on severity
snyk test --severity-threshold=high

# Monitor (upload to dashboard)
snyk monitor

# Fix vulnerabilities
snyk fix

# Test container image
snyk container test image:tag

# Test IaC
snyk iac test infrastructure/
```

---

## Azure Pipeline Integration

### Full Security Pipeline

```yaml
# templates/jobs/snyk-security.yml
parameters:
  - name: severityThreshold
    type: string
    default: 'high'
  - name: failOnIssues
    type: boolean
    default: true
  - name: monitorProject
    type: boolean
    default: true

jobs:
  - job: SnykSecurity
    displayName: 'Snyk Security Scan'
    pool:
      vmImage: 'ubuntu-latest'
    steps:
      # =====================================================
      # DEPENDENCY SCANNING (.NET)
      # =====================================================
      - task: SnykSecurityScan@1
        displayName: 'Snyk: .NET Dependencies'
        inputs:
          serviceConnectionEndpoint: 'Snyk'
          testType: 'app'
          targetFile: '**/*.sln'
          severityThreshold: '${{ parameters.severityThreshold }}'
          failOnIssues: ${{ parameters.failOnIssues }}
          monitorWhen: ${{ parameters.monitorProject }}
          additionalArguments: '--all-projects --detection-depth=6'

      # =====================================================
      # DEPENDENCY SCANNING (npm)
      # =====================================================
      - task: SnykSecurityScan@1
        displayName: 'Snyk: npm Dependencies'
        inputs:
          serviceConnectionEndpoint: 'Snyk'
          testType: 'app'
          targetFile: 'src/frontend/package.json'
          severityThreshold: '${{ parameters.severityThreshold }}'
          failOnIssues: ${{ parameters.failOnIssues }}
          monitorWhen: ${{ parameters.monitorProject }}

      # =====================================================
      # CONTAINER SCANNING
      # =====================================================
      - task: SnykSecurityScan@1
        displayName: 'Snyk: Container Image'
        condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
        inputs:
          serviceConnectionEndpoint: 'Snyk'
          testType: 'container'
          dockerImageName: '$(containerRegistry)/$(imageName):$(Build.BuildId)'
          dockerfilePath: 'Dockerfile'
          severityThreshold: '${{ parameters.severityThreshold }}'
          failOnIssues: ${{ parameters.failOnIssues }}

      # =====================================================
      # IAC SCANNING (Terraform)
      # =====================================================
      - task: SnykSecurityScan@1
        displayName: 'Snyk: Infrastructure as Code'
        inputs:
          serviceConnectionEndpoint: 'Snyk'
          testType: 'code'
          codeScanType: 'iac'
          targetFile: 'infrastructure/'
          severityThreshold: 'medium'  # IaC often has more findings
          failOnIssues: ${{ parameters.failOnIssues }}
```

### Quick Scan (PR Validation)

```yaml
# templates/steps/snyk-pr.yml
steps:
  - script: |
      npm install -g snyk
      snyk auth $(SNYK_TOKEN)
      snyk test --severity-threshold=high --json > snyk-results.json || true
    displayName: 'Snyk Quick Scan'
    env:
      SNYK_TOKEN: $(SNYK_TOKEN)

  - script: |
      if grep -q '"ok": false' snyk-results.json; then
        echo "##vso[task.logissue type=error]High/Critical vulnerabilities found"
        exit 1
      fi
    displayName: 'Check Snyk Results'
```

---

## Policy Configuration

### .snyk File

```yaml
# .snyk
version: v1.25.0

# Ignore specific vulnerabilities
ignore:
  # Ignore with expiration
  SNYK-DOTNET-SYSTEMTEXTJSON-12345:
    - '*':
        reason: 'No direct exposure, updating in Q2'
        expires: 2024-06-01T00:00:00.000Z
        created: 2024-01-15T00:00:00.000Z

  # Ignore for specific path only
  SNYK-JS-LODASH-67890:
    - 'frontend > lodash':
        reason: 'Development dependency only'
        expires: 2024-12-31T00:00:00.000Z

# Patch vulnerabilities (when available)
patch:
  SNYK-JS-MINIMIST-559764:
    - lodash > minimist:
        patched: 2024-01-15T00:00:00.000Z

# Exclude paths from scanning
exclude:
  global:
    - tests/**
    - samples/**
    - '*.test.ts'
```

---

## GitHub Integration

### Snyk GitHub Action

```yaml
# .github/workflows/snyk.yml
name: Snyk Security

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Weekly Monday 6 AM

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Snyk to check for vulnerabilities
        uses: snyk/actions/dotnet@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high --sarif-file-output=snyk.sarif

      - name: Upload SARIF to GitHub
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: snyk.sarif
```

---

## Container Scanning Best Practices

### Dockerfile Security

```dockerfile
# ✅ Use specific, verified base images
FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine AS base

# ✅ Run as non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# ✅ Use multi-stage builds
FROM mcr.microsoft.com/dotnet/sdk:8.0-alpine AS build
WORKDIR /src
COPY . .
RUN dotnet publish -c Release -o /app

FROM base AS final
COPY --from=build /app .
ENTRYPOINT ["dotnet", "App.dll"]
```

### Scan Commands

```bash
# Test image
snyk container test myapp:latest

# Test with Dockerfile for recommendations
snyk container test myapp:latest --file=Dockerfile

# Monitor image
snyk container monitor myapp:latest

# Get base image upgrade advice
snyk container test myapp:latest --app-vulns
```

---

## Reporting and Monitoring

### Dashboard Configuration

1. **Import projects** from SCM (GitHub, Azure Repos)
2. **Set notification rules** for new vulnerabilities
3. **Configure integrations** (Slack, Jira, PagerDuty)
4. **Set organization policies** for blocking

### Metrics to Track

| Metric | Target |
|--------|--------|
| Critical/High open issues | 0 |
| Mean time to remediate (Critical) | < 7 days |
| Mean time to remediate (High) | < 30 days |
| Dependency freshness | < 90 days |
| Container base image age | < 30 days |

---

## Best Practices

1. **Shift Left**: Scan in IDE and PR, not just CI/CD
2. **Prioritize**: Fix critical/high first, track medium/low
3. **Automate**: Use Dependabot/Snyk auto-fix PRs
4. **Monitor**: Set up alerts for new vulnerabilities
5. **Baseline**: Track metrics over time
6. **Exceptions**: Document all ignored vulnerabilities with expiration
