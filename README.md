# AI Engineering Framework

> Zero-dependency, AI-native framework for software engineering teams. Skills, agents, hooks, quality gates, and CI/CD — all in markdown.

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

Open Claude Code and type `/commit`, `/review`, `/test`, or any available skill.

---

## Features

### Skills (21)

Interactive workflows invoked with `/skill-name`. They run in the current session.

| Skill | Description | Auto-invocable |
|-------|-------------|:--------------:|
| `/commit` | Smart commit with secret scanning | No |
| `/commit-push-pr` | Full cycle: commit + push + PR (GitHub + Azure DevOps) | No |
| `/pr` | Create structured pull request (GitHub + Azure DevOps) | No |
| `/review` | Code review against standards | Yes |
| `/test` | Generate and run tests | Yes |
| `/fix` | Fix build, test, or lint errors | Yes |
| `/refactor` | Refactor with test verification | No |
| `/security-audit` | OWASP Top 10 security review | No |
| `/quality-gate` | Run quality gate checks | No |
| `/blast-radius` | Analyze impact of changes | Yes |
| `/deploy-check` | Pre-deployment verification | No |
| `/document` | Generate documentation | No |
| `/create-adr` | Create Architecture Decision Record | No |
| `/learn` | Record a learning for future sessions | Yes |
| `/validate` | Validate framework + platform detection | Yes |
| `/setup-project` | Initialize new project | No |
| `/add-endpoint` | Scaffold .NET API endpoint | No |
| `/add-component` | Scaffold React component | No |
| `/migrate-api` | Migrate API version | No |
| `/dotnet:add-provider` | Create .NET provider | No |
| `/dotnet:add-http-client` | Create typed HTTP client | No |
| `/dotnet:add-error-mapping` | Add error type + mapping | No |

### Background Agents (5)

Autonomous agents dispatched for parallel work. They run independently and report results.

| Agent | Purpose |
|-------|---------|
| **verify-app** | The "finisher": build + tests + lint + security + quality in one pass |
| **code-architect** | Designs before implementing: analyzes codebase, proposes 2 options |
| **oncall-guide** | Production incident debugging: root cause, fix, rollback |
| **doc-generator** | Update docs from code changes |
| **code-simplifier** | Reduce complexity with pattern-aware reconnaissance |

### Hooks (4)

Shell scripts that run automatically in response to Claude Code events.

| Hook | Trigger | Action |
|------|---------|--------|
| `auto-format.sh` | After Edit/Write | Runs formatter for the file type |
| `block-dangerous.sh` | Before Bash | Blocks force push, rm -rf, etc. |
| `block-env-edit.sh` | Before Edit/Write | Blocks editing .env and credential files |
| `notify.sh` | Notification | Desktop notification on macOS/Linux |

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

### Multi-Platform Support

The framework auto-detects your platform from the git remote URL:

| Platform | CLI | PR Command | Work Item Linking |
|----------|-----|------------|------------------|
| **GitHub** | `gh` | `gh pr create` | `Closes #123` |
| **Azure DevOps** | `az` | `az repos pr create` | `AB#123` |

---

## Directory Structure

```
ai-engineering/
├── CLAUDE.md                    # Master entry point for Claude Code
├── VERSION                      # Framework version (semver)
├── CHANGELOG.md                 # Version history
├── UPGRADING.md                 # Migration guide between versions
├── .claude/
│   ├── settings.json            # Permissions + hooks config
│   ├── skills/                  # 21 interactive skills
│   │   ├── commit/SKILL.md
│   │   ├── commit-push-pr/SKILL.md
│   │   ├── pr/SKILL.md
│   │   ├── ...
│   │   ├── dotnet/              # Stack-specific skills
│   │   ├── utils/               # Shared utilities (platform detection, git helpers)
│   │   └── custom/              # Team custom skills (never overwritten)
│   ├── agents/                  # 5 background agents
│   │   ├── verify-app.md
│   │   ├── code-architect.md
│   │   ├── oncall-guide.md
│   │   ├── doc-generator.md
│   │   ├── code-simplifier.md
│   │   └── custom/              # Team custom agents (never overwritten)
│   └── hooks/                   # 4 hook scripts
│       ├── auto-format.sh
│       ├── block-dangerous.sh
│       ├── block-env-edit.sh
│       └── notify.sh
├── .github/
│   ├── copilot-instructions.md  # GitHub Copilot instructions
│   ├── instructions/            # File-pattern-matched instructions
│   └── workflows/               # GitHub Actions CI/CD
├── pipelines/                   # Azure Pipelines CI/CD
│   └── templates/               # Reusable pipeline templates
├── standards/                   # 10 coding standards files
├── context/                     # Project-specific context
│   └── decisions/               # Architecture Decision Records
├── learnings/                   # Accumulated knowledge
├── workshop/                    # 11-module learning guide
└── scripts/
    └── install.sh               # Framework installer + updater
```

---

## How It Works

```
CLAUDE.md (entry point)
    │
    ├── References standards/*.md for coding rules
    ├── References learnings/*.md for accumulated knowledge
    ├── Lists available skills in .claude/skills/
    ├── Lists available agents in .claude/agents/
    └── Hooks in .claude/hooks/ run automatically
          │
          ├── Skills: human-directed, multi-step workflows
          │   /commit-push-pr → scan → commit → push → create PR
          │   /review → read standards → analyze code → report
          │
          ├── Agents: autonomous, focused, background verification
          │   verify-app → build → test → lint → security → quality → report
          │   code-architect → analyze → propose options → plan
          │
          └── Hooks: automatic, event-driven guards
              auto-format → detect type → format
              block-dangerous → check command → allow/block
```

---

## Production Reliability (Boris Cherny Workflow)

The framework enforces 6 production reliability practices:

1. **Verification Protocol** — Exact commands per stack. Never "should work."
2. **Reconnaissance Before Writing** — Search for 2+ existing patterns before implementing.
3. **Two Options for High Stakes** — Propose A and B with pros/cons. Wait for approval.
4. **Danger Zones** — Extra caution for auth, DB, payments, permissions, config, API contracts, CI/CD.
5. **Layered Memory** — Global → Project → Personal context, loaded in order.
6. **Reliability Template** — Goal → Constraints → Recon → Plan → Wait → Implement → Verify → Summarize.

See [workshop/09-boris-cherny-workflow.md](workshop/09-boris-cherny-workflow.md) for the full guide.

---

## Three-Layer Architecture

```
┌──────────────────────────────────────────────┐
│ LAYER 1: Framework (upstream, versioned)     │
│ Skills, hooks, agents, standards, workshop   │
│ → Updated via install.sh --update            │
├──────────────────────────────────────────────┤
│ LAYER 2: Team (project, committed)           │
│ CLAUDE.md, context/, learnings/, custom/     │
│ → Maintained by the team                     │
├──────────────────────────────────────────────┤
│ LAYER 3: Personal (local, NOT committed)     │
│ CLAUDE.local.md, ~/.claude/CLAUDE.md         │
│ → Individual engineer preferences            │
└──────────────────────────────────────────────┘
```

Update with: `scripts/install.sh --update --target /path/to/project`

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
| **Claude Code** | Full | Skills + agents + hooks + standards + learnings + CLAUDE.md |
| **GitHub Copilot** | Standards | `.github/copilot-instructions.md` + `.github/instructions/` |
| **Cursor** | Partial | Reads CLAUDE.md and standards |
| **VS Code + SonarLint** | Full | Connected mode with SonarQube Cloud |

### Claude Code vs GitHub Copilot

| Capability | Claude Code | Copilot |
|-----------|:-----------:|:-------:|
| Skills (`/commit`, `/pr`, etc.) | Full | No |
| Agents (verify-app, code-architect) | Full | No |
| Hooks (auto-format, security guards) | Full | No |
| Terminal execution (build, test) | Full | No |
| Standards enforcement | Active | Passive |
| Multi-platform PRs (GitHub + AzDO) | Full | No |

Copilot users get value from the framework as a **standards library** via `copilot-instructions.md`. The full automation (skills, agents, hooks, verification) is Claude Code only.

---

## Workshop

Learn the framework step by step:

| Module | Topic |
|--------|-------|
| [00](workshop/00-introduction.md) | Introduction — What and why |
| [01](workshop/01-installation.md) | Installation — Get started |
| [02](workshop/02-first-commands.md) | First Skills — Daily workflow |
| [03](workshop/03-standards-and-learnings.md) | Standards & Learnings |
| [04](workshop/04-agents.md) | Agents — Background workers |
| [05](workshop/05-quality-gates.md) | Quality Gates — SonarQube, Snyk |
| [06](workshop/06-cicd-integration.md) | CI/CD — GitHub Actions + Azure |
| [07](workshop/07-customization.md) | Customization — Extend the framework |
| [08](workshop/08-advanced-workflows.md) | Advanced — Hooks, parallel work, MCP |
| [09](workshop/09-boris-cherny-workflow.md) | Production Reliability — The Boris Cherny workflow |
| [10](workshop/10-versioning.md) | Versioning — Updates, personalization |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT - see [LICENSE](LICENSE).
