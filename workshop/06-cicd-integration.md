# Module 6: CI/CD Integration

## Overview

Enable automated CI/CD pipelines on GitHub Actions and/or Azure Pipelines.

---

## GitHub Actions

### Available Workflows

| Workflow | File | Triggers | Purpose |
|----------|------|----------|---------|
| CI | `.github/workflows/ci.yml` | Push, PR | Build, test, lint |
| Security | `.github/workflows/security.yml` | Push, PR, weekly | gitleaks, Snyk, CodeQL |
| Quality Gate | `.github/workflows/quality-gate.yml` | PR | SonarQube analysis |

### Setup Steps

#### 1. Enable Workflows

Workflows are already in `.github/workflows/`. Push to GitHub and they'll run automatically.

#### 2. Configure Secrets

Go to Settings → Secrets and variables → Actions:

| Secret | Required | Purpose |
|--------|----------|---------|
| `SONAR_TOKEN` | For quality gate | SonarQube Cloud token |
| `SNYK_TOKEN` | For dependency scan | Snyk API token |

#### 3. Enable GitHub Features

Go to Settings → Code security and analysis:

- [x] **Dependabot alerts**: Enabled
- [x] **Dependabot security updates**: Enabled
- [x] **Secret scanning**: Enabled
- [x] **Push protection**: Enabled
- [x] **CodeQL analysis**: Enabled (via security workflow)

#### 4. Branch Protection

Go to Settings → Branches → Add rule for `main`:

- [x] Require a pull request before merging
- [x] Require status checks to pass (select: `build`, `security-scan`, `quality-gate`)
- [x] Require branches to be up to date

---

## Azure Pipelines

### Available Pipelines

| Pipeline | File | Triggers | Purpose |
|----------|------|----------|---------|
| CI | `pipelines/ci.yml` | Push, PR | Build, test, lint |
| Security | `pipelines/security.yml` | Push, PR, weekly | gitleaks, Snyk, OWASP |
| Quality Gate | `pipelines/quality-gate.yml` | PR | SonarQube analysis |

### Reusable Templates

Located in `pipelines/templates/`:

| Template | Purpose |
|----------|---------|
| `dotnet-build.yml` | Build + test .NET projects |
| `typescript-build.yml` | Build + test TypeScript projects |
| `python-build.yml` | Build + test Python projects |
| `terraform-validate.yml` | Validate Terraform configs |
| `security-scan.yml` | gitleaks + dependency scanning |
| `sonarqube-analysis.yml` | SonarQube/SonarCloud analysis |

### Setup Steps

#### 1. Import Pipelines

In Azure DevOps → Pipelines → New Pipeline:
- Select your repo
- Choose "Existing Azure Pipelines YAML file"
- Select `pipelines/ci.yml`
- Repeat for `security.yml` and `quality-gate.yml`

#### 2. Create Variable Groups

Go to Pipelines → Library → New variable group:

**Group: `common-variables`**

| Variable | Value | Secret? |
|----------|-------|---------|
| `SONAR_TOKEN` | Your SonarQube token | Yes |
| `SNYK_TOKEN` | Your Snyk token | Yes |

#### 3. Create Service Connections

Go to Project Settings → Service connections:

- **SonarCloud**: Type "SonarCloud", add your token
- **SonarQube**: Type "SonarQube", add your server URL and token

#### 4. Branch Policies

Go to Repos → Branches → `main` → Branch policies:

- [x] Require minimum number of reviewers
- [x] Build validation: Add CI pipeline
- [x] Build validation: Add quality-gate pipeline

---

## Verifying CI/CD

### GitHub Actions

Push a commit and check the Actions tab. You should see:

```
✓ CI          Build, test, and lint passed
✓ Security    No secrets or vulnerabilities found
✓ Quality     Quality gate passed
```

### Azure Pipelines

Create a PR and check the Pipelines tab. You should see:

```
✓ CI          Build, test, and lint passed
✓ Security    No secrets or vulnerabilities found
✓ Quality     Quality gate passed
```

## Next

→ [Module 7: Customization](07-customization.md)
