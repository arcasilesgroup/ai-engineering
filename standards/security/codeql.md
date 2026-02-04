# CodeQL Security Analysis

> GitHub's semantic code analysis for vulnerability detection.

---

## Overview

CodeQL is a semantic code analysis engine that:
- Finds vulnerabilities using queries
- Supports C#, JavaScript/TypeScript, Python, Java, Go, Ruby, C/C++
- Integrates with GitHub Security tab
- Provides SARIF output for any CI system

---

## Query Suites

| Suite | Description | Use Case |
|-------|-------------|----------|
| `default` | High-confidence alerts | Production scanning |
| `security-extended` | More security queries | Security-focused projects |
| `security-and-quality` | Security + code quality | Comprehensive analysis |

---

## GitHub Actions Workflow

### Standard Configuration

```yaml
# .github/workflows/codeql.yml
name: CodeQL Analysis

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  schedule:
    # Run weekly on Monday at 6 AM UTC
    - cron: '0 6 * * 1'

permissions:
  actions: read
  contents: read
  security-events: write

jobs:
  analyze:
    name: Analyze (${{ matrix.language }})
    runs-on: ${{ matrix.os }}
    timeout-minutes: 360

    strategy:
      fail-fast: false
      matrix:
        include:
          - language: csharp
            os: ubuntu-latest
            build-mode: autobuild
          - language: javascript-typescript
            os: ubuntu-latest
            build-mode: none
          - language: python
            os: ubuntu-latest
            build-mode: none

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}
          queries: security-extended
          # Optional: custom queries
          # queries: +security-and-quality,.github/codeql/custom-queries

      # For compiled languages (C#, Java, etc.)
      - name: Autobuild
        if: matrix.build-mode == 'autobuild'
        uses: github/codeql-action/autobuild@v3

      # Alternative: Manual build for .NET
      # - name: Build .NET
      #   if: matrix.language == 'csharp'
      #   run: |
      #     dotnet restore
      #     dotnet build --configuration Release --no-restore

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
        with:
          category: "/language:${{ matrix.language }}"
          upload: true  # Upload to GitHub Security tab
          output: sarif-results
          # add-snippets: true  # Include code snippets in SARIF
```

### Multi-Language with Custom Build

```yaml
# .github/workflows/codeql-custom.yml
name: CodeQL Custom Build

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'

jobs:
  analyze-dotnet:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.x'

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: csharp
          queries: security-extended

      - name: Build
        run: |
          dotnet restore
          dotnet build --configuration Release --no-restore

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
        with:
          category: "/language:csharp"

  analyze-typescript:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: 'src/frontend/package-lock.json'

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: javascript-typescript
          queries: security-extended
          source-root: src/frontend

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
        with:
          category: "/language:javascript-typescript"
```

---

## Azure Pipeline Integration

```yaml
# templates/jobs/codeql-analysis.yml
parameters:
  - name: language
    type: string
    values: ['csharp', 'javascript', 'python']
  - name: buildCommand
    type: string
    default: ''

jobs:
  - job: CodeQL_${{ parameters.language }}
    displayName: 'CodeQL: ${{ parameters.language }}'
    pool:
      vmImage: 'ubuntu-latest'
    steps:
      # Download CodeQL CLI
      - script: |
          wget https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip
          unzip codeql-linux64.zip -d $(Agent.ToolsDirectory)
          echo "##vso[task.prependpath]$(Agent.ToolsDirectory)/codeql"
        displayName: 'Install CodeQL CLI'

      # Download CodeQL queries
      - script: |
          git clone --depth 1 https://github.com/github/codeql.git $(Agent.ToolsDirectory)/codeql-queries
        displayName: 'Download CodeQL Queries'

      # Create database
      - script: |
          codeql database create codeql-db \
            --language=${{ parameters.language }} \
            --source-root=$(Build.SourcesDirectory) \
            ${{ if ne(parameters.buildCommand, '') }}:
            --command="${{ parameters.buildCommand }}"
        displayName: 'Create CodeQL Database'

      # Run analysis
      - script: |
          codeql database analyze codeql-db \
            $(Agent.ToolsDirectory)/codeql-queries/${{ parameters.language }}/ql/src/codeql-suites/${{ parameters.language }}-security-extended.qls \
            --format=sarif-latest \
            --output=codeql-results.sarif
        displayName: 'Run CodeQL Analysis'

      # Upload SARIF
      - task: PublishBuildArtifacts@1
        inputs:
          pathToPublish: 'codeql-results.sarif'
          artifactName: 'codeql-${{ parameters.language }}'
        displayName: 'Publish SARIF Results'

      # Optional: Upload to GitHub Security tab
      - script: |
          codeql github upload-results \
            --sarif=codeql-results.sarif \
            --repository=$(Build.Repository.Name) \
            --ref=$(Build.SourceBranch) \
            --commit=$(Build.SourceVersion)
        displayName: 'Upload to GitHub'
        condition: eq(variables['Build.SourceBranch'], 'refs/heads/main')
        env:
          GITHUB_TOKEN: $(GITHUB_TOKEN)
```

---

## Custom Queries

### Query Structure

```
.github/codeql/
├── custom-queries/
│   ├── csharp/
│   │   ├── qlpack.yml
│   │   └── security/
│   │       └── HardcodedCredentials.ql
│   └── javascript/
│       ├── qlpack.yml
│       └── security/
│           └── InsecureRandomness.ql
└── codeql-config.yml
```

### Custom Query Example (C#)

```ql
// .github/codeql/custom-queries/csharp/security/HardcodedCredentials.ql
/**
 * @name Hardcoded credentials
 * @description Finds hardcoded passwords or API keys
 * @kind problem
 * @problem.severity error
 * @security-severity 9.0
 * @precision high
 * @id cs/hardcoded-credentials
 * @tags security
 *       external/cwe/cwe-798
 */

import csharp

from StringLiteral s
where
  s.getValue().regexpMatch("(?i).*(password|secret|api[_-]?key|token).*=.*[a-zA-Z0-9]{8,}.*")
select s, "Potential hardcoded credential detected."
```

### Configuration File

```yaml
# .github/codeql/codeql-config.yml
name: "Custom CodeQL Config"

queries:
  - uses: security-extended
  - uses: ./.github/codeql/custom-queries

paths-ignore:
  - tests
  - '**/*.test.ts'
  - '**/*Tests.cs'

query-filters:
  - exclude:
      id: cs/xml-external-entity  # False positive in our context
```

---

## Common Vulnerabilities Detected

### C# / .NET

| CWE | Name | Example |
|-----|------|---------|
| CWE-89 | SQL Injection | String concatenation in queries |
| CWE-79 | XSS | Unencoded user input in HTML |
| CWE-798 | Hardcoded Credentials | Passwords in source |
| CWE-327 | Weak Cryptography | MD5, SHA1 for security |
| CWE-502 | Insecure Deserialization | BinaryFormatter usage |
| CWE-601 | Open Redirect | Unvalidated redirect URLs |

### JavaScript/TypeScript

| CWE | Name | Example |
|-----|------|---------|
| CWE-79 | XSS | innerHTML with user input |
| CWE-94 | Code Injection | eval() with user data |
| CWE-918 | SSRF | Unvalidated URLs in fetch |
| CWE-312 | Cleartext Storage | localStorage for secrets |
| CWE-1275 | Cookie without flags | Missing Secure/HttpOnly |

---

## Best Practices

1. **Run on every PR**: Catch issues before merge
2. **Weekly full scan**: Detect new vulnerability patterns
3. **Use security-extended**: More comprehensive than default
4. **Custom queries**: Add organization-specific rules
5. **Review alerts**: Don't ignore, either fix or dismiss with reason
6. **SARIF integration**: Upload to GitHub Security tab for tracking
7. **Baseline**: Track metrics over time (open/closed alerts)
