# AI Engineering Framework

> Zero-dependency, AI-native framework for software engineering teams. Standards, commands, agents, quality gates, and CI/CD — all in markdown.

## What Is This?

A collection of **markdown files** that AI coding agents (Claude Code, GitHub Copilot) read natively to enforce your team's standards, automate workflows, and maintain quality. No CLI, no build step, no dependencies.

```
Your Project + AI Engineering Framework = Consistent, Secure, Quality Code
```

## Quick Start

### 1. Install

```bash
git clone https://github.com/your-org/ai-engineering.git /tmp/ai-engineering

/tmp/ai-engineering/scripts/install.sh \
  --name "MyProject" \
  --stacks dotnet,typescript \
  --cicd github
```

### 2. Customize

Edit `context/project.md` with your project details and review `CLAUDE.md`.

### 3. Use

Open Claude Code and type `/commit`, `/review`, `/test`, or any available command.

---

## Features

### Slash Commands (20)

| Command | Description |
|---------|-------------|
| `/commit` | Smart commit with secret scanning |
| `/pr` | Create structured pull request |
| `/review` | Code review against standards |
| `/test` | Generate and run tests |
| `/fix` | Fix build, test, or lint errors |
| `/refactor` | Refactor with test verification |
| `/security-audit` | OWASP Top 10 security review |
| `/quality-gate` | Run quality gate checks |
| `/blast-radius` | Analyze impact of changes |
| `/deploy-check` | Pre-deployment verification |
| `/document` | Generate documentation |
| `/create-adr` | Create Architecture Decision Record |
| `/learn` | Record a learning for future sessions |
| `/validate` | Validate framework installation |
| `/setup-project` | Initialize new project |
| `/add-endpoint` | Scaffold .NET API endpoint |
| `/add-component` | Scaffold React component |
| `/migrate-api` | Migrate API version |
| `/dotnet/add-provider` | Create .NET provider |
| `/dotnet/add-http-client` | Create typed HTTP client |
| `/dotnet/add-error-mapping` | Add error type + mapping |

### Background Agents (6)

| Agent | Purpose |
|-------|---------|
| `build-validator` | Verify build + tests pass |
| `test-runner` | Run tests with coverage |
| `security-scanner` | Scan secrets, deps, OWASP |
| `quality-checker` | SonarQube quality gate |
| `doc-generator` | Update docs from code |
| `code-simplifier` | Reduce complexity |

### Standards (10)

| Standard | Scope |
|----------|-------|
| `global.md` | Universal conventions |
| `dotnet.md` | .NET / ASP.NET Core |
| `typescript.md` | TypeScript / React |
| `python.md` | Python |
| `terraform.md` | Terraform / IaC |
| `security.md` | OWASP, secrets, deps |
| `quality-gates.md` | SonarQube, linters |
| `cicd.md` | GitHub Actions + Azure Pipelines |
| `testing.md` | Cross-stack testing |
| `api-design.md` | REST API conventions |

### CI/CD (Dual Platform)

| Platform | Workflows |
|----------|-----------|
| **GitHub Actions** | CI, Security, Quality Gate |
| **Azure Pipelines** | CI, Security, Quality Gate + 6 reusable templates |

### Quality & Security Stack (All Free)

| Tool | Purpose |
|------|---------|
| SonarQube Cloud | Code quality + quality gates |
| SonarLint | IDE real-time quality |
| gitleaks | Secret detection |
| Snyk | Dependency scanning |
| CodeQL | Static analysis (GitHub) |
| OWASP Dependency-Check | Dependency analysis (Azure) |
| Dependabot | Automated dependency updates |

---

## Directory Structure

```
ai-engineering/
├── CLAUDE.md                    # Master entry point for Claude Code
├── .claude/
│   ├── settings.json            # Permissions config
│   ├── commands/                # 20 slash commands
│   │   └── dotnet/              # Stack-specific commands
│   └── agents/                  # 6 background agents
├── .github/
│   ├── copilot-instructions.md  # GitHub Copilot master instructions
│   ├── instructions/            # File-pattern-matched instructions
│   └── workflows/               # GitHub Actions CI/CD
├── pipelines/                   # Azure Pipelines CI/CD
│   └── templates/               # Reusable pipeline templates
├── standards/                   # 10 coding standards files
├── context/                     # Project-specific context
│   └── decisions/               # Architecture Decision Records
├── learnings/                   # Accumulated knowledge
├── workshop/                    # 9-module learning guide
└── scripts/
    └── install.sh               # Framework installer
```

---

## How It Works

```
CLAUDE.md (entry point)
    │
    ├── References standards/*.md for coding rules
    ├── References learnings/*.md for accumulated knowledge
    ├── Lists available commands in .claude/commands/
    └── Lists available agents in .claude/agents/
          │
          ├── Commands: human-directed, multi-step workflows
          │   /commit → scan secrets → analyze changes → conventional commit
          │   /review → read standards → analyze code → generate report
          │
          └── Agents: autonomous, focused, background verification
              build-validator → detect stack → build → test → report
              security-scanner → gitleaks → dep audit → OWASP scan → report
```

---

## Integration Options

### Option A: Install Script (Recommended)

```bash
./scripts/install.sh --name "MyProject" --stacks dotnet,typescript --cicd github
```

### Option B: Git Submodule

```bash
git submodule add <repo-url> .ai-engineering
ln -s .ai-engineering/CLAUDE.md CLAUDE.md
ln -s .ai-engineering/.claude .claude
```

### Option C: GitHub Template Repository

Click "Use this template" on GitHub.

---

## Tool Compatibility

| Tool | Support | How |
|------|---------|-----|
| **Claude Code** | Full | CLAUDE.md + .claude/commands/ + .claude/agents/ |
| **GitHub Copilot** | Full | .github/copilot-instructions.md + .github/instructions/ |
| **Cursor** | Partial | Reads CLAUDE.md and standards |
| **VS Code + SonarLint** | Full | Connected mode with SonarQube Cloud |

---

## Workshop

Learn the framework step by step:

| Module | Topic |
|--------|-------|
| [00](workshop/00-introduction.md) | Introduction — What and why |
| [01](workshop/01-installation.md) | Installation — Get started |
| [02](workshop/02-first-commands.md) | First Commands — Daily workflow |
| [03](workshop/03-standards-and-learnings.md) | Standards & Learnings |
| [04](workshop/04-agents.md) | Agents — Background workers |
| [05](workshop/05-quality-gates.md) | Quality Gates — SonarQube, Snyk |
| [06](workshop/06-cicd-integration.md) | CI/CD — GitHub Actions + Azure |
| [07](workshop/07-customization.md) | Customization — Extend the framework |
| [08](workshop/08-advanced-workflows.md) | Advanced — Parallel Claudes, hooks |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT - see [LICENSE](LICENSE).
