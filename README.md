# ai-engineering

AI coding assistant framework with executable enforcement: **prompts + runtime hooks + verification gates**.

The first framework that physically blocks dangerous actions and automatically verifies quality — not just suggestions.

## The Problem

AI coding assistants are powerful but undisciplined. Existing frameworks suggest best practices but cannot *prevent* the AI from ignoring them. `ai-engineering` solves this with three layers of enforcement:

| Layer | What | How |
|-------|------|-----|
| **Prompts** | Standards, agents, skills compiled into IDE instructions | AI reads at session start |
| **Runtime Hooks** | Pre/post tool validation | Blocks dangerous operations in real-time |
| **Verification Gates** | Git hooks + CI/CD quality gates | Blocks bad code from leaving the machine |

## Quick Start

```bash
npx ai-engineering init
```

This interactive wizard:
1. Detects your stack (TypeScript/React, .NET, Python, CI/CD)
2. Detects your IDE (Claude Code, GitHub Copilot, Codex)
3. Asks your enforcement level (Basic, Standard, Strict)
4. Generates all configuration files

### Non-Interactive

```bash
npx ai-engineering init --stack typescript-react --ide claude-code --level strict --yes
```

### Multi-Stack, Multi-IDE

```bash
npx ai-engineering init --stack typescript-react dotnet --ide claude-code copilot --level strict --yes
```

## What Gets Generated

```
your-project/
├── .ai-engineering/           # Framework config, standards, knowledge
│   ├── config.yml             # Central configuration
│   ├── standards/             # Compiled standards per stack
│   ├── knowledge/             # Your project's learnings, patterns, ADRs
│   └── hooks/                 # Runtime enforcement hooks
├── CLAUDE.md                  # Claude Code instructions (if selected)
├── .claude/commands/          # Slash commands (/ai-commit, /ai-review, etc.)
├── .github/copilot-instructions.md  # Copilot instructions (if selected)
├── codex.md                   # Codex instructions (if selected)
├── lefthook.yml               # Git hooks (Standard/Strict levels)
└── .gitleaks.toml             # Secret scanning config
```

## Stacks

| Stack | Coverage |
|-------|----------|
| **TypeScript/React** | TS strict, React patterns, Vitest + RTL, XSS prevention |
| **.NET** | C#, ASP.NET Core, EF Core, Clean Architecture, xUnit |
| **Python** | Typing, async, FastAPI/Django, pytest, injection prevention |
| **CI/CD** | GitHub Actions, Azure Pipelines, secrets, caching |

## IDE Targets

| IDE | Output | Enforcement |
|-----|--------|-------------|
| **Claude Code** | CLAUDE.md + commands + settings.json | Prompts + Runtime hooks + Git hooks |
| **GitHub Copilot** | copilot-instructions.md | Prompts + Git hooks |
| **Codex** | codex.md | Prompts + Git hooks |

## Enforcement Levels

| Level | Prompts | Git Hooks | Runtime Hooks | CI/CD Gates |
|-------|---------|-----------|---------------|-------------|
| **Basic** | Yes | - | - | - |
| **Standard** | Yes | Yes (gitleaks, lint, format, conventional commits) | - | - |
| **Strict** | Yes | Yes + tests + dep audit | Yes (block dangerous ops) | Yes (PR quality gates) |

## Agents

| Agent | Purpose |
|-------|---------|
| **Developer** | Implementation with Boris Cherny principles |
| **Reviewer** | Structured code review with severity ratings |
| **Code Simplifier** | Post-implementation complexity reduction |
| **Verify App** | End-to-end testing verification pipeline |
| **Code Explain** | Feynman-style teaching |

## Skills (Slash Commands)

| Command | Description |
|---------|-------------|
| `/ai-commit` | Verified commit (gitleaks + lint + format + conventional) |
| `/ai-pr` | Structured PR with risk assessment |
| `/ai-implement` | Guided implementation workflow |
| `/ai-review` | Multi-pass code review |
| `/ai-security` | OWASP security audit |
| `/ai-git` | Git Way-of-Working (cleanup, health, full report) |
| `/ai-explain` | Feynman-style code explanation |

## Updating

```bash
# Check what would change
npx ai-engineering update --dry-run

# Apply update (creates backup automatically)
npx ai-engineering update

# Rollback if needed
npx ai-engineering update --rollback
```

Updates are safe:
- **Framework files** (hooks, scripts): auto-replaced
- **Compiled output** (CLAUDE.md, commands): re-compiled
- **Your customizations** (config, blocklist): 3-way merge
- **Your knowledge** (learnings, patterns, ADRs): never touched

## Branch Compliance

Protected branches are enforced by git hooks:
- **main/master**: No direct push, requires PR + review + all checks
- **develop**: Requires PR + checks
- **release/\***: PR to default branch required
- **hotfix/\***: Push allowed, must PR to default + develop
- **dev/\***: No restrictions

## Development

```bash
git clone https://github.com/your-org/ai-engineering.git
cd ai-engineering
npm install
npm run build
npm test
```

## License

MIT
