# Quality Gates Standards

> Consolidated quality gate standards: SonarQube thresholds, linter configurations per stack, coverage targets, and setup guides.

---

## 1. SonarQube Quality Gate Thresholds

### Default Quality Gate ("Sonar Way" Enhanced)

All projects must pass these thresholds before merging to the main branch:

| Metric | Threshold | Scope |
|--------|-----------|-------|
| Coverage | >= 80% | New code |
| Duplicated Lines | <= 3% | New code |
| Maintainability Rating | A | New code |
| Reliability Rating | A | New code |
| Security Rating | A | New code |
| Security Hotspots Reviewed | 100% | New code |

### Rating Scale Reference

| Rating | Meaning |
|--------|---------|
| A | No issues (or minimal technical debt ratio < 5%) |
| B | Minor issues (technical debt ratio 6-10%) |
| C | Major issues (technical debt ratio 11-20%) |
| D | Critical issues (technical debt ratio 21-50%) |
| E | Blocker issues (technical debt ratio > 50%) |

### Quality Gate Enforcement

- Quality gates are enforced as PR checks; merging is blocked if the gate fails
- Quality gate applies to **new code** (code changed in the PR) by default
- Overall project health is monitored but does not block PRs (improve incrementally)
- Security hotspots must be reviewed and marked as safe or fixed before merge

---

## 2. SonarLint IDE Setup

### Required IDE Integration

Every developer must have SonarLint installed and connected to the SonarQube server:

**VS Code:**
```json
// .vscode/settings.json
{
  "sonarlint.connectedMode.connections.sonarqube": [
    {
      "connectionId": "company-sonarqube",
      "serverUrl": "https://sonarqube.company.com",
      "token": "${env:SONAR_TOKEN}"
    }
  ],
  "sonarlint.connectedMode.project": {
    "connectionId": "company-sonarqube",
    "projectKey": "my-project-key"
  }
}
```

**JetBrains (Rider, IntelliJ, PyCharm):**
1. Install SonarLint plugin from Marketplace
2. Settings > Tools > SonarLint > Connect to SonarQube
3. Bind project to remote SonarQube project key

### Benefits of Connected Mode

- Rules synchronized with server quality profile
- Issues detected locally before push
- Suppressed issues respected locally
- New rules applied automatically

---

## 3. Linter Configurations Per Stack

### Python: Ruff

```toml
# pyproject.toml
[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = [
    "E", "W",   # pycodestyle
    "F",         # pyflakes
    "I",         # isort
    "N",         # pep8-naming
    "UP",        # pyupgrade
    "B",         # flake8-bugbear
    "S",         # flake8-bandit
    "A",         # flake8-builtins
    "C4",        # flake8-comprehensions
    "DTZ",       # flake8-datetimez
    "RUF",       # ruff-specific
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101"]
```

### TypeScript: ESLint

```json
{
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/strict-type-checked",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended"
  ],
  "rules": {
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/explicit-function-return-type": ["error", {
      "allowExpressions": true
    }],
    "@typescript-eslint/no-unused-vars": ["error", {
      "argsIgnorePattern": "^_"
    }],
    "react-hooks/exhaustive-deps": "error",
    "no-console": ["warn", { "allow": ["warn", "error"] }]
  }
}
```

### .NET: Roslyn Analyzers

```xml
<!-- Directory.Build.props -->
<Project>
  <PropertyGroup>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <AnalysisLevel>latest-recommended</AnalysisLevel>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
    <EnableNETAnalyzers>true</EnableNETAnalyzers>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" Version="8.*" />
    <PackageReference Include="SonarAnalyzer.CSharp" Version="9.*" />
    <PackageReference Include="StyleCop.Analyzers" Version="1.*" />
  </ItemGroup>
</Project>
```

```ini
# .editorconfig (selected rules)
[*.cs]
dotnet_diagnostic.CA1062.severity = error    # Validate arguments of public methods
dotnet_diagnostic.CA2007.severity = error    # ConfigureAwait
dotnet_diagnostic.CA1848.severity = warning  # Use LoggerMessage delegates
dotnet_diagnostic.SA1600.severity = none     # Elements should be documented (too noisy)
```

### Terraform: tflint

```hcl
# .tflint.hcl
config {
  call_module_type = "local"
}

plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

plugin "azurerm" {
  enabled = true
  version = "0.27.0"
  source  = "github.com/terraform-linters/tflint-ruleset-azurerm"
}

rule "terraform_naming_convention" {
  enabled = true
  format  = "snake_case"
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_typed_variables" {
  enabled = true
}
```

---

## 4. Coverage Thresholds by Layer

### Target Coverage by Architecture Layer

| Layer | Minimum Coverage | Rationale |
|-------|-----------------|-----------|
| Providers / Repositories | 90% | Data access correctness is critical |
| Services / Business Logic | 80% | Core domain logic must be well tested |
| Controllers / API Handlers | 70% | Integration-tested; less unit coverage needed |
| Utilities / Helpers | 90% | Reused widely; must be reliable |
| Infrastructure / Config | 50% | Often integration-tested at higher levels |
| UI Components | 70% | Behavior-focused testing; visual testing supplements |

### Coverage Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|-------------|---------|-----------------|
| Chasing 100% coverage | Diminishing returns, brittle tests | Focus on meaningful coverage per layer |
| Testing private methods | Coupled to implementation | Test through public interface |
| Coverage without assertions | Tests pass but verify nothing | Every test must assert expected behavior |
| Excluding files to inflate numbers | Hides untested code | Only exclude generated and config files |

---

## 5. SonarQube Cloud Setup (Free for Open Source)

### Step 1: Connect Repository

1. Navigate to [sonarcloud.io](https://sonarcloud.io) and sign in with GitHub
2. Import your organization and select the repository
3. SonarCloud automatically detects language and creates a default quality gate

### Step 2: Configure CI Integration

```yaml
# .github/workflows/sonar.yml
name: SonarCloud Analysis
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  sonar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for accurate blame

      - name: SonarCloud Scan
        uses: SonarSource/sonarcloud-github-action@master
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

### Step 3: Configure Project Properties

```properties
# sonar-project.properties
sonar.organization=my-org
sonar.projectKey=my-org_my-project
sonar.sources=src
sonar.tests=tests
sonar.coverage.exclusions=**/tests/**,**/*.test.*,**/migrations/**
sonar.javascript.lcov.reportPaths=coverage/lcov.info
sonar.python.coverage.reportPaths=coverage.xml
```

### Step 4: Enable PR Decoration

- SonarCloud automatically decorates PRs with quality gate status
- Configure branch protection rules to require the SonarCloud check to pass
- PR comments show new issues, coverage changes, and duplications

---

## 6. SonarQube Community Build Setup (Self-Hosted)

### Step 1: Deploy SonarQube

```yaml
# docker-compose.yml
services:
  sonarqube:
    image: sonarqube:community
    ports:
      - "9000:9000"
    environment:
      SONAR_JDBC_URL: jdbc:postgresql://db:5432/sonarqube
      SONAR_JDBC_USERNAME: sonar
      SONAR_JDBC_PASSWORD: ${SONAR_DB_PASSWORD}
    volumes:
      - sonarqube_data:/opt/sonarqube/data
      - sonarqube_extensions:/opt/sonarqube/extensions
    depends_on:
      - db

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: sonar
      POSTGRES_PASSWORD: ${SONAR_DB_PASSWORD}
      POSTGRES_DB: sonarqube
    volumes:
      - postgresql_data:/var/lib/postgresql/data

volumes:
  sonarqube_data:
  sonarqube_extensions:
  postgresql_data:
```

### Step 2: Configure Quality Gate

1. Navigate to Administration > Quality Gates
2. Create a new quality gate or copy "Sonar Way"
3. Set thresholds per the table in Section 1
4. Set as default for all projects

### Step 3: Configure CI Scanner

```yaml
# Azure Pipelines example
- task: SonarQubePrepare@6
  inputs:
    SonarQube: "sonarqube-connection"
    scannerMode: "CLI"
    configMode: "manual"
    cliProjectKey: "my-project"
    cliSources: "src"
    extraProperties: |
      sonar.coverage.exclusions=**/tests/**
      sonar.cs.opencover.reportsPaths=**/coverage.opencover.xml

- script: dotnet build && dotnet test --collect:"XPlat Code Coverage"
  displayName: "Build and Test"

- task: SonarQubeAnalyze@6
  displayName: "Run SonarQube Analysis"

- task: SonarQubePublish@6
  displayName: "Publish Quality Gate Result"
```

### Step 4: Branch Analysis (Developer Edition+)

- Community Build only analyzes the main branch
- For PR analysis, use SonarQube Developer Edition or SonarCloud
- Alternative: Run analysis on feature branches and compare manually

---

## 7. Quality Gate Decision Matrix

| Scenario | Action |
|----------|--------|
| Quality gate passes | Merge allowed (still requires code review) |
| Coverage below threshold | Fix: add tests for new code |
| Duplications above threshold | Fix: extract shared logic |
| Security rating below A | Fix: resolve all security issues (blocking) |
| Reliability rating below A | Fix: resolve all bugs (blocking) |
| Security hotspots not reviewed | Fix: review all hotspots and mark safe/fixed |
| Overall project rating low | Track as tech debt; improve incrementally |
