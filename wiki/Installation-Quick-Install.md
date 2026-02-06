# Quick Install

> Get the AI Engineering Framework running in your project in under 2 minutes.

## One-Line Install

```bash
git clone https://github.com/arcasilesgroup/ai-engineering.git /tmp/ai-framework && \
/tmp/ai-framework/scripts/install.sh \
  --name "MyProject" \
  --stacks dotnet,typescript \
  --install-tools && \
rm -rf /tmp/ai-framework
```

## Step by Step

### 1. Clone the Framework

```bash
git clone https://github.com/arcasilesgroup/ai-engineering.git /tmp/ai-framework
```

### 2. Run the Installer

```bash
/tmp/ai-framework/scripts/install.sh \
  --name "MyProject" \
  --stacks dotnet,typescript
```

### 3. Clean Up

```bash
rm -rf /tmp/ai-framework
```

## Install Options

| Flag | Required | Description | Example |
|------|----------|-------------|---------|
| `--name` | Yes | Project name | `"MyProject"` |
| `--stacks` | Yes | Comma-separated stacks | `dotnet,typescript,python,terraform` |
| `--target` | No | Target directory | `/path/to/project` (default: `.`) |
| `--install-tools` | No | Install dev tools | Installs gitleaks, gh CLI, pre-commit and pre-push hooks |
| `--skip-sdks` | No | Skip SDK verification | Skips dotnet, node, python checks |
| `--exec` | No | Run post-install commands | Runs `npm install` / `pip install` |

> **CI/CD pipelines** are no longer installed via a flag. Use `/scaffold cicd github` or `/scaffold cicd azure` after installation to generate pipelines on demand. See [GitHub Actions](CI-CD-GitHub-Actions) or [Azure Pipelines](CI-CD-Azure-Pipelines).

## With Tool Installation (Recommended)

```bash
/tmp/ai-framework/scripts/install.sh \
  --name "MyProject" \
  --stacks dotnet,typescript \
  --install-tools
```

This additionally installs:
- **gitleaks** - Secret scanning
- **gh CLI** - GitHub CLI for `/ship pr` mode
- **pre-commit hook** - Scans staged files for secrets before commit
- **pre-push hook** - Blocks pushes with critical vulnerabilities

## Verify Installation

After installing, open Claude Code and run:

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

See [/validate full output example](Skills-Daily-Workflow#validate) for the complete report format.

## What Gets Installed

```
your-project/
├── CLAUDE.md                    # AI entry point
├── CLAUDE.local.md.example      # Template for personal overrides
├── .editorconfig                # Baseline formatting rules
├── .vscode/
│   ├── settings.json            # IDE linting configuration
│   └── extensions.json          # Recommended extensions (SonarLint + stack linters)
├── .claude/
│   ├── settings.json            # Permissions + hooks config
│   ├── skills/                  # 11 interactive skills
│   ├── agents/                  # 4 background agents
│   └── hooks/                   # 5 hook scripts
├── standards/                   # 10 coding standards
├── context/                     # Project context templates
└── learnings/                   # Accumulated knowledge templates
```

> CI/CD pipeline files (`.github/workflows/` or `pipelines/`) are generated on demand via `/scaffold cicd github` or `/scaffold cicd azure`.

## Next Steps

1. [Customize Project Context](Getting-Started#customize-your-installation)
2. [Enable Hooks](Installation-Tool-Installation#enabling-hooks)
3. [Try Your First Commands](Skills-Daily-Workflow)

---
**See also:** [Manual Setup](Installation-Manual-Setup) | [Tool Installation](Installation-Tool-Installation)
