# Getting Started

> Install the AI Engineering Framework and start using it in under 5 minutes.

## Prerequisites

- **Claude Code** installed ([claude.ai/claude-code](https://claude.ai/claude-code))
- OR **GitHub Copilot** with Chat enabled
- A project repository (any stack: .NET, TypeScript, Python, Terraform)
- Git and your preferred IDE

## Quick Install

```bash
# Clone the framework
git clone https://github.com/arcasilesgroup/ai-engineering.git /tmp/ai-framework

# Install into your project
/tmp/ai-framework/scripts/install.sh \
  --name "MyProject" \
  --stacks dotnet,typescript \
  --install-tools

# Clean up
rm -rf /tmp/ai-framework
```

The `--install-tools` flag automatically installs gitleaks, gh CLI, and configures a pre-commit secret scanning hook and a pre-push vulnerability check hook.

The installer also creates IDE configuration files (`.editorconfig`, `.vscode/settings.json`, `.vscode/extensions.json`) for built-in linting. See [IDE Linting Setup](Standards-IDE-Linting) for details.

## Verify Installation

Open Claude Code in your project and run:

```
/validate
```

Expected output (abbreviated):
```
## Framework Validation Report
**Status:** VALID
**Version:** 2.0.0
...
Framework is correctly installed.
```

This checks that all required files exist, are correctly configured, verifies tools are installed, and reports the detected CI/CD platform. See [/validate full output example](Skills-Daily-Workflow#validate) for the complete report format.

## What Was Installed

```
your-project/
├── CLAUDE.md                    # AI entry point
├── .editorconfig                # Baseline formatting rules
├── .vscode/
│   ├── settings.json            # IDE linting configuration
│   └── extensions.json          # Recommended extensions
├── .claude/
│   ├── settings.json            # Permissions + hooks config
│   ├── skills/                  # 11 interactive skills
│   ├── agents/                  # 4 background agents
│   └── hooks/                   # 5 hook scripts
├── standards/                   # 10 coding standards
├── context/                     # Project context
└── learnings/                   # Accumulated knowledge
```

## First Commands

Try these commands to get familiar with the framework:

| Command | What It Does |
|---------|--------------|
| `/validate` | Check framework installation |
| `/review staged` | Review your staged changes |
| `/ship` | Smart commit with secret scanning + push |
| `/test` | Generate and run tests |
| `/ship pr` | Commit, push, and create a pull request |

## Customize Your Installation

### 1. Edit Project Context

Edit `context/project.md` with your project details:

```markdown
# Project: MyProject

## Overview
[Describe what your project does]

## Objectives
[What are you building toward?]
```

### 2. Review CLAUDE.md

The `CLAUDE.md` file is the main entry point. Review and customize:
- Project name and description
- Critical rules specific to your project
- Remove references to stacks you don't use

### 3. Configure IDE Linting

The installer creates `.vscode/settings.json` and `.vscode/extensions.json` with recommended linters. To complete the setup:

1. Open VS Code and install the recommended extensions when prompted
2. Configure **SonarLint Connected Mode** to connect to your SonarCloud/SonarQube instance (see [IDE Linting Setup](Standards-IDE-Linting))

### 4. Generate CI/CD Pipelines (Optional)

Pipelines are generated on demand using the scaffold skill:

```
/scaffold cicd github    # For GitHub Actions
/scaffold cicd azure     # For Azure Pipelines
```

See [GitHub Actions](CI-CD-GitHub-Actions) or [Azure Pipelines](CI-CD-Azure-Pipelines) for pipeline structure details.

### 5. Personal Overrides (Optional)

Create `CLAUDE.local.md` for personal, non-committed settings:

```bash
cp CLAUDE.local.md.example CLAUDE.local.md
```

This file is `.gitignore`d by default.

## Next Steps

- [Core Concepts](Core-Concepts-Overview) - Understand the philosophy
- [Skills Overview](Skills-Overview) - Learn about available skills
- [Agents Overview](Agents-Overview) - Learn about background agents

---
**See also:** [Quick Install](Installation-Quick-Install) | [Manual Setup](Installation-Manual-Setup)
