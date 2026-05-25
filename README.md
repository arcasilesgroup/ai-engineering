<div align="center">
  <a href="https://github.com/arcasilesgroup/ai-engineering">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/banner-dark.svg">
      <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/banner-light.svg">
      <img src="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/banner-light.svg" alt="ai-engineering — AI governance framework" width="700">
    </picture>
  </a>

  <p><strong>{ai} engineering turns AI-assisted delivery into a governed local workflow.</strong></p>

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

<div align="center">
  <picture>
    <source srcset="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/demo.webp" type="image/webp">
    <img src="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/demo.gif" alt="ai-eng install, then ai-eng doctor (warnings are advisory, non-blocking), then exploring the .ai-engineering tree plus 53 skills and 9 agents in VS Code, ending with /ai-start in Claude Code" width="900">
  </picture>
</div>

53 skills · 9 agents · 6 surfaces · 1 governed flow

{ai} engineering installs a deterministic governance layer into any repository: specs, decisions, skills, agents, runbooks, hooks, and audit trails as versioned local files. No hosted control plane. No provider lock-in. Every IDE follows the same rules.

## Install

### 1.1 — Prerequisites

Python 3.11+ and Git.

### 1.2 — Install ai-engineering

1. If you use `uv`, install the published PyPI release as a managed tool:

```bash
uv tool install --force ai-engineering
uv tool update-shell
exec "$SHELL" -l
```

2. If you do not use `uv`, install with `pipx`:

```bash
pipx install ai-engineering
```

3. If you do not use `uv` or `pipx`, install with `pip`:

```bash
python -m pip install --user ai-engineering
```

If `ai-eng` is not available after the `pip` install, add Python's user scripts directory to your `PATH`, then reopen your shell.

4. Verify the CLI:

```bash
ai-eng version
```

5. Install governance into a repository:

```bash
cd your-project
ai-eng install .
ai-eng doctor
```

[PASS] `doctor` confirms hooks, mirrors, manifest defaults, and required tools.

To update later from PyPI:

1. Upgrade the installed CLI with the command that matches your install method:

```bash
uv tool upgrade ai-engineering
# or
pipx upgrade ai-engineering
# or
python -m pip install --user --upgrade ai-engineering
```

These commands fetch the latest published `ai-engineering` release from PyPI.

2. Verify that the new version is available:

```bash
ai-eng version
```

3. In each governed project, refresh the installed framework files:

```bash
cd your-project
ai-eng update
ai-eng doctor
```

## Governed Flow

The canonical chain is:

```text
/ai-brainstorm → /ai-plan → /ai-build → /ai-pr
```

Use it when work changes product behavior, framework behavior, security posture, public docs, or release state. `/ai-commit` remains available for WIP checkpoints; it is not part of the canonical delivery chain.

## Supported Surfaces

One canonical payload is mirrored into all enabled surfaces:

| Surface | Entry point |
|---------|-------------|
| Claude Code | [CLAUDE.md](CLAUDE.md) |
| GitHub Copilot | [.github/copilot-instructions.md](.github/copilot-instructions.md) |
| OpenAI Codex | [AGENTS.md](AGENTS.md) |
| Antigravity | [AGENTS.md](AGENTS.md) + `.agents/` skills and agents |
| OpenCode | `.opencode/` skills and commands |
| Cursor | `.cursor/` skills |

The ruleset lives in [AGENTS.md](AGENTS.md). Project identity and hard prohibitions live in [CONSTITUTION.md](CONSTITUTION.md). Release history and breakage notes live in [CHANGELOG.md](CHANGELOG.md).

## Why Governance Matters

- Spec-driven work keeps LLM output tied to approved scope.
- Deterministic gates catch secrets, broken mirrors, missing docs, and policy drift.
- The local NDJSON audit chain records what happened without sending telemetry by default.
- Skills and agents are file-backed, reviewable, and synchronized across IDEs.

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
| [GSD](https://github.com/open-gsd/get-shit-done-redux) | Autonomous execution patterns |
| [Anthropic Skills](https://github.com/anthropics/claude-code-skills) | Frontend-design, canvas, skill-creator — absorbed and extended |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, testing, and the pull request process.

## Code of conduct

This project follows the Contributor Covenant Code of Conduct. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

MIT. See [LICENSE](LICENSE).
