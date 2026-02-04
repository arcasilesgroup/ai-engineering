# Dependabot Configuration Standards

> Automated dependency updates configuration for GitHub repositories.

---

## Configuration File

Location: `.github/dependabot.yml`

### Complete Example

```yaml
# .github/dependabot.yml
version: 2

registries:
  # Private NuGet feed
  nuget-private:
    type: nuget-feed
    url: https://pkgs.dev.azure.com/org/project/_packaging/feed/nuget/v3/index.json
    username: azure
    password: ${{ secrets.AZURE_DEVOPS_PAT }}

  # Private npm registry
  npm-private:
    type: npm-registry
    url: https://npm.pkg.github.com
    token: ${{ secrets.GH_PACKAGES_TOKEN }}

updates:
  # ========== .NET NuGet ==========
  - package-ecosystem: "nuget"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "06:00"
      timezone: "Europe/Madrid"
    registries:
      - nuget-private
    groups:
      microsoft:
        patterns:
          - "Microsoft.*"
          - "System.*"
        exclude-patterns:
          - "Microsoft.Extensions.Logging"
      azure:
        patterns:
          - "Azure.*"
      testing:
        patterns:
          - "NUnit*"
          - "Moq*"
          - "FluentAssertions*"
          - "coverlet*"
    ignore:
      # Ignore major version updates for specific packages
      - dependency-name: "Newtonsoft.Json"
        update-types: ["version-update:semver-major"]
    open-pull-requests-limit: 10
    reviewers:
      - "team-backend"
    labels:
      - "dependencies"
      - "dotnet"
    commit-message:
      prefix: "chore(deps)"
      include: "scope"

  # ========== npm/Node.js ==========
  - package-ecosystem: "npm"
    directory: "/src/frontend"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "06:00"
    registries:
      - npm-private
    groups:
      react:
        patterns:
          - "react*"
          - "@types/react*"
      typescript:
        patterns:
          - "typescript"
          - "@typescript-eslint/*"
      testing:
        patterns:
          - "jest*"
          - "@testing-library/*"
          - "vitest*"
      linting:
        patterns:
          - "eslint*"
          - "prettier*"
    versioning-strategy: increase
    open-pull-requests-limit: 10
    reviewers:
      - "team-frontend"
    labels:
      - "dependencies"
      - "npm"
    commit-message:
      prefix: "chore(deps)"

  # ========== Python ==========
  - package-ecosystem: "pip"
    directory: "/scripts"
    schedule:
      interval: "weekly"
    groups:
      dev-tools:
        patterns:
          - "ruff"
          - "black"
          - "mypy"
          - "pytest*"
    labels:
      - "dependencies"
      - "python"
    commit-message:
      prefix: "chore(deps)"

  # ========== Terraform ==========
  - package-ecosystem: "terraform"
    directory: "/infrastructure"
    schedule:
      interval: "weekly"
    groups:
      azure:
        patterns:
          - "azurerm"
          - "azuread"
    labels:
      - "dependencies"
      - "terraform"
    commit-message:
      prefix: "chore(deps)"

  # ========== Docker ==========
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "monthly"
    labels:
      - "dependencies"
      - "docker"
    commit-message:
      prefix: "chore(deps)"

  # ========== GitHub Actions ==========
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      actions:
        patterns:
          - "*"
    labels:
      - "dependencies"
      - "github-actions"
    commit-message:
      prefix: "chore(deps)"
```

---

## Configuration Options

### Schedule Options

| Option | Values | Description |
|--------|--------|-------------|
| `interval` | `daily`, `weekly`, `monthly` | Update frequency |
| `day` | `monday` - `sunday` | Day for weekly updates |
| `time` | `HH:MM` (24h) | Time to check (UTC default) |
| `timezone` | IANA timezone | e.g., `Europe/Madrid` |

### Versioning Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `increase` | Increase version requirement | npm, default for most |
| `increase-if-necessary` | Only increase if needed | Conservative updates |
| `lockfile-only` | Only update lockfile | Lock-based workflows |
| `widen` | Widen version range | Libraries |
| `auto` | Strategy based on manifest | Auto-detect |

### Grouping Patterns

```yaml
groups:
  # Group by pattern
  microsoft:
    patterns:
      - "Microsoft.*"
      - "System.*"
    exclude-patterns:
      - "Microsoft.EntityFrameworkCore"
  
  # Group by update type
  minor-updates:
    update-types:
      - "minor"
      - "patch"
```

---

## Package Ecosystem Reference

| Ecosystem | Files Detected |
|-----------|----------------|
| `nuget` | `*.csproj`, `packages.config`, `*.nuspec` |
| `npm` | `package.json`, `package-lock.json` |
| `pip` | `requirements.txt`, `Pipfile`, `pyproject.toml` |
| `terraform` | `*.tf` |
| `docker` | `Dockerfile`, `docker-compose.yml` |
| `github-actions` | `.github/workflows/*.yml` |
| `gradle` | `build.gradle`, `build.gradle.kts` |
| `maven` | `pom.xml` |
| `cargo` | `Cargo.toml` |
| `gomod` | `go.mod` |

---

## Best Practices

### 1. Group Related Dependencies

```yaml
# Group to reduce PR noise
groups:
  all-microsoft:
    patterns:
      - "Microsoft.*"
      - "System.*"
      - "Azure.*"
```

### 2. Ignore Major Updates for Critical Packages

```yaml
ignore:
  # Require manual review for major updates
  - dependency-name: "Microsoft.EntityFrameworkCore*"
    update-types: ["version-update:semver-major"]
  - dependency-name: "react"
    update-types: ["version-update:semver-major"]
```

### 3. Set Reasonable PR Limits

```yaml
# Prevent PR flood
open-pull-requests-limit: 10
```

### 4. Use Semantic Commit Messages

```yaml
commit-message:
  prefix: "chore(deps)"
  prefix-development: "chore(deps-dev)"
  include: "scope"
```

### 5. Assign Appropriate Reviewers

```yaml
reviewers:
  - "team-name"
  - "security-team"  # For security-critical packages

assignees:
  - "bot-account"
```

### 6. Label for Workflow Automation

```yaml
labels:
  - "dependencies"
  - "auto-merge"  # If using auto-merge workflow
```

---

## Auto-Merge Configuration

### GitHub Actions Workflow for Auto-Merge

```yaml
# .github/workflows/dependabot-auto-merge.yml
name: Dependabot Auto-Merge

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: write
  pull-requests: write

jobs:
  auto-merge:
    runs-on: ubuntu-latest
    if: github.actor == 'dependabot[bot]'
    steps:
      - name: Fetch Dependabot metadata
        id: metadata
        uses: dependabot/fetch-metadata@v2
        with:
          github-token: "${{ secrets.GITHUB_TOKEN }}"

      - name: Auto-merge minor and patch updates
        if: |
          steps.metadata.outputs.update-type == 'version-update:semver-patch' ||
          steps.metadata.outputs.update-type == 'version-update:semver-minor'
        run: gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Security Considerations

### 1. Review Before Auto-Merge

- Only auto-merge patch/minor updates
- Require CI to pass before merge
- Major updates require manual review

### 2. Monitor for Security Advisories

```yaml
# Dependabot alerts are enabled separately in repo settings
# Security updates are created automatically when vulnerabilities are found
```

### 3. Private Registry Authentication

```yaml
registries:
  private-nuget:
    type: nuget-feed
    url: https://pkgs.dev.azure.com/org/_packaging/feed/nuget/v3/index.json
    # Use encrypted secrets, never plain text
    password: ${{ secrets.AZURE_ARTIFACTS_PAT }}
```
