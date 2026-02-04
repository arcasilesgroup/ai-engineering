# Module 1: Installation

## Overview

Install the AI Engineering Framework into your project using one of three methods.

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
| `--cicd` | No | CI/CD platform (default: github) | `github`, `azure`, `both` |
| `--target` | No | Target directory (default: `.`) | `/path/to/project` |

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
2. Click **"Use this template"** → **"Create a new repository"**
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

### 3. Verify Installation

Open Claude Code in your project and run:

```
/validate
```

This checks that all required files exist and are correctly configured.

---

## What Was Installed

```
your-project/
├── CLAUDE.md                    # AI entry point
├── .claude/
│   ├── settings.json            # Permissions
│   ├── commands/                # Slash commands
│   └── agents/                  # Background agents
├── standards/                   # Coding standards
├── context/                     # Project context
├── learnings/                   # Accumulated knowledge
├── .github/workflows/           # GitHub Actions (if selected)
└── pipelines/                   # Azure Pipelines (if selected)
```

## Next

→ [Module 2: First Commands](02-first-commands.md)
