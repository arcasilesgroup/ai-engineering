# Quick Install

> Get the AI Engineering Framework running in your project in under 2 minutes.

## One-Line Install

```bash
git clone https://github.com/arcasilesgroup/ai-engineering.git /tmp/ai-framework && \
/tmp/ai-framework/scripts/install.sh \
  --name "MyProject" \
  --stacks dotnet,typescript \
  --cicd github \
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
  --stacks dotnet,typescript \
  --cicd github
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
| `--cicd` | No | CI/CD platform | `github`, `azure`, `both` |
| `--target` | No | Target directory | `/path/to/project` (default: `.`) |
| `--install-tools` | No | Install dev tools | Installs gitleaks, gh CLI, pre-commit and pre-push hooks |
| `--skip-sdks` | No | Skip SDK verification | Skips dotnet, node, python checks |
| `--exec` | No | Run post-install commands | Runs `npm install` / `pip install` |

## With Tool Installation (Recommended)

```bash
/tmp/ai-framework/scripts/install.sh \
  --name "MyProject" \
  --stacks dotnet,typescript \
  --cicd github \
  --install-tools
```

This additionally installs:
- **gitleaks** - Secret scanning
- **gh CLI** - GitHub CLI for `/ship pr` mode
- **pre-commit hook** - Scans staged files for secrets before commit
- **pre-push hook** - Blocks pushes with critical vulnerabilities

## Platform Auto-Detection

If you omit `--cicd`, the installer auto-detects your platform from the git remote URL:

| Remote URL Pattern | Detected Platform |
|--------------------|-------------------|
| `github.com` | GitHub |
| `dev.azure.com` or `visualstudio.com` | Azure DevOps |

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
├── .claude/
│   ├── settings.json            # Permissions + hooks config
│   ├── skills/                  # 11 interactive skills
│   ├── agents/                  # 4 background agents
│   └── hooks/                   # 5 hook scripts
├── standards/                   # 10 coding standards
├── context/                     # Project context templates
├── learnings/                   # Accumulated knowledge templates
├── .github/workflows/           # GitHub Actions (if selected)
└── pipelines/                   # Azure Pipelines (if selected)
```

## Next Steps

1. [Customize Project Context](Getting-Started#customize-your-installation)
2. [Enable Hooks](Installation-Tool-Installation#enabling-hooks)
3. [Try Your First Commands](Skills-Daily-Workflow)

---
**See also:** [Manual Setup](Installation-Manual-Setup) | [Tool Installation](Installation-Tool-Installation)
