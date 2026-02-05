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
  --cicd github \
  --install-tools

# Clean up
rm -rf /tmp/ai-framework
```

The `--install-tools` flag automatically installs gitleaks, gh CLI, and configures a pre-commit secret scanning hook and a pre-push vulnerability check hook.

## Verify Installation

Open Claude Code in your project and run:

```
/validate
```

Expected output:
```
## Framework Validation Report

**Status:** VALID
**Version:** 2.0.0

### Files
- [x] CLAUDE.md
- [x] .claude/settings.json
- [x] Skills: 21 found
- [x] Agents: 6 found
- [x] Hooks: 4 found (4 executable)
- [x] Standards: 10 found

### Platform
- [x] Platform: GitHub
- [x] CLI: gh installed
- [x] Auth: Authenticated

### Tools
- [x] gitleaks: installed
- [x] Pre-commit hook: installed
- [x] Pre-push hook: installed
- [x] Stack tools: configured

### Warnings
(none)

Framework is correctly installed.
```

This checks that all required files exist, are correctly configured, verifies tools are installed, and reports the detected CI/CD platform.

## What Was Installed

```
your-project/
├── CLAUDE.md                    # AI entry point
├── .claude/
│   ├── settings.json            # Permissions + hooks config
│   ├── skills/                  # 21 interactive skills
│   ├── agents/                  # 6 background agents
│   └── hooks/                   # 4 hook scripts
├── standards/                   # 10 coding standards
├── context/                     # Project context
├── learnings/                   # Accumulated knowledge
├── .github/workflows/           # GitHub Actions (if selected)
└── pipelines/                   # Azure Pipelines (if selected)
```

## First Commands

Try these commands to get familiar with the framework:

| Command | What It Does |
|---------|--------------|
| `/validate` | Check framework installation |
| `/review staged` | Review your staged changes |
| `/commit-push` | Smart commit with secret scanning + push |
| `/test` | Generate and run tests |
| `/pr` | Create a pull request |

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

### 3. Personal Overrides (Optional)

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
