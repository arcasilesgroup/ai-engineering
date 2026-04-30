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

**48 skills. 10 agents. 4 IDEs. One governed workflow.**

AI governance that developers actually want -- for teams that ship.

ai-engineering turns any repository into a governed AI workspace. Governance is content-first: policies, skills, agents, runbooks, and specs all live as versioned files inside the repo -- no hosted control plane, no vendor lock-in. It works across Claude Code, GitHub Copilot, OpenAI Codex, and Gemini CLI from the same repository.

[Install](#install) · [Quick Start](#quick-start) · [What's new in 0.5.0](#whats-new-in-050) · [What You Get](#what-you-get) · [How It Works](#how-it-works) · [CLI](#cli-commands) · [Slash Commands](#slash-commands) · [Inspirations](#standing-on-the-shoulders-of) · [Contributing](#contributing)

## Install

**Prerequisites**: Python 3.11+ and Git.

### Recommended: pipx (isolated, global)

```bash
pipx install ai-engineering
```

### Alternative: uv

```bash
uv tool install ai-engineering
```

### Fallback: pip (requires a virtual environment)

```bash
python -m venv .venv && source .venv/bin/activate
pip install ai-engineering
```

### Verify

```bash
ai-eng version
```

### Update to latest version

```bash
# pipx
pipx upgrade ai-engineering

# uv
uv tool upgrade ai-engineering

# pip
pip install --upgrade ai-engineering
```

After upgrading, run `ai-eng update` in each project to pull the latest skills, contexts, and runbooks, then `ai-eng doctor` to verify.

## Quick Start

```bash
cd your-project
ai-eng install .
ai-eng doctor
```

`install` scaffolds the governance root, detects your stack, and mirrors skills to every configured IDE. It also auto-installs missing tools (`ruff`, `gitleaks`, `ty`, `pip-audit`) via your OS package manager. `doctor` validates the installation, checks tooling, and reports anything that needs attention.

See [GETTING_STARTED.md](GETTING_STARTED.md) for the full tutorial.

## What's new in 0.5.0

> **Upgrading from 0.4.x?** Walk through this section once. New installs can skip ahead to [What You Get](#what-you-get) — the defaults are already right.

Highlights:

- **Installer is a hard contract.** `ai-eng install` and `ai-eng doctor --fix --phase tools` exit `EXIT 80` (missing tool) or `EXIT 81` (missing language SDK) instead of silently passing.
- **`ai-eng install` auto-heals.** A second-pass remediation runs automatically; opt out with `--no-auto-remediate`.
- **Live progress UI.** Replaces the single spinner with `[N/M] phase_label`.
- **Python tooling is worktree-fast.** `python_env.mode` defaults to `uv-tool` (tools live once in `~/.local/share/uv/tools/`). Two escape hatches remain: `venv` (legacy per-cwd) and `shared-parent` (single `.venv` shared across worktrees).
- **Single-pass local gate.** Wave-1 fixers then Wave-2 checkers in parallel, with a 24h SHA-256 cache. ~2-3x faster on warm checkouts. Try `ai-eng gate run --cache-aware --json`.
- **First-class risk acceptance.** New `ai-eng risk accept | accept-all | renew | resolve | revoke | list | show` namespace. No more hand-edited `decision-store.json`.
- **`gates > mode: prototyping`.** Skip Tier 2 governance for spike work. CI auto-detects and forces `regulated`.
- **Copilot agent rename.** `@Explorer` is now `@ai-explore`, matching Claude / Codex / Gemini.

For the full list, including decision IDs, schema deltas, and per-spec rationale, see [CHANGELOG.md](CHANGELOG.md).

### Quick upgrade path

```bash
pipx upgrade ai-engineering          # or: uv tool upgrade ai-engineering
ai-eng install .                     # in each project
ai-eng doctor                        # verify
```

If your team relies on `source .venv/bin/activate`, set `python_env > mode: venv` in `.ai-engineering/manifest.yml` *before* the second step.

The first install after upgrading prints a one-shot BREAKING banner to stderr, recorded once via `breaking_banner_seen` in `.ai-engineering/state/install-state.json`.

## Upgrade reference -- spec-101 install contract (BREAKING)

### EXIT 80 / EXIT 81 -- hard fail on missing tooling

Two reserved exit codes replace the previous best-effort silent pass:

| Code | Meaning |
|------|---------|
| `EXIT 80` | A required CLI tool is missing or unverifiable after install. Examples: `ruff`, `ty`, `gitleaks`, `pip-audit`, `prettier`, `eslint`, `vitest`, `staticcheck`, `phpstan`, `cargo-audit`, `ktlint`, `swiftlint`, `sqlfluff`, `shellcheck`, `clang-tidy`. |
| `EXIT 81` | A language SDK / prerequisite from `prereqs.sdk_per_stack` is missing. Examples: JDK, Swift toolchain, Dart SDK, .NET SDK, Go toolchain, Rust toolchain, PHP, clang/LLVM. |

**Migration**: remove any `ai-eng install || true` shielding from your CI scripts. The framework now surfaces failures explicitly so you can fix them, not paper over them. If a tool is genuinely unsupported on a host OS, declare it via `platform_unsupported` (tool-level, max 2 of 3 OSes) or escalate via `platform_unsupported_stack` (stack-level, may list all 3) -- both require a non-empty `unsupported_reason` (D-101-03 + D-101-13). See `.ai-engineering/manifest.yml > required_tools` for working examples.

### `platform_unsupported` -- tool vs stack scope

Two governance keys control where unsupported markers may appear:

- `platform_unsupported` lives **on a single tool** inside a stack's tool list. Caps at 2 of 3 OSes; using it for all 3 is rejected by the model validator. Example: `semgrep` carries `platform_unsupported: [windows]`.
- `platform_unsupported_stack` lives **on the entire stack block** when the whole toolchain has no native binaries on a given OS. May list all 3 OSes. Example: the `swift` stack carries `platform_unsupported_stack: [linux, windows]` because `swiftlint` and `swift-format` ship for macOS only.

Both keys require an `unsupported_reason` field; the lint refuses an unreasoned escalation.

### `python_env.mode` decision tree

`python_env.mode` defaults to `uv-tool`. Three values exist:

```
                       ┌──────────────────────────────────┐
Need a fresh worktree  │  uv-tool   (default, recommended)│
to be fast (< 30 s)?   │   tools install once into        │
                       │   ~/.local/share/uv/tools/       │
                       └──────────────────────────────────┘
                                       │
                                       ▼
                Need .venv/ for legacy   ┌──────────────────────────┐
                workflows                │  venv                    │
                (source .venv/bin/...)?  │   per-cwd .venv/         │
                                         │   classic, slow worktree │
                                         └──────────────────────────┘
                                       │
                                       ▼
                Want a single .venv      ┌──────────────────────────┐
                shared across worktrees  │  shared-parent           │
                (requires git repo)?     │   .venv at repo root,    │
                                         │   linked from worktrees  │
                                         └──────────────────────────┘
```

Set the value in `.ai-engineering/manifest.yml`:

```yaml
python_env:
  mode: uv-tool   # or: venv | shared-parent
```

A full reference (`.ai-engineering/contexts/python-env-modes.md`) covers migration commands and trade-offs.

### 14 stacks covered by `required_tools`

A single `manifest.yml > required_tools` block drives both `ai-eng install` and `ai-eng doctor --fix`. The 14 supported stacks are:

| # | Stack | Representative tools |
|---|-------|----------------------|
| 1 | python | ruff, ty, pip-audit, pytest |
| 2 | typescript | prettier, eslint, tsc, vitest |
| 3 | javascript | prettier, eslint, vitest |
| 4 | java | checkstyle, google-java-format |
| 5 | csharp | dotnet-format |
| 6 | go | staticcheck, govulncheck |
| 7 | php | phpstan, php-cs-fixer, composer |
| 8 | rust | cargo-audit |
| 9 | kotlin | ktlint |
| 10 | swift | swiftlint, swift-format (macOS only) |
| 11 | dart | dart-stack-marker |
| 12 | sql | sqlfluff |
| 13 | bash | shellcheck, shfmt |
| 14 | cpp | clang-tidy, clang-format, cppcheck |

Plus a universal `baseline` block (`gitleaks`, `semgrep`, `jq`) that applies to every stack.

### First-run banner

The first install after upgrading prints a one-shot BREAKING banner to stderr. The banner mentions EXIT 80/81, the `python_env.mode` flip, and the 14-stack scope. It only fires once per project -- the flag persists in `.ai-engineering/state/install-state.json` (`breaking_banner_seen`).

## What You Get

### 48 Skills

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

Release discipline: do not bump framework versions by hand across files. Use `ai-eng release <VERSION>`
as the single operational entry point. The release workflow updates the package version in
`pyproject.toml`, syncs the bundled version registry and source-repo `framework_version` manifests,
promotes `CHANGELOG.md`, and records release metadata in install state.

## Slash Commands

Skills are invoked as slash commands inside your IDE. The two primary flows:

### Spec-driven flow

The default path for planned work after install and health-check:

```text
/ai-start  -->  /ai-brainstorm  -->  /ai-plan  -->  /ai-dispatch  -->  /ai-verify  -->  /ai-pr
  (start)       (spec)              (plan)        (execute)          (evidence)       (ship)
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
| `/ai-start` | Bootstrap the session with context, dashboard, and active work |
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
