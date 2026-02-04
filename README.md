# AI Engineering Framework (ai-engineering)

> **Single Source of Truth** for AI-assisted software engineering.

[![PyPI version](https://badge.fury.io/py/ai-engineering.svg)](https://badge.fury.io/py/ai-engineering)
[![CI](https://github.com/arcasilesgroup/ai-engineering/actions/workflows/ci.yml/badge.svg)](https://github.com/arcasilesgroup/ai-engineering/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This framework provides a standardized, tool-agnostic structure for working with AI coding assistants. It integrates seamlessly with GitHub Copilot, Claude, and other AI tools while maintaining consistency across projects.

## Installation

### Option 1: pip (Recommended)

```bash
pip install ai-engineering
```

### Option 2: One-liner Installation

**Linux/macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
iwr -useb https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/install.ps1 | iex
```

### Option 3: From Source

```bash
git clone https://github.com/arcasilesgroup/ai-engineering.git
cd ai-engineering
pip install -e .
```

### Option 4: GitHub Template

Use this repository as a template to include the full `.ai/` framework structure:

1. Click "Use this template" on GitHub
2. Create your new repository
3. The `.ai/` structure is ready to customize

### Option 5: Git Submodule (Advanced)

For teams wanting independent framework updates:

```bash
# Add as submodule
git submodule add https://github.com/arcasilesgroup/ai-engineering.git .ai-framework
ln -s .ai-framework/.ai .ai

# Update to latest
git submodule update --remote
```

## Quick Start

```bash
# Initialize in a new project
ai-engineering init --name "MyProject" --stack dotnet

# Sync to GitHub Copilot
ai-engineering sync github

# Sync to Claude
ai-engineering sync claude

# Validate framework structure
ai-engineering validate

# Update to latest version
ai-engineering update
```

## CLI Commands

### `ai-engineering init`

Initialize the `.ai/` framework in a new project.

```bash
ai-engineering init --name "MyAPI" --stack dotnet
ai-engineering init --name "WebApp" --stack typescript --target ./my-project
ai-engineering init -n "DataPipeline" -s python --include-examples
```

**Options:**
- `--name, -n` - Project name (required)
- `--stack, -s` - Technology stack: `dotnet`, `typescript`, `python`, `terraform`, `multi` (required)
- `--target, -t` - Target directory (default: current)
- `--include-examples, -e` - Include example files
- `--force, -f` - Overwrite existing `.ai/` directory

### `ai-engineering sync`

Synchronize `.ai/` content to AI tool configurations.

```bash
ai-engineering sync github          # Sync to GitHub Copilot (.github/)
ai-engineering sync claude          # Sync to Claude (.claude/)
ai-engineering sync all             # Sync to all tools
ai-engineering sync github --dry-run  # Preview changes
```

**Options:**
- `--force, -f` - Overwrite existing files
- `--dry-run, -n` - Preview without making changes

### `ai-engineering validate`

Validate the `.ai/` framework structure and content.

```bash
ai-engineering validate           # Basic validation
ai-engineering validate --fix     # Validate and fix issues
ai-engineering validate -v        # Verbose output
```

**Options:**
- `--fix, -f` - Attempt to fix issues
- `--verbose, -v` - Show detailed results

### `ai-engineering update`

Update ai-engineering to the latest version.

```bash
ai-engineering update              # Update CLI to latest
ai-engineering update --check      # Check for updates only
ai-engineering update --framework  # Update CLI and project templates
```

### Legacy Script Support

For backwards compatibility, you can still use Python scripts directly:

```bash
python .ai/tools/sync_github.py
python .ai/tools/sync_claude.py
python .ai/tools/validate.py
```

## Framework Structure

```
.ai/
├── README.md                    # This file
├── config.yaml                  # Global configuration
│
├── context/                     # PROJECT CONTEXT
│   ├── project.md               # Vision, objectives, stakeholders
│   ├── architecture.md          # System architecture (C4 compatible)
│   ├── stack.md                 # Technology stack details
│   ├── glossary.md              # Domain terminology
│   └── decisions/               # Architecture Decision Records (ADRs)
│
├── standards/                   # CODING STANDARDS
│   ├── _index.yaml              # Standards registry
│   ├── global.md                # Cross-stack rules
│   ├── dotnet/                  # .NET specific
│   ├── typescript/              # TypeScript/React specific
│   ├── python/                  # Python specific
│   └── infrastructure/          # Terraform/IaC specific
│
├── prompts/                     # REUSABLE PROMPTS
│   ├── _index.yaml              # Prompts registry
│   ├── system.md                # Base system prompt
│   └── templates/               # Prompt templates by use case
│
├── skills/                      # MODULAR SKILLS
│   ├── _index.yaml              # Skills registry
│   ├── dotnet/                  # .NET skills
│   ├── typescript/              # TypeScript skills
│   └── cross-cutting/           # Universal skills
│
├── agents/                      # AUTONOMOUS AGENTS
│   ├── _index.yaml              # Agents registry
│   ├── feature-builder/         # Multi-step feature creation
│   ├── code-reviewer/           # Code review automation
│   └── migrator/                # Version migration assistance
│
├── learnings/                   # EVOLUTIONARY LEARNINGS
│   ├── global.md                # Cross-project learnings
│   └── by-stack/                # Stack-specific learnings
│
└── tools/                       # AUTOMATION SCRIPTS (Legacy)
    ├── sync_github.py           # Wrapper for ai-engineering sync github
    ├── sync_claude.py           # Wrapper for ai-engineering sync claude
    └── validate.py              # Wrapper for ai-engineering validate
```

## AI Tool Integration

### GitHub Copilot

`ai-engineering sync github` generates:
- `.github/copilot-instructions.md` - Main instructions from `prompts/system.md`
- `.github/instructions/*.md` - Stack-specific instructions from `standards/`
- `.github/prompts/*.md` - Prompt templates

### Claude

`ai-engineering sync claude` generates:
- `.claude/CLAUDE.md` - Combined project documentation
- `.claude/commands/*.md` - Prompt templates as commands
- `.claude/docs/*.md` - Stack-specific standards

### Other Tools

The agnostic `.ai/` structure can be adapted to any AI tool by creating a new sync command.

## Core Concepts

### Hierarchy: Prompts -> Skills -> Agents

![Concept Hierarchy](.ai/assets/svg/prompt-skill-agent.svg)

| Concept | Purpose | Autonomy | Example |
|---------|---------|----------|---------|
| **Prompt** | Define AI behavior | None (static) | "Use Result pattern" |
| **Skill** | Atomic capability | Low (invoked) | "Create API endpoint" |
| **Agent** | Orchestrate workflows | High (autonomous) | "Build complete feature" |

### When to Use What

| Task | Use |
|------|-----|
| Change base behavior | **Prompt** |
| Repetitive atomic task | **Skill** |
| Complex multi-step work | **Agent** |

## Cross-Platform Support

ai-engineering works on:
- **Windows** 10/11 (PowerShell 5.1+, CMD)
- **macOS** (Intel & Apple Silicon)
- **Linux** (Ubuntu, Debian, Fedora, Arch, etc.)

**Requirements:**
- Python 3.9 or higher
- pip (Python package manager)

## File Format Conventions

### YAML Front Matter (for tool integration)

```yaml
---
id: skill-id
name: Human Readable Name
description: Brief description for AI tools
applyTo: "**/*.cs"              # Glob pattern (optional)
tags: [dotnet, api]
---
```

### Learnings Format

```markdown
* Learning description with context (weight)
```
- Weight starts at `1`, increases with confirmation
- Higher weight = higher priority for AI consideration

### ADR Format (Architecture Decision Records)

```markdown
# ADR-001: Title

## Status
Accepted | Superseded | Deprecated

## Context
Why this decision was needed

## Decision
What was decided

## Consequences
Impact of the decision
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Follow existing patterns when adding new content
4. Update `_index.yaml` files when adding skills/agents
5. Run `ai-engineering validate` before committing
6. Submit a Pull Request

## License

MIT - See [LICENSE](LICENSE) file for details.

## Links

- [Documentation](https://github.com/arcasilesgroup/ai-engineering#readme)
- [Issues](https://github.com/arcasilesgroup/ai-engineering/issues)
- [PyPI Package](https://pypi.org/project/ai-engineering/)
