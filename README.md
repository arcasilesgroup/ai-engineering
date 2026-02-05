<div align="center">

# AI Engineering Framework

**The production-ready framework for AI-assisted software development**

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/arcasilesgroup/ai-engineering/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-purple.svg)](https://claude.ai/code)

[Documentation](https://github.com/arcasilesgroup/ai-engineering/wiki) |
[Quick Start](#quick-start) |
[Features](#features) |
[Contributing](CONTRIBUTING.md)

</div>

---

## Why AI Engineering Framework?

Traditional coding standards live in documents nobody reads. **This framework embeds standards directly into your AI assistant.**

```
Before: "Please follow our coding standards" -> AI ignores them
After:  Standards loaded automatically -> AI enforces them
```

**Zero dependencies. Pure markdown. Works with Claude Code out of the box.**

---

## Quick Start

### 1. Install

```bash
# Clone the framework
git clone https://github.com/arcasilesgroup/ai-engineering.git /tmp/ai-framework

# Install in your project
/tmp/ai-framework/scripts/install.sh \
  --name "MyProject" \
  --stacks dotnet,typescript \
  --cicd github \
  --install-tools
```

### 2. Verify

Open Claude Code in your project and run:

```
/validate
```

### 3. Use

Type `/` to see available skills:

- `/commit` — Smart commits with secret scanning
- `/review` — Code review against your standards
- `/test` — Generate and run tests
- `/pr` — Create pull requests (GitHub + Azure DevOps)

**[Full documentation](https://github.com/arcasilesgroup/ai-engineering/wiki)**

---

## Features

### Skills (21)

Interactive workflows that execute in your current session.

| Category | Skills |
|----------|--------|
| **Git** | `/commit`, `/pr`, `/commit-push-pr` |
| **Quality** | `/review`, `/test`, `/fix`, `/refactor` |
| **Security** | `/security-audit`, `/quality-gate` |
| **Documentation** | `/document`, `/create-adr` |
| **Setup** | `/validate`, `/setup-project`, `/learn` |

### Agents (6)

Background workers for autonomous tasks.

| Agent | Purpose |
|-------|---------|
| `verify-app` | Build + test + lint + security in one pass |
| `code-architect` | Design before implementing |
| `oncall-guide` | Production debugging assistance |
| `doc-generator` | Auto-update documentation |
| `code-simplifier` | Reduce complexity |

### Standards (10)

Stack-specific coding rules enforced by AI.

- `.NET` / `TypeScript` / `Python` / `Terraform`
- `Security` (OWASP) / `API Design` / `Testing`
- `Quality Gates` (SonarQube thresholds)
- `CI/CD` (GitHub Actions + Azure Pipelines)

### Hooks (5)

Automatic guards and formatters.

| Hook | Trigger | Action |
|------|---------|--------|
| `auto-format` | After edit | Format code |
| `block-dangerous` | Before bash | Block `rm -rf`, force push |
| `block-env-edit` | Before edit | Protect `.env` files |
| `pre-push` | Before push | Block critical vulnerabilities |

---

## How It Works

```
CLAUDE.md (loaded automatically by Claude Code)
├── References -> standards/*.md
├── References -> learnings/*.md
├── Lists -> .claude/skills/
└── Lists -> .claude/agents/

        |
        v

AI reads your standards and enforces them
• "Use Result<T> pattern" -> AI uses Result<T>
• "Never hardcode secrets" -> AI warns you
• "Run tests before PR" -> AI runs tests
```

---

## Installation Options

| Method | Best For | Command |
|--------|----------|---------|
| **Script** | New projects | `./install.sh --name X --stacks Y` |
| **Update** | Existing projects | `./install.sh --update` |
| **Submodule** | Monorepos | [See wiki](https://github.com/arcasilesgroup/ai-engineering/wiki/Advanced-Submodule-Approach) |

### Install Flags

| Flag | Description |
|------|-------------|
| `--name` | Project name (required) |
| `--stacks` | `dotnet`, `typescript`, `python`, `terraform` |
| `--cicd` | `github`, `azure`, `both` |
| `--install-tools` | Install gitleaks, gh CLI, hooks |
| `--skip-sdks` | Skip SDK verification |
| `--exec` | Run `npm install` / `pip install` after |

---

## Documentation

**[View Full Documentation](https://github.com/arcasilesgroup/ai-engineering/wiki)**

| Section | Description |
|---------|-------------|
| [Getting Started](https://github.com/arcasilesgroup/ai-engineering/wiki/Getting-Started) | Install and configure |
| [Skills](https://github.com/arcasilesgroup/ai-engineering/wiki/Skills-Overview) | All 21 workflows |
| [Agents](https://github.com/arcasilesgroup/ai-engineering/wiki/Agents-Overview) | Background workers |
| [Standards](https://github.com/arcasilesgroup/ai-engineering/wiki/Standards-Overview) | Coding rules |
| [Hooks](https://github.com/arcasilesgroup/ai-engineering/wiki/Hooks-Overview) | Automation |
| [CI/CD](https://github.com/arcasilesgroup/ai-engineering/wiki/CI-CD-GitHub-Actions) | Pipeline setup |
| [Advanced](https://github.com/arcasilesgroup/ai-engineering/wiki/Advanced-Parallel-Work) | Power features |
| [FAQ](https://github.com/arcasilesgroup/ai-engineering/wiki/FAQ) | Common questions |

---

## Compatibility

| Tool | Support |
|------|---------|
| **Claude Code** | Full (skills, agents, hooks) |
| **GitHub Copilot** | Standards only |
| **Cursor** | CLAUDE.md only |

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

Made with care for AI-assisted development

</div>
