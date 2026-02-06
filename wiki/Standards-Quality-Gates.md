# Quality Gates

> Thresholds that code must pass before merging.

## Overview

Quality gates are automated checks that verify code meets minimum standards. All code must pass these gates before merging to main.

## Quality Gate Thresholds

| Metric | Threshold | Tool |
|--------|-----------|------|
| Test Coverage | >= 80% | SonarQube |
| Code Duplications | <= 3% | SonarQube |
| Reliability Rating | A | SonarQube |
| Security Rating | A | SonarQube |
| Maintainability Rating | A | SonarQube |
| Security Hotspots Reviewed | 100% | SonarQube |
| Secrets Detected | 0 | gitleaks |
| Critical Vulnerabilities | 0 | npm audit / pip audit |
| High Vulnerabilities | 0 | npm audit / pip audit |

## SonarQube Ratings

| Rating | Meaning |
|--------|---------|
| **A** | Best - No issues or minimal technical debt |
| **B** | Good - Minor issues |
| **C** | Fair - Moderate issues |
| **D** | Poor - Significant issues |
| **E** | Worst - Critical issues |

## IDE Linting (Shift-Left Layer)

Quality enforcement starts in the IDE, before code is committed. The framework installs three config files that provide layered linting:

| Layer | Tool | Scope |
|-------|------|-------|
| **Baseline** | `.editorconfig` | Indentation, charset, line endings, trailing whitespace |
| **Stack Linters** | ESLint, Ruff, Roslyn analyzers, tflint | Language-specific rules, auto-fix on save |
| **SonarLint Connected Mode** | SonarLint extension | Same rules as SonarCloud/SonarQube, in real time |

This ensures issues are caught at authoring time rather than in CI. See [IDE Linting Setup](Standards-IDE-Linting) for full configuration details.

## Running Quality Gates

### Using /quality-gate Skill

```
/quality-gate
```

This runs all checks and reports pass/fail.

### Using verify-app Agent

```
Run the verify-app agent.
```

This includes quality checks plus build, tests, and security.

### Manual Commands

**.NET:**
```bash
dotnet build --no-restore
dotnet test --collect:"XPlat Code Coverage"
dotnet format --verify-no-changes
gitleaks detect --source . --no-git
dotnet list package --vulnerable
```

**TypeScript:**
```bash
npx tsc --noEmit
npm test -- --coverage
npx eslint .
gitleaks detect --source . --no-git
npm audit
```

**Python:**
```bash
pytest --cov --cov-report=term-missing
ruff check .
mypy .
gitleaks detect --source . --no-git
pip audit
```

## CI/CD Integration

### GitHub Actions

```yaml
jobs:
  quality-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run tests with coverage
        run: dotnet test --collect:"XPlat Code Coverage"

      - name: SonarCloud Scan
        uses: SonarSource/sonarcloud-github-action@master
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

      - name: Check Quality Gate
        uses: sonarsource/sonarqube-quality-gate-action@master
        timeout-minutes: 5
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

### Azure Pipelines

```yaml
- task: SonarCloudPrepare@1
  inputs:
    SonarCloud: 'SonarCloud'
    organization: 'your-org'
    scannerMode: 'MSBuild'
    projectKey: 'your-project'

- task: DotNetCoreCLI@2
  inputs:
    command: 'test'
    arguments: '--collect:"XPlat Code Coverage"'

- task: SonarCloudAnalyze@1

- task: SonarCloudPublish@1
  inputs:
    pollingTimeoutSec: '300'
```

## Coverage Requirements by Layer

| Layer | Minimum | Target |
|-------|---------|--------|
| Services | 80% | 90% |
| Providers | 80% | 85% |
| Controllers | 70% | 80% |
| Models | 50% | 60% |
| Utilities | 90% | 95% |

## Handling Quality Gate Failures

### Coverage Below Threshold

1. Identify uncovered code: `dotnet test --collect:"XPlat Code Coverage"`
2. Generate tests with `/test` skill
3. Focus on critical paths first

### Duplications Above Threshold

1. Identify duplicated code in SonarQube
2. Extract to shared utilities
3. Use `/refactor` skill for safe extraction

### Security Issues

1. Review findings in SonarQube
2. Prioritize by severity (Critical > High > Medium)
3. Use `/security-audit` for detailed analysis

### Dependency Vulnerabilities

1. Run `npm audit` or `pip audit`
2. Update vulnerable packages
3. If update not possible, document risk and mitigation

## Exemptions

In rare cases, you may need to exclude code from quality gates:

### SonarQube Exclusions

```xml
<!-- sonar-project.properties -->
sonar.exclusions=**/migrations/**,**/generated/**
sonar.coverage.exclusions=**/tests/**,**/Program.cs
```

### gitleaks Allowlist

```toml
# .gitleaks.toml
[allowlist]
paths = [
  '''tests/fixtures/''',
  '''docs/examples/'''
]
```

**Warning:** Exemptions should be rare and documented. Don't use them to hide technical debt.

---
**See also:** [Standards Overview](Standards-Overview) | [Security Skills](Skills-Security)
