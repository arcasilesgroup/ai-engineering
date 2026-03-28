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

ai-engineering turns any repository into a governed AI workspace. The framework is content-first: policies, skills, agents, runbooks, specs, and state all live in versioned files inside the repo instead of behind a hosted control plane. The CLI installs the framework, keeps mirrors in sync, previews safe updates, and enforces quality/security gates before code leaves your machine.

It works with Claude Code, OpenAI Codex, Gemini CLI, and GitHub Copilot from the same repository.

[Install](#install) · [Quick start](#quick-start) · [How it works](#how-it-works) · [Runtime contracts](#runtime-contracts) · [Providers and mirrors](#providers-and-mirrors) · [Commands](#commands) · [Contributing](#contributing)

## Install

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
ai-eng install .
ai-eng doctor
```

Install with an explicit stack and provider set:

```bash
ai-eng install . --stack python --provider claude_code --provider codex
```

Your next governed workflow usually looks like this:

```text
/ai-brainstorm -> /ai-plan -> /ai-dispatch or /ai-autopilot -> /ai-verify -> /ai-pr
```

## How it works

ai-engineering installs a governance root plus provider-specific mirrors:

```text
your-project/
├── .ai-engineering/
│   ├── contexts/      # shared, language, framework, and team context
│   ├── runbooks/      # self-contained Markdown automation contracts
│   ├── scripts/       # hooks and helper scripts
│   ├── specs/         # active spec/plan plus autopilot child specs when needed
│   ├── state/         # decisions, events, ownership, capability catalog
│   └── ...            # reviews/, instincts/, notes/, learnings/, schemas/ as used
├── .claude/
├── .agents/
├── .github/
├── AGENTS.md
└── CLAUDE.md
```

Three ownership boundaries keep updates safe:

- Framework-managed: shipped by ai-engineering and refreshable through `ai-eng update`
- Team-managed: your local conventions under `contexts/team/**`
- Project-managed: active specs, plans, work-item state, and project identity

## What ships today

- 41 skills across the canonical framework surfaces
- 9 role-based agents
- Claude Code mirrors for all 41 skills and all 9 agents
- Codex/Gemini mirrors for all 41 skills and all 9 agents
- GitHub Copilot mirrors for 40 skills and all 9 agents
- `analyze-permissions` is intentionally Claude-only, so it is not mirrored to GitHub Copilot

The framework also installs local quality and security gates around tools such as `ruff`, `ty`, `pytest`, `gitleaks`, and `pip-audit`, plus telemetry and integrity validation under `.ai-engineering/state/`.

## Runtime contracts

### Runbooks

The framework ships 12 self-contained portable runbooks in `.ai-engineering/runbooks/*.md`. Each runbook is a single Markdown contract that carries its own purpose, provider scope, hierarchy rules, cadence, handoff rules, and expected outputs. There are no separate adapter files -- the runbook itself is the portable artifact that any host can execute directly.

All runbooks are human-in-the-loop (HITL): they prepare work items in the provider (triage, enrich, label, comment, move cards) but never touch code or write local `spec.md` / `plan.md`.

**Cadences:**

- **Daily** (4 runbooks): triage, refine, feature-scanner, stale-issues
- **Weekly** (8 runbooks): dependency-health, code-quality, security-scan, docs-freshness, performance, governance-drift, architecture-drift, wiring-scanner

**Supported hosts:** Codex App Automation, Claude scheduled tasks, GitHub Agents, Azure Foundry.

| Runbook | Cadence | Purpose |
|---------|---------|---------|
| triage | daily | Scan backlog, classify, prioritize, label for refinement |
| refine | daily | Gather context, draft acceptance criteria, mark `handoff:ai-eng` |
| feature-scanner | daily | Detect spec-vs-code gaps and uncovered acceptance criteria |
| stale-issues | daily | Label stale issues (14 d), auto-close (21 d) with grace period |
| dependency-health | weekly | Outdated versions, CVEs, license compliance |
| code-quality | weekly | Complexity hotspots, duplication, tech debt |
| security-scan | weekly | Secrets, OWASP/SAST patterns, compliance gaps |
| docs-freshness | weekly | Stale docs, coverage gaps, doc-vs-code drift |
| performance | weekly | Test slowdowns, build time increases, regressions |
| governance-drift | weekly | Mirror sync, quality gates, hook integrity, manifest consistency |
| architecture-drift | weekly | Solution-intent vs codebase deviations, layer violations |
| wiring-scanner | weekly | Disconnected code, orphaned modules, dead exports |

### Review

`/ai-review` is narrative, architecture-aware review.

- Default mode is `normal`
- `normal` still covers every specialist, but through 3 fixed macro-agents
- `--full` runs one agent per specialist
- Final output always reports by original specialist lens, not by macro-agent
- `finding-validator` challenges every emitted finding in both profiles

Current specialist roster:

- `security`
- `backend`
- `performance`
- `correctness`
- `testing`
- `compatibility`
- `architecture`
- `maintainability`
- `frontend`

### Verify

`/ai-verify` is evidence-first verification.

- `/ai-verify platform` is the aggregate pass
- Default mode is `normal`
- `normal` covers all 7 specialists through 2 fixed macro-agents
- `--full` runs one agent per specialist
- Output stays attributed by original specialist even when execution is grouped
- `verify` does not run a separate adversarial validator stage

Current specialist roster:

- `governance`
- `security`
- `architecture`
- `quality`
- `performance`
- `a11y`
- `feature`

### Update

`ai-eng update` is preview-first. The human preview now renders as a grouped tree instead of a flat list, so you can see what will be added, changed, protected, skipped, or left untouched before applying.

Typical preview shape:

```text
Update [PREVIEW]
Available
├── .claude/skills/ai-review/SKILL.md
└── .ai-engineering/runbooks/triage.md
Protected
└── .ai-engineering/contexts/team/lessons.md
Unchanged
└── AGENTS.md
```

The CLI also prints per-file reasons and next steps in the preview body. JSON output remains machine-friendly.

## Providers and mirrors

ai-engineering keeps the same workflow model across all supported coding assistants:

| Surface | What it contains |
|---------|------------------|
| `.claude/skills/` + `.claude/agents/` | Claude Code slash commands and agents |
| `.agents/skills/` + `.agents/agents/` | Codex and Gemini generic skill/agent surfaces |
| `.github/skills/` + `.github/agents/` | GitHub Copilot skills and custom agents |
| `AGENTS.md` + `CLAUDE.md` | shared instruction files for tools that read repo guidance directly |

When framework content changes, run:

```bash
ai-eng sync
```

That regenerates the mirrored provider files and keeps template/install surfaces aligned.

## Commands

```bash
ai-eng install [TARGET]
ai-eng update [TARGET]
ai-eng update [TARGET] --apply
ai-eng doctor [TARGET]
ai-eng validate [TARGET]
ai-eng sync
ai-eng spec verify|catalog|list|compact
ai-eng decision record "<TITLE>"
ai-eng release <VERSION>
ai-eng version
```

For slash-command workflows, the most common ones are:

```text
/ai-brainstorm   define the spec
/ai-plan         break it into executable work
/ai-dispatch     execute one approved plan
/ai-autopilot    execute a multi-spec DAG
/ai-review       human-quality review
/ai-verify       evidence-backed verification
/ai-pr           open, watch, and merge the PR
```

## Governance root

The installed `.ai-engineering/README.md` is the topology guide for consumers of the framework. It explains:

- which directories are seeded at install time
- which directories appear lazily as skills are used
- which paths are framework-managed, team-managed, or system-generated
- how runbooks, specs, reviews, instincts, notes, and learnings fit together

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, testing, and pull request guidelines.

## Code of conduct

This project follows the Contributor Covenant Code of Conduct. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

MIT. See [LICENSE](LICENSE).
