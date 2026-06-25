<div align="center">
  <a href="https://github.com/arcasilesgroup/ai-engineering">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/banner-dark.svg">
      <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/banner-light.svg">
      <img src="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/banner-light.svg" alt="{ai} engineering" width="720">
    </picture>
  </a>

  <p><strong>Turn AI-assisted delivery into a governed local workflow — in any repo, any IDE.</strong></p>

  <p>
    <a href="https://pypi.org/project/ai-engineering/"><img src="https://img.shields.io/pypi/v/ai-engineering.svg?style=flat-square&color=00D4AA&labelColor=0B1120" alt="PyPI version"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.11%2B-00D4AA.svg?style=flat-square&labelColor=0B1120" alt="Python 3.11+"></a>
    <a href="https://github.com/arcasilesgroup/ai-engineering/actions"><img src="https://img.shields.io/github/actions/workflow/status/arcasilesgroup/ai-engineering/ci-check.yml?branch=main&style=flat-square&labelColor=0B1120" alt="CI"></a>
    <a href="https://sonarcloud.io/summary/overall?id=arcasilesgroup_ai-engineering"><img src="https://img.shields.io/sonar/quality_gate/arcasilesgroup_ai-engineering?server=https%3A%2F%2Fsonarcloud.io&style=flat-square&labelColor=0B1120&color=00D4AA" alt="Quality Gate"></a>
    <a href="https://sonarcloud.io/summary/overall?id=arcasilesgroup_ai-engineering"><img src="https://img.shields.io/sonar/coverage/arcasilesgroup_ai-engineering?server=https%3A%2F%2Fsonarcloud.io&style=flat-square&labelColor=0B1120&color=00D4AA" alt="Coverage"></a>
    <a href="https://snyk.io/test/github/arcasilesgroup/ai-engineering"><img src="https://img.shields.io/badge/Snyk-monitored-00D4AA?style=flat-square&labelColor=0B1120" alt="Snyk security"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-00D4AA.svg?style=flat-square&labelColor=0B1120" alt="License: MIT"></a>
  </p>

  <p><code>54 skills · 9 agents · 6 surfaces · 1 governed flow</code></p>

  <img src="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/demo.gif" alt="Terminal demo: uv tool install ai-engineering, then ai-eng install . and ai-eng doctor both report [PASS], then open your IDE and run /ai-start" width="760">
</div>

`{ai} engineering` installs a deterministic governance layer into any repository — specs, decisions, skills, agents, hooks, and an audit trail, all as versioned local files. No hosted control plane. No provider lock-in. Every IDE follows the same rules.

## Quickstart

Get a governed repo in under a minute — `{ai} engineering` is uv-first:

```bash
uv tool install ai-engineering   # install the CLI
ai-eng install .                 # add governance to your repo
ai-eng doctor                    # [PASS] hooks, mirrors, manifest, required tools
```

<details>
<summary>Prefer <code>pip</code> or <code>pipx</code>?</summary>

```bash
pipx install ai-engineering
# or
python -m pip install --user ai-engineering
```

</details>

Then open your editor and type `/ai-start`. Prefer to ease in? Start in observe mode and enforce only what proves useful.

**What you get:** 54 skills and 9 agents you invoke with `/ai-<name>` · a spec-driven workflow · automatic checks on every change · versioned local files you own. Update any time with `ai-eng update`.

## The governed workflow

You drive the intent and approve each step; the gates catch the rest — no secrets, broken docs, or untested changes reach a merge.

<div align="center">
  <img src="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/diagrams/workflow.png" alt="The governed workflow: /ai-brainstorm agrees the spec, /ai-plan breaks it down, /ai-build or /ai-autopilot implements it, /ai-pr ships a reviewed and merged pull request. You approve each step; automatic checks (clean diff, tests, docs, review) must pass before merge." width="820">
</div>

The canonical chain is **`/ai-brainstorm → /ai-plan → /ai-build → /ai-pr`**. Use it whenever work changes product behavior, framework behavior, security posture, public docs, or release state. `/ai-commit` stays available for WIP checkpoints; it is not part of the chain.

## Your toolkit

Fifty-four skills and nine agents cover the whole delivery loop — and the same commands work in every supported editor.

<div align="center">
  <img src="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/diagrams/toolkit.png" alt="54 skills and 9 agents grouped by what you do: plan and build, ship safely, design and docs, research and learn. The same commands run in Claude Code, GitHub Copilot, Codex, Antigravity, OpenCode, and Cursor." width="820">
</div>

Need evidence? `/ai-research` returns cited findings from local context, the web, and async deep research. And because plans carry ready-to-apply patches, mechanical work routes to a smaller model — routine edits stay cheap.

## Supported surfaces

One canonical payload is mirrored, byte-for-byte, into every enabled surface.

| Surface | Entry point |
|---------|-------------|
| Claude Code | [CLAUDE.md](CLAUDE.md) |
| GitHub Copilot | [.github/copilot-instructions.md](.github/copilot-instructions.md) |
| OpenAI Codex | [AGENTS.md](AGENTS.md) |
| Antigravity | [AGENTS.md](AGENTS.md) + `.agents/` |
| OpenCode | `.opencode/` |
| Cursor | `.cursor/` |

The ruleset lives in [AGENTS.md](AGENTS.md). Project identity and hard prohibitions live in [CONSTITUTION.md](CONSTITUTION.md). Release history lives in [CHANGELOG.md](CHANGELOG.md).

## Highlights

- **Ship a whole spec in one run** — `/ai-autopilot` decomposes it, builds a dependency DAG, runs parallel waves, and converges on a reviewed PR.
- **What you approved is what shipped** — a brainstorm hard-gate plus a spec-lifecycle state machine keep every change anchored to the approved spec (Rung 2 SDD — spec and code stay in sync, not just spec-first that drifts).
- **An audit trail you own** — every AI action lands in a hash-chained NDJSON log you can verify offline, with no telemetry by default.
- **Every bypass has an owner and an expiry** — no `# noqa` or `@ts-ignore`; findings are refactored or formally risk-accepted with a severity-based TTL.
- **Every tool call is screened before it runs** — a deterministic guard checks each edit, write, and shell command and stops risky ones.
- **AI quality is a tested property** — skills are measured with pass@k, and a regression beyond five points blocks the pull request.

## Documentation

- [docs/](docs/) — architecture, getting started, and the diagram set
- [CONSTITUTION.md](CONSTITUTION.md) — mission, stakeholders, prohibitions
- [CHANGELOG.md](CHANGELOG.md) — release history and breakage notes

## Standing on the shoulders of

`{ai} engineering` builds on ideas and patterns from these projects:

| Project | What we learned |
|---------|----------------|
| [Superpowers](https://github.com/NicolasMontworker/superpowers) | Brainstorm hard-gate, TDD-for-skills patterns |
| [review-code](https://github.com/peterknights1/review-code) | Handler-as-workflow, parallel specialist agents |
| [dotfiles/ai](https://github.com/ericbuess/dotfiles) | Agent matrix, SDLC coverage |
| [autoresearch](https://github.com/vgel/autoresearch) | Radical simplicity as a design principle |
| [SpecKit](https://github.com/speckit/speckit) | Spec-driven workflow inspiration |
| [Anthropic Skills](https://github.com/anthropics/claude-code-skills) | Frontend-design, skill-creator — absorbed and extended |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, testing, and the pull request process. This project follows the Contributor Covenant [Code of Conduct](CODE_OF_CONDUCT.md).

## License

MIT. See [LICENSE](LICENSE).

## Star history

<div align="center">
  <a href="https://star-history.com/#arcasilesgroup/ai-engineering&Date">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=arcasilesgroup/ai-engineering&type=Date&theme=dark">
      <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=arcasilesgroup/ai-engineering&type=Date">
      <img src="https://api.star-history.com/svg?repos=arcasilesgroup/ai-engineering&type=Date" alt="Star history chart for arcasilesgroup/ai-engineering" width="640">
    </picture>
  </a>
</div>

## Contributors

<div align="center">
  <a href="https://github.com/arcasilesgroup/ai-engineering/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=arcasilesgroup/ai-engineering" alt="ai-engineering contributors">
  </a>
</div>

Made with [contrib.rocks](https://contrib.rocks).
