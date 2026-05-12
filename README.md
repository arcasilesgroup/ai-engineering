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

**AI governance that ships.** Turn any repository into a governed AI workspace: policies, skills, agents, runbooks, and specs as versioned files. No hosted control plane, no vendor lock-in. One canonical chain across Claude Code, GitHub Copilot, OpenAI Codex, Gemini CLI, and Antigravity.

## Install

**Prerequisites**: Python 3.11+ and Git.

```bash
# pipx (recommended)
pipx install ai-engineering

# uv
uv tool install ai-engineering

# pip (inside a venv)
python -m venv .venv && source .venv/bin/activate
pip install ai-engineering
```

Verify:

```bash
ai-eng version
```

Update later with `pipx upgrade ai-engineering` (or `uv tool upgrade` / `pip install --upgrade`), then `ai-eng update` in each project followed by `ai-eng doctor` to verify.

## Quick Start

```bash
cd your-project
ai-eng install .
ai-eng doctor
```

`install` scaffolds the governance root, detects your stack, mirrors skills to every configured IDE, and wires the secrets-gate. `doctor` validates the result.

See [docs/getting-started.md](docs/getting-started.md) for the 3-minute walkthrough from clone to merged PR.

**Telemetry** is strict-opt-in (default disabled). The audit chain is local NDJSON; external emitters require explicit operator opt-in via `.ai-engineering/manifest.yml > telemetry.*`.

### Optional: Engram (third-party memory)

`ai-engineering` ships **without** a built-in memory layer. Engram is no longer wired into the installer (spec-132 D-132-06); install it separately if you want cross-session memory. See [docs/integrations/engram.md](docs/integrations/engram.md) for OS-specific install commands and the `engram setup claude_code` post-step.

## How AI Works Here

This framework defines a single canonical chain that every supported IDE follows identically. The full ruleset, principles, surface index, and chain definition live in:

- [AGENTS.md](AGENTS.md) — canonical "how AI works in this repo" payload (mirrored byte-equivalent into [CLAUDE.md](CLAUDE.md), [GEMINI.md](GEMINI.md), and [.github/copilot-instructions.md](.github/copilot-instructions.md))
- [CONSTITUTION.md](CONSTITUTION.md) — project identity (mission, stakeholders, vocabulary, prohibitions, compliance gates)
- [CHANGELOG.md](CHANGELOG.md) — version history and breaking-change reference

The skill catalogue, agent roster, runbook list, quality-gate thresholds, and CLI command reference all live in [AGENTS.md](AGENTS.md) (canonical) and [docs/cli-reference.md](docs/cli-reference.md). They are not duplicated here.

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
| [Anthropic Skills](https://github.com/anthropics/claude-code-skills) | Frontend-design, canvas, skill-creator — absorbed and extended |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, testing, and the pull request process.

## Code of conduct

This project follows the Contributor Covenant Code of Conduct. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

MIT. See [LICENSE](LICENSE).
