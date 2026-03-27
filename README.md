<div align="center">
  <a href="https://github.com/arcasilesgroup/ai-engineering">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/banner-dark.svg">
      <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/banner-light.svg">
      <img src="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/banner-light.svg" alt="ai-engineering — AI governance framework" width="700">
    </picture>
  </a>

  <p><strong>Open-source governance framework for AI-assisted software delivery</strong></p>

  <p>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
    <a href="https://pypi.org/project/ai-engineering/"><img src="https://img.shields.io/pypi/v/ai-engineering.svg" alt="PyPI"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.11%2B-blue.svg" alt="Python 3.11+"></a>
    <a href="https://github.com/arcasilesgroup/ai-engineering/actions"><img src="https://github.com/arcasilesgroup/ai-engineering/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <a href="https://sonarcloud.io/summary/overall?id=arcasilesgroup_ai-engineering"><img src="https://sonarcloud.io/api/project_badges/measure?project=arcasilesgroup_ai-engineering&metric=alert_status" alt="Quality Gate"></a>
    <a href="https://sonarcloud.io/summary/overall?id=arcasilesgroup_ai-engineering"><img src="https://sonarcloud.io/api/project_badges/measure?project=arcasilesgroup_ai-engineering&metric=coverage" alt="Coverage"></a>
    <a href="https://snyk.io/test/github/arcasilesgroup/ai-engineering"><img src="https://snyk.io/test/github/arcasilesgroup/ai-engineering/badge.svg" alt="Snyk"></a>
  </p>
</div>

ai-engineering turns any repository into a governed AI workspace. One command installs quality gates, security scanning, and risk management — enforced locally through git hooks so problems are caught before code leaves your machine. It works with Claude Code, GitHub Copilot, Gemini CLI, and OpenAI Codex out of the box.

[Install](#install-recommended) · [Quick start](#quick-start) · [How it works](#how-it-works-short) · [What you get](#what-you-get) · [Governance root](#the-governance-root--ai-engineering) · [Commands](#commands-reference) · [AI providers](#ai-provider-setup) · [Contributing](#contributing)

## Install (recommended)

```bash
pip install ai-engineering
```

Or with `uv`:

```bash
uv pip install ai-engineering
```

Requires Python 3.11+ and Git.

## Quick start

```bash
cd your-project
ai-eng install .                           # bootstrap governance + git hooks
ai-eng doctor                              # verify everything is operational
git commit -m "first governed commit"      # quality gates run automatically
```

Install with a specific stack and IDE:

```bash
ai-eng install . --stack python --ide vscode
```

Your next commit after install is already governed — formatting, linting, and secret scanning run automatically.

## How it works (short)

ai-engineering is a **content framework**, not a platform. The governance layer is Markdown, YAML, and JSON living inside your repository. The CLI (`ai-eng`) handles lifecycle operations — install, update, doctor, validate — while git hooks enforce quality and security at every commit and push.

```
your-project/
├── .ai-engineering/            ← governance root (content-first)
│   ├── standards/              ← rules for AI agents and quality gates
│   ├── skills/                 ← 34 procedural skills AI agents execute
│   ├── agents/                 ← 8 role-based agent personas
│   ├── context/                ← project memory: specs, goals, decisions
│   └── state/                  ← decisions, risks, audit trail
├── .claude/skills/             ← 34 slash commands (Claude Code)
├── .github/skills/             ← 36 Agent Skills (GitHub Copilot)
├── .github/agents/             ← 8 custom agents (GitHub Copilot)
├── AGENTS.md                   ← instruction file (Gemini CLI / Codex / Copilot)
├── .git/hooks/                 ← quality gate hooks (auto-installed)
└── ...your code
```

Three ownership boundaries keep your content safe:

- **Framework-managed** — standards and baselines, updated by `ai-eng update`. Preview-first by default, with confirmation before writes in interactive terminals.
- **Team-managed** — your team's rules and overrides. Never overwritten by framework updates.
- **Project-managed** — specs, product goals, decisions. Never overwritten. Your project memory stays yours.

## What you get

- **Quality gates at every commit** — `ruff`, `gitleaks`, `semgrep`, `pip-audit`, `pytest`, and `ty` run at the right stage. Problems are blocked before they reach the remote repository.
- **Security scanning without CI** — secrets, SAST/OWASP vulnerabilities, and dependency CVEs are detected locally on every push.
- **Risk acceptance lifecycle** — accept, track, and expire security risks with severity-based deadlines (critical: 15 days, high: 30, medium: 60, low: 90). Max 2 renewals per risk.
- **34 procedural skills** — structured procedures for commit, PR, debug, refactor, code review, security assessment, architecture review, and more. AI agents read and execute them.
- **8 role-based agents** — behavioral contracts for plan, build, guard, verify, guide, operate, explore, and simplify. Each agent has identity, capabilities, and boundaries. Only `ai-build` has code write permissions.
- **Multi-provider from day one** — same governance works with Claude Code (34 slash commands), GitHub Copilot (34 prompt files + 8 custom agents), Gemini CLI, and OpenAI Codex.
- **Stack-aware enforcement** — tailored rules for Python, .NET, and Next.js. Each stack has its own linting, testing, and security toolchain.
- **Content integrity validation** — 6 programmatic categories verify that governance files stay consistent across updates.
- **Doctor diagnostics** — one command checks framework health and auto-fixes missing hooks or tools.
- **Framework updates without risk** — `ai-eng update` previews changes, explains protected files, and asks for confirmation before writing in interactive terminals. Your team and project content is never touched.

## The governance root — `.ai-engineering/`

When you run `ai-eng install`, a `.ai-engineering/` directory is created in your repository. This is the single source of truth for all governance behavior. Everything is content — Markdown, YAML, JSON — readable by humans and AI agents alike.

### Standards

Rules and conventions that AI agents and quality gates follow.

Standards use a two-layer model. The **framework layer** (`standards/framework/`) provides the baseline — coverage thresholds, complexity limits, security requirements. The **team layer** (`standards/team/`) is where you add overrides. Your team can raise the coverage threshold from 80% to 95%, add stricter linting rules, or define project-specific conventions. Framework updates never touch the team layer.

Each supported stack (21 stacks: Python, .NET, TypeScript, Rust, Java/Kotlin, Swift, Ruby, PHP, C/C++, and more) has its own standards file with tailored rules for linting, formatting, testing, and dependency management.

### Skills — 34 in flat organization

Skills are step-by-step procedures written in Markdown that any AI agent can read and execute. They define **what** the agent does, **when** to trigger, **how** to execute, and **what** to output. All skills live in `skills/<name>/SKILL.md` — no nested categories.

Skill frontmatter follows the Anthropic skill-creator pattern with `name` and `description` (the primary trigger, under 1024 chars) at top level, and versioning/classification under `metadata`.

| Domain | Skills |
|--------|--------|
| Planning | plan, contract, spec, cleanup, explain |
| Build | code, test, debug, refactor, simplify, api, schema, pipeline, infra, migrate |
| Verify | security, quality, governance, architecture, performance, accessibility, gap, integrity |
| Ship | commit, pr, release, triage |
| Write | document |
| Observe | dashboard, evolve |
| Guard | guard |
| Execute | dispatch |
| Operate | ops |
| Governance | lifecycle |

Invoke any skill with `/ai-<name>` — for example, `/ai-debug` for systematic diagnosis, `/ai-security` for security assessment, or `/ai-governance` for proactive governance validation.

Skills are provider-agnostic — the same skill works in Claude Code, GitHub Copilot, Gemini CLI, and OpenAI Codex without modification.

### Agents — 8 role-based personas

Agents are behavioral contracts for AI (the ROLE). Skills are procedures (the HOW). Agents compose skills at runtime — this is the Strategy Pattern applied to AI governance.

| Agent | Role | Scope |
|-------|------|-------|
| **plan** | Planning pipeline, spec creation — stops before execution | read-write |
| **guard** | Proactive governance advisory during development (shift-left) | read-only + decision-store |
| **build** | Implementation across 20+ stacks (only code write agent) | read-write |
| **verify** | 7-mode assessment: security, quality, governance, performance, accessibility, architecture, gap | read-write (work items only) |
| **guide** | Developer growth: teach, onboard, explain, architecture tour | read-only |
| **operate** | SRE: runbook execution, incident response, operational health | read-write (issues only) |
| **explorer** | Context gatherer: codebase navigation, dependency mapping, architecture discovery | read-only |
| **simplifier** | Background code cleaner: reduce complexity, guard clauses, early returns, dead code removal | read-write |

Activate any agent with `/ai-<name>` — for example, `/ai-build` for implementation, `/ai-verify` for assessment, or `ai-guard` as a dispatched governance advisory agent.

### Context — your project memory

Context is where your project lives. Product goals, active specifications, and decisions — all stored as Markdown files that AI agents read to understand your project.

The spec-driven delivery model tracks work through four documents:

- **spec.md** — what to build (requirements, scope, acceptance criteria)
- **plan.md** — how to build it (architecture decisions, approach, trade-offs)
- **tasks.md** — what to do (ordered, assignable, trackable tasks)
- **done.md** — what was done (completion summary)

Any AI agent can resume work on any spec by reading `_active.md` → `spec.md` → `tasks.md`. No context is lost between sessions.

Context is project-managed — the framework never overwrites it.

### State — decisions, risks, and framework events

State files track runtime information automatically:

- **decision-store.json** — decisions persist across AI sessions with SHA-256 context hashing. No repeated questions — agents check the store before asking.
- **framework-events.ndjson** — append-only canonical framework event stream for hooks, gates, governance, security, and quality outcomes.
- **framework-capabilities.json** — machine-readable catalog of skills, agents, contexts, and hook kinds for downstream viewers.
- **install-manifest.json** — what was installed, when, which version.
- **ownership-map.json** — who owns each path in the governance root.

State is system-managed — maintained automatically by the CLI and git hooks.

## Commands (reference)

Core commands you use daily:

```bash
ai-eng install [TARGET]           # Bootstrap governance in any project
ai-eng install --provider claude_code --provider github_copilot  # Select AI providers
ai-eng update [TARGET]            # Preview framework updates
ai-eng update [TARGET] --apply    # Preview, confirm in TTY, then apply framework updates
ai-eng doctor [TARGET]            # Diagnose and auto-fix framework health
ai-eng guide [TARGET]             # View branch policy setup instructions
ai-eng validate [TARGET]          # Validate content integrity
ai-eng spec verify|catalog|list|compact  # Spec lifecycle management
ai-eng decision record "<TITLE>"  # Record architectural decisions (dual-write NDJSON + Markdown)
ai-eng release <VERSION>          # Create a governed release (validate, bump, PR, tag)
ai-eng version                    # Show installed version and lifecycle status
```

Additional command groups for stack/IDE management, quality gates, skills, maintenance, platform setup, VCS configuration, and CI/CD are documented in the [CLI reference](docs/cli-reference.md).

## AI provider setup

ai-engineering generates integration files for each AI provider during install.

### Claude Code (recommended)

The framework generates `CLAUDE.md` (instruction file) and 34 slash commands via skills in `.claude/skills/`. Run `/ai-commit` to stage, validate, commit, and push. Run `/ai-build` to activate the build agent. All commands invoke canonical skill and agent files — no content is duplicated.

### Gemini CLI

The framework generates `AGENTS.md` (instruction file) for Gemini CLI. It provides context and rules similar to `CLAUDE.md`. The same governance, skills, and conventions apply automatically.

### GitHub Copilot

The framework generates `.github/copilot-instructions.md`, 36 Agent Skills in `.github/skills/`, and 9 custom agents in `.github/agents/`. Use skills like `/ai-commit` or `/ai-debug` and agents like `@build` or `@verify` directly in Copilot Chat.

### OpenAI Codex

Codex CLI reads `AGENTS.md` natively — no separate instruction file needed. The same governance, skills, and conventions apply automatically.

Switch providers at any time — the governance layer is the same. Skills and agents are Markdown, not provider-specific code.

## Configuration

ai-engineering uses a content-first approach — configuration lives in `.ai-engineering/` as Markdown, YAML, and JSON files.

**At install time**, control which stacks and IDEs to enable via `--stack` and `--ide` flags. Add or remove them later with `ai-eng stack` and `ai-eng ide` commands.

**Updates** are preview-first by default. Run `ai-eng update` to inspect grouped results, or `ai-eng update --apply` to preview and then apply. In interactive terminals the CLI asks for confirmation before writing; in JSON or non-TTY mode it stays prompt-free. The updater only touches framework-managed files.

**Doctor remediation** provides `--fix` to repair the framework and `--fix --phase <name>` to target a specific phase (e.g. `hooks` to reinstall git hooks, `tools` to auto-install missing tools such as `ruff`, `ty`, `gitleaks`, `semgrep`, `pip-audit`).

**Risk lifecycle** enforces severity-based expiry:

| Severity | Expiry | Max renewals |
|----------|--------|--------------|
| Critical | 15 days | 2 |
| High | 30 days | 2 |
| Medium | 60 days | 2 |
| Low | 90 days | 2 |

Expired risks block `git push` until you remediate or renew them.

## Tooling baseline

| Tool | Purpose | Scope |
|------|---------|-------|
| `uv` | Package and runtime management | Local |
| `ruff` | Linting and formatting | Local + CI |
| `ty` | Type checking | Local + CI |
| `pip-audit` | Dependency vulnerability scanning | Local + CI |
| `gitleaks` | Secret detection | Local + CI |
| `semgrep` | Static analysis (SAST/OWASP) | Local + CI |
| [SonarCloud](https://sonarcloud.io/summary/overall?id=arcasilesgroup_ai-engineering) | Code quality, coverage, and duplication analysis | CI |
| [Snyk](https://snyk.io) | Dependency vulnerabilities + SAST (requires `SNYK_TOKEN`) | CI |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, testing, and pull request guidelines.

## Code of conduct

This project follows the Contributor Covenant Code of Conduct. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE)
