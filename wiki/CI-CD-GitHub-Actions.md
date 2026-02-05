# GitHub Actions

> CI/CD workflows for GitHub-hosted projects.

## Included Workflows

The framework includes three GitHub Actions workflows:

| Workflow | File | Purpose |
|----------|------|---------|
| CI | `ci.yml` | Build, test, lint on every PR |
| Security | `security.yml` | Secret scanning, dependency audit |
| Quality Gate | `quality-gate.yml` | SonarCloud analysis |

## CI Workflow

**File:** `.github/workflows/ci.yml`

Runs on every push and pull request.

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  build-and-test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'

      - name: Restore
        run: dotnet restore

      - name: Build
        run: dotnet build --no-restore

      - name: Test
        run: dotnet test --no-build --verbosity normal

      - name: Lint
        run: dotnet format --verify-no-changes
```

### Multi-Stack CI

For projects with multiple stacks:

```yaml
jobs:
  dotnet:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'
      - run: dotnet build
      - run: dotnet test

  typescript:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run build
      - run: npm test
```

## Security Workflow

**File:** `.github/workflows/security.yml`

Runs on push to main and weekly schedule.

```yaml
name: Security

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday

jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  dependency-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: npm audit
        if: hashFiles('package-lock.json') != ''
        run: npm audit --audit-level=high

      - name: pip audit
        if: hashFiles('requirements.txt') != ''
        run: |
          pip install pip-audit
          pip-audit -r requirements.txt
```

## Quality Gate Workflow

**File:** `.github/workflows/quality-gate.yml`

Runs SonarCloud analysis.

```yaml
name: Quality Gate

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  sonarcloud:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'

      - name: Install SonarScanner
        run: dotnet tool install --global dotnet-sonarscanner

      - name: Build and Analyze
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        run: |
          dotnet sonarscanner begin \
            /k:"your-project-key" \
            /o:"your-org" \
            /d:sonar.token="${SONAR_TOKEN}" \
            /d:sonar.host.url="https://sonarcloud.io"
          dotnet build
          dotnet test --collect:"XPlat Code Coverage"
          dotnet sonarscanner end /d:sonar.token="${SONAR_TOKEN}"
```

## Required Secrets

Configure these secrets in your repository settings:

| Secret | Purpose |
|--------|---------|
| `SONAR_TOKEN` | SonarCloud authentication |
| `GITHUB_TOKEN` | Automatic (for gitleaks) |

## Branch Protection

Recommended branch protection rules for `main`:

1. **Require status checks:**
   - `build-and-test`
   - `secret-scan`
   - `sonarcloud`

2. **Require pull request reviews:** 1+

3. **Require conversation resolution**

4. **Do not allow bypassing**

## Customizing Workflows

### Adding Deployment

```yaml
deploy:
  needs: [build-and-test, security]
  if: github.ref == 'refs/heads/main'
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Deploy to Azure
      uses: azure/webapps-deploy@v2
      with:
        app-name: 'your-app-name'
        publish-profile: ${{ secrets.AZURE_PUBLISH_PROFILE }}
```

### Matrix Builds

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest]
    dotnet: ['6.0.x', '8.0.x']

runs-on: ${{ matrix.os }}
steps:
  - uses: actions/setup-dotnet@v4
    with:
      dotnet-version: ${{ matrix.dotnet }}
```

---
**See also:** [Azure Pipelines](CI-CD-Azure-Pipelines) | [Quality Gates](Standards-Quality-Gates)
