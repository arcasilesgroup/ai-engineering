# IDE Linting Setup

> Catch issues at authoring time with built-in IDE linting configuration.

## Overview

The framework installs three IDE configuration files that provide layered linting, ensuring issues are caught before code leaves the developer's machine.

| File | Purpose |
|------|---------|
| `.editorconfig` | Baseline formatting: indentation, charset, line endings, trailing whitespace |
| `.vscode/settings.json` | IDE linting rules: enable linters, format-on-save, auto-fix |
| `.vscode/extensions.json` | Recommended extensions: SonarLint + stack-specific linters |

## Linting Layers

The three layers work together from broad formatting to deep analysis:

### Baseline: `.editorconfig`

Enforces consistent formatting across all editors and IDEs that support EditorConfig.

- Indentation style and size (per file type)
- Character encoding (UTF-8)
- Line endings (LF)
- Trailing whitespace trimming
- Final newline insertion

This layer works in any editor (VS Code, JetBrains, Vim, etc.) without plugins.

### Stack Linters (Layer 2)

Language-specific linters configured via `.vscode/settings.json` with format-on-save and auto-fix enabled.

| Stack | Linter | Key Features |
|-------|--------|--------------|
| TypeScript | ESLint | Type-aware rules, import ordering, unused variable detection |
| Python | Ruff | Fast linting + formatting, replaces flake8/isort/black |
| .NET | Roslyn Analyzers | Code style, naming conventions, nullable reference types |
| Terraform | tflint | Resource validation, naming conventions, deprecated syntax |

These linters provide immediate feedback in the editor and auto-fix common issues on save.

### SonarLint Connected Mode (Layer 1)

SonarLint runs the same rules as your SonarCloud or SonarQube server, directly in the IDE. Connected Mode synchronizes:

- Quality profiles and rule configurations
- Issue suppressions and exclusions
- New Code Period settings

This ensures that what passes locally will also pass the CI quality gate.

## VS Code Setup

### 1. Install Recommended Extensions

When you open the project in VS Code, you will be prompted to install the recommended extensions from `.vscode/extensions.json`. Accept the prompt, or install manually:

```
Ctrl+Shift+P → Extensions: Show Recommended Extensions → Install All
```

### 2. Configure SonarLint Connected Mode

1. Open VS Code settings (`Ctrl+,`)
2. Search for `sonarlint.connectedMode`
3. Add your SonarCloud or SonarQube connection:

**SonarCloud:**
```json
{
  "sonarlint.connectedMode.connections.sonarcloud": [
    {
      "organizationKey": "your-org",
      "token": "<your-token>"
    }
  ],
  "sonarlint.connectedMode.project": {
    "projectKey": "your-project-key"
  }
}
```

**SonarQube:**
```json
{
  "sonarlint.connectedMode.connections.sonarqube": [
    {
      "serverUrl": "https://sonarqube.your-company.com",
      "token": "<your-token>"
    }
  ],
  "sonarlint.connectedMode.project": {
    "projectKey": "your-project-key"
  }
}
```

> **Note:** Store your SonarLint token in `CLAUDE.local.md` or your personal VS Code settings (not in the committed `.vscode/settings.json`). Never commit tokens to the repository.

### 3. Verify

After setup, SonarLint should show issues inline in the editor with the same severity as your SonarCloud/SonarQube quality profile.

## JetBrains Setup

JetBrains IDEs (IntelliJ, Rider, WebStorm, PyCharm) support EditorConfig natively and have their own SonarLint plugin.

### 1. Install SonarLint Plugin

```
Settings → Plugins → Marketplace → Search "SonarLint" → Install
```

### 2. Configure Connected Mode

```
Settings → Tools → SonarLint → Connection → Add SonarCloud/SonarQube Connection
```

Enter your server URL (or select SonarCloud), provide your token, and bind the project.

### 3. Stack Linters

JetBrains IDEs include built-in support for most stack linters:

| Stack | JetBrains Support |
|-------|-------------------|
| TypeScript | ESLint integration built into WebStorm/IntelliJ |
| Python | Ruff plugin or built-in inspections in PyCharm |
| .NET | Roslyn analyzers supported in Rider |
| Terraform | HCL plugin with tflint integration |

## How It Fits Together

```
Developer writes code
        │
        ▼
  .editorconfig          ← Formatting (all editors)
        │
        ▼
  Stack Linters           ← Language rules, auto-fix on save
  (ESLint/Ruff/Roslyn)
        │
        ▼
  SonarLint               ← Same rules as CI quality gate
  (Connected Mode)
        │
        ▼
  pre-commit hook          ← Secret scanning (gitleaks)
        │
        ▼
  CI Pipeline              ← Full build + test + quality gate
  (/scaffold cicd)
```

Issues are caught as early as possible, reducing CI feedback loops.

---
**See also:** [Quality Gates](Standards-Quality-Gates) | [Standards Overview](Standards-Overview) | [Git Hooks](Hooks-Git-Hooks)
