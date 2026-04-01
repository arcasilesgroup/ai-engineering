<div align="center">
  <a href="https://github.com/arcasilesgroup/ai-engineering">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/banner-dark.svg">
      <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/banner-light.svg">
      <img src="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/banner-light.svg" alt="ai-engineering — AI governance framework" width="700">
    </picture>
  </a>

  <p><strong>Open-source AI governance framework</strong></p>

  <p>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
    <a href="https://pypi.org/project/ai-engineering/"><img src="https://img.shields.io/pypi/v/ai-engineering.svg" alt="PyPI"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.11%2B-blue.svg" alt="Python 3.11+"></a>
    <a href="https://github.com/arcasilesgroup/ai-engineering/actions"><img src="https://github.com/arcasilesgroup/ai-engineering/actions/workflows/ci-check.yml/badge.svg" alt="CI"></a>
    <a href="https://sonarcloud.io/summary/overall?id=arcasilesgroup_ai-engineering"><img src="https://sonarcloud.io/api/project_badges/measure?project=arcasilesgroup_ai-engineering&metric=alert_status" alt="Quality Gate"></a>
    <a href="https://sonarcloud.io/summary/overall?id=arcasilesgroup_ai-engineering"><img src="https://sonarcloud.io/api/project_badges/measure?project=arcasilesgroup_ai-engineering&metric=coverage" alt="Coverage"></a>
    <a href="https://snyk.io/test/github/arcasilesgroup/ai-engineering"><img src="https://snyk.io/test/github/arcasilesgroup/ai-engineering/badge.svg" alt="Snyk"></a>
  </p>
</div>

**47 skills. 10 agents. 4 IDEs. One governed workflow.**

AI governance that developers actually want -- for teams that ship.

ai-engineering turns any repository into a governed AI workspace. Governance is content-first: policies, skills, agents, runbooks, and specs all live as versioned files inside the repo -- no hosted control plane, no vendor lock-in. It works across Claude Code, GitHub Copilot, OpenAI Codex, and Gemini CLI from the same repository.

[Install](#install) · [Quick Start](#quick-start) · [What You Get](#what-you-get) · [How It Works](#how-it-works) · [CLI](#cli-commands) · [Slash Commands](#slash-commands) · [Inspirations](#standing-on-the-shoulders-of) · [Contributing](#contributing)

## Install

```bash
pip install ai-engineering
```

Or with `uv`:

```bash
uv pip install ai-engineering
```

Requires Python 3.11+ and Git.

## Quick Start

```bash
cd your-project
ai-eng install .
ai-eng doctor
```

`install` scaffolds the governance root, detects your stack, and mirrors skills to every configured IDE. `doctor` validates the installation, checks tooling, and reports anything that needs attention.

See [GETTING_STARTED.md](GETTING_STARTED.md) for the full tutorial.

## What You Get

### 47 Skills

Skills are slash commands that encode team workflows as repeatable, governed procedures. Each skill carries its own trigger patterns, validation gates, and output contracts.

| Group | Skills |
|-------|--------|
| Workflow | brainstorm, plan, dispatch, code, test, debug, verify, review, eval, schema |
| Delivery | commit, pr, release-gate, cleanup, market |
| Enterprise | security, governance, pipeline, docs, board-discover, board-sync, platform-audit |
| Teaching | explain, guide, write, slides, media, video-editing |
| Design | design, animation, canvas |
| SDLC | note, standup, sprint, postmortem, support, resolve-conflicts |
| Meta | create, learn, prompt, start, analyze-permissions, instinct, autopilot, run, constitution, skill-evolve |

### 10 Agents

Agents are role-based specialists that skills dispatch to. Each agent has a defined mandate, boundaries, and output contract.

| Agent | Role |
|-------|------|
| plan | Architecture, specs, decomposition |
| build | Code generation with quality gates |
| verify | Evidence-first verification (7 specialist lenses) |
| guard | Governance, compliance, policy enforcement |
| review | Narrative code review (9 specialist lenses) |
| explore | Deep codebase research and analysis |
| guide | Onboarding, teaching, knowledge transfer |
| simplify | Reduce complexity, refactor, extract |
| autopilot | Autonomous multi-spec execution |
| run-orchestrator | Source-driven backlog execution |

### 14 Runbooks

Self-contained Markdown automation contracts. Each runbook carries its own purpose, cadence, hierarchy rules, and expected outputs. All are human-in-the-loop: they prepare work items but never touch code.

| Cadence | Runbooks |
|---------|----------|
| Daily | triage, refine, feature-scanner, stale-issues |
| Weekly | dependency-health, code-quality, security-scan, docs-freshness, performance, governance-drift, architecture-drift, work-item-audit, consolidate, wiring-scanner |

### Contexts

14 language contexts (bash, C++, C#, Dart, Go, Java, JavaScript, Kotlin, PHP, Python, Rust, SQL, Swift, TypeScript) and 15 framework contexts (Android, API Design, ASP.NET Core, Backend Patterns, Bun, Claude API, Deployment Patterns, Django, Flutter, iOS, MCP SDK, Next.js, Node.js, React, React Native) ship with the framework. These are loaded at session start based on your project's detected stack and applied to all code generation and review.

### Quality Gates

Enforced on every commit, not just in CI.

| Gate | Threshold |
|------|-----------|
| Test coverage | >= 80% |
| Code duplication | <= 3% |
| Cyclomatic complexity | <= 10 per function |
| Cognitive complexity | <= 15 per function |
| Blocker/critical issues | 0 |
| Security findings (medium+) | 0 |
| Secret leaks | 0 |
| Dependency vulnerabilities | 0 |

Tooling: `ruff` + `ty` (lint/format), `pytest` (test), `gitleaks` (secrets), `pip-audit` (deps).

## How It Works

`ai-eng install .` creates a governance root alongside IDE-specific mirrors:

```text
your-project/
├── .ai-engineering/          # governance root
│   ├── contexts/             # language, framework, and team context
│   ├── runbooks/             # automation contracts
│   ├── runs/                 # autonomous execution state
│   ├── scripts/              # hooks and helpers
│   ├── specs/                # active spec and plan
│   ├── state/                # decisions, events, capabilities
│   └── LESSONS.md            # persistent learning across sessions
├── .claude/                  # Claude Code skills + agents (canonical)
├── .codex/                   # OpenAI Codex mirror
├── .gemini/                  # Gemini CLI mirror
├── .github/                  # GitHub Copilot mirror
├── AGENTS.md                 # Codex instruction file
├── CLAUDE.md                 # Claude Code instruction file
└── GEMINI.md                 # Gemini CLI instruction file
```

### Three ownership boundaries

| Boundary | What it covers | How it changes |
|----------|---------------|----------------|
| Framework-managed | Skills, agents, runbooks, gates | `ai-eng update` -- preview before apply |
| Team-managed | `contexts/team/**`, lessons, constitution | Your team edits directly |
| Project-managed | Specs, plans, decisions, work-item state | Generated during workflow execution |

### Multi-IDE mirroring

`.claude/` is the canonical surface. Running `ai-eng sync` regenerates all other IDE mirrors (`.codex/`, `.gemini/`, `.github/`) from the canonical source. One set of skills, consistent behavior across all four IDEs.

## CLI Commands

| Command | Purpose |
|---------|---------|
| `ai-eng install [TARGET]` | Scaffold governance into a project |
| `ai-eng update [TARGET]` | Preview and apply framework updates |
| `ai-eng doctor [TARGET]` | Validate installation and tooling |
| `ai-eng validate [TARGET]` | Check manifest and structural integrity |
| `ai-eng verify [TARGET]` | Run verification checks |
| `ai-eng sync` | Regenerate IDE mirrors from canonical source |
| `ai-eng spec verify\|list\|catalog\|compact` | Manage specs |
| `ai-eng decision record\|list\|expire-check` | Track architectural decisions |
| `ai-eng release <VERSION>` | Cut a release |
| `ai-eng version` | Print current version |
| `ai-eng gate pre-commit\|commit-msg\|pre-push\|risk-check\|all` | Run quality gates |
| `ai-eng stack add\|remove\|list` | Manage project stacks |
| `ai-eng ide add\|remove\|list` | Manage IDE configurations |
| `ai-eng provider add\|remove\|list` | Manage AI provider mirrors |
| `ai-eng workflow commit\|pr\|pr-only` | Delivery workflows |
| `ai-eng maintenance report\|pr\|all` | Repository maintenance |
| `ai-eng setup platforms\|github\|sonar` | Platform onboarding |
| `ai-eng work-item sync` | Sync work items with board |
| `ai-eng skill status` | Show skill installation status |
| `ai-eng vcs status\|set-primary` | Version control configuration |
| `ai-eng guide` | Interactive onboarding |

## Slash Commands

Skills are invoked as slash commands inside your IDE. The two primary flows:

### Spec-driven flow

The default path for planned work:

```text
/ai-brainstorm  -->  /ai-plan  -->  /ai-dispatch  -->  /ai-verify  -->  /ai-pr
   (spec)           (plan)        (execute)          (evidence)       (ship)
```

### Backlog-driven flow

Autonomous execution against a work-item backlog:

```text
/ai-run  -->  intake  -->  explore  -->  waves  -->  /ai-pr
 (start)    (filter)    (context)    (execute)     (ship)
```

### Key commands

| Command | What it does |
|---------|-------------|
| `/ai-brainstorm` | Define requirements as a structured spec |
| `/ai-plan` | Decompose a spec into executable tasks |
| `/ai-dispatch` | Execute one approved plan |
| `/ai-autopilot` | Execute a multi-spec DAG autonomously |
| `/ai-run` | Execute a source-driven backlog run |
| `/ai-review` | Architecture-aware code review (9 specialist lenses) |
| `/ai-verify` | Evidence-backed verification (7 specialist lenses) |
| `/ai-pr` | Open, watch, and merge the pull request |

## Standing on the shoulders of...

ai-engineering builds on ideas, patterns, and principles from these projects:

| Project | What we learned |
|---------|----------------|
| [Superpowers](https://github.com/NicolasMontworker/superpowers) | Brainstorm hard-gate, TDD-for-skills patterns |
| [review-code](https://github.com/peterknights1/review-code) | Handler-as-workflow architecture, parallel specialist agents, finding-validator |
| [dotfiles/ai](https://github.com/ericbuess/dotfiles) | Agent matrix, SDLC coverage patterns |
| [autoresearch](https://github.com/vgel/autoresearch) | Radical simplicity as a design principle |
| [Emil Kowalski](https://emilkowal.ski) | Motion principles, spring physics, easing strategy |
| [SpecKit](https://github.com/speckit/speckit) | Spec-driven workflow inspiration |
| [GSD](https://github.com/jlowin/gsd) | Autonomous execution patterns |
| [Anthropic Skills](https://github.com/anthropics/claude-code-skills) | Frontend-design, canvas, skill-creator -- absorbed and extended |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, testing, and pull request guidelines.

## Code of conduct

This project follows the Contributor Covenant Code of Conduct. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

MIT. See [LICENSE](LICENSE).
