# Module 1: Installation

## Overview

Install the AI Engineering Framework into your project using one of three methods. The installer auto-detects your CI/CD platform (GitHub or Azure DevOps) based on your repository's remote URL.

---

## Option A: Install Script (Recommended)

```bash
# Clone the framework
git clone https://github.com/your-org/ai-engineering.git /tmp/ai-engineering

# Install into your project
/tmp/ai-engineering/scripts/install.sh \
  --name "MyProject" \
  --stacks dotnet,typescript \
  --cicd github \
  --target /path/to/your/project

# Clean up
rm -rf /tmp/ai-engineering
```

### Flags

| Flag | Required | Description | Example |
|------|----------|-------------|---------|
| `--name` | Yes | Project name | `"MyProject"` |
| `--stacks` | Yes | Comma-separated stacks | `dotnet,typescript` |
| `--cicd` | No | CI/CD platform (auto-detected if omitted) | `github`, `azure`, `both` |
| `--target` | No | Target directory (default: `.`) | `/path/to/project` |
| `--update` | No | Update an existing installation (preserves customizations) | — |

### Updating an Existing Installation

If the framework is already installed, use `--update` to pull in new skills, agents, and hooks without overwriting your customized files (e.g., `context/project.md`, `learnings/`, `CLAUDE.local.md`):

```bash
/tmp/ai-engineering/scripts/install.sh \
  --name "MyProject" \
  --stacks dotnet,typescript \
  --target /path/to/your/project \
  --update
```

---

## Option B: Git Submodule

```bash
cd your-project

# Add as submodule
git submodule add https://github.com/your-org/ai-engineering.git .ai-engineering

# Symlink the files Claude Code needs
ln -s .ai-engineering/CLAUDE.md CLAUDE.md
ln -s .ai-engineering/.claude .claude
ln -s .ai-engineering/standards standards

# Copy files you'll customize
cp -r .ai-engineering/context context
cp -r .ai-engineering/learnings learnings

# Copy CI/CD for your platform
cp -r .ai-engineering/.github/workflows .github/workflows
# OR
cp -r .ai-engineering/pipelines pipelines
```

---

## Option C: GitHub Template Repository

1. Go to the framework repository on GitHub
2. Click **"Use this template"** -> **"Create a new repository"**
3. Clone your new repository
4. Customize `context/project.md` and `CLAUDE.md`

---

## Post-Installation

### 1. Customize Project Context

Edit `context/project.md` and replace the `{{PLACEHOLDER}}` values:

```markdown
# Project: MyProject

## Overview
[Describe what your project does]

## Objectives
[What are you building toward?]
```

### 2. Customize CLAUDE.md

Review `CLAUDE.md` and update:
- Project name and description
- Critical rules specific to your project
- Remove references to stacks you don't use

### 3. Set Up Personal Overrides (Optional)

Copy the example file for personal, non-committed overrides:

```bash
cp CLAUDE.local.md.example CLAUDE.local.md
```

Edit `CLAUDE.local.md` for sprint context, personal preferences, or environment-specific settings. This file is `.gitignore`d by default.

### 4. Enable Hooks

Make the hook scripts executable:

```bash
chmod +x .claude/hooks/*.sh
```

This enables the safety and productivity hooks (auto-format, block dangerous commands, protect `.env` files, desktop notifications).

### 5. Verify Installation

Open Claude Code in your project and run:

```
/validate
```

This checks that all required files exist, are correctly configured, and reports the detected CI/CD platform (GitHub or Azure DevOps).

---

## What Was Installed

```
your-project/
├── CLAUDE.md                    # AI entry point
├── CLAUDE.local.md.example      # Template for personal overrides
├── .claude/
│   ├── settings.json            # Permissions + hooks config
│   ├── skills/                  # Slash skills (commands)
│   │   ├── commit.md
│   │   ├── pr.md
│   │   ├── review.md
│   │   ├── test.md
│   │   └── ...
│   ├── agents/                  # Background agents
│   └── hooks/                   # Event-driven shell scripts
│       ├── auto-format.sh       # PostToolUse: format after edits
│       ├── block-dangerous.sh   # PreToolUse: block force push, rm -rf
│       ├── block-env-edit.sh    # PreToolUse: protect .env files
│       └── notify.sh            # Notification: desktop alerts
├── standards/                   # Coding standards
├── context/                     # Project context
├── learnings/                   # Accumulated knowledge
├── .github/workflows/           # GitHub Actions (if detected/selected)
└── pipelines/                   # Azure Pipelines (if detected/selected)
```

## Next

-> [Module 2: First Skills](02-first-commands.md)
