# Module 5: Quality Gates

## Overview

Set up automated quality checks: SonarQube for code quality, Snyk for dependency scanning, and gitleaks for secret detection.

---

## The Quality Stack (All Free)

| Layer | Tool | What It Does | Cost |
|-------|------|-------------|------|
| IDE | SonarLint | Real-time code quality in your editor | Free |
| Pre-commit | gitleaks | Scan staged files for secrets | Free |
| Pre-push | `/quality-gate` | Coverage, linting, dependency audit | Free |
| CI | SonarQube Cloud | Quality gate analysis | Free (open source) |
| CI | Snyk | Dependency vulnerability scanning | Free (400 tests/month) |
| CI | CodeQL | Static application security testing | Free (public repos) |
| Platform | GitHub Secret Scanning | Block secret pushes | Free (public repos) |
| Platform | Dependabot | Automated dependency updates | Free |

---

## Setup: SonarQube Cloud

### 1. Create Account

Go to [sonarcloud.io](https://sonarcloud.io) and sign in with GitHub.

### 2. Import Project

- Click "+" → "Analyze new project"
- Select your repository
- Note your **organization key** and **project key**

### 3. Generate Token

- Go to My Account → Security → Generate Tokens
- Create a token named `CI`
- Save as `SONAR_TOKEN` in your CI secrets

### 4. Add Configuration

Create `sonar-project.properties` in your project root:

```properties
sonar.projectKey=your-project-key
sonar.organization=your-org

sonar.sources=src
sonar.tests=tests
sonar.exclusions=**/node_modules/**,**/bin/**,**/obj/**

sonar.qualitygate.wait=true
```

---

## Setup: SonarLint (IDE)

### VS Code

1. Install the **SonarLint** extension
2. Connect to SonarQube Cloud:

```json
// .vscode/settings.json
{
  "sonarlint.connectedMode.connections.sonarcloud": [
    {
      "organizationKey": "your-org",
      "connectionId": "my-sonarcloud"
    }
  ],
  "sonarlint.connectedMode.project": {
    "connectionId": "my-sonarcloud",
    "projectKey": "your-project-key"
  }
}
```

Now your IDE shows the same rules SonarQube will check in CI.

---

## Setup: Snyk (Free Tier)

### 1. Create Account

Go to [snyk.io](https://snyk.io) and sign in with GitHub.

### 2. Generate Token

- Go to Account Settings → API Token
- Save as `SNYK_TOKEN` in your CI secrets

### Free Tier Limits

- **Public repos**: Unlimited tests
- **Private repos**: 400 open source tests per month
- **Alternative**: OWASP Dependency-Check (fully free, no limits)

---

## Setup: gitleaks (Secret Scanning)

### Install

```bash
# macOS
brew install gitleaks

# Linux
curl -sSfL https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.18.0_linux_x64.tar.gz | tar xz

# Or use Docker
docker run --rm -v $(pwd):/repo zricethezav/gitleaks:latest detect --source /repo
```

### Usage

The `/commit` command runs gitleaks automatically. You can also run it manually:

```bash
gitleaks detect --source . --verbose
```

---

## Exercise: Run Quality Gate

```
/quality-gate
```

This runs all quality checks and reports:

```markdown
## Quality Gate Report

**Verdict:** PASS | FAIL

### Metrics
| Metric | Threshold | Actual | Status |
|--------|-----------|--------|--------|
| Coverage | >= 80% | 85% | PASS |
| Duplication | <= 3% | 1% | PASS |
| Linter issues | 0 | 0 | PASS |
| Vulnerabilities | 0 | 0 | PASS |
```

---

## Quality Gate Thresholds

Defined in `standards/quality-gates.md`:

| Metric | New Code Threshold |
|--------|-------------------|
| Coverage | >= 80% |
| Duplication | <= 3% |
| Maintainability rating | A |
| Reliability rating | A |
| Security rating | A |
| Security hotspots reviewed | 100% |

## Next

→ [Module 6: CI/CD Integration](06-cicd-integration.md)
