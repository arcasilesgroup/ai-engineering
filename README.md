# ai-engineering

Open-source AI governance framework for secure, practical software delivery.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

ai-engineering gives your repository a complete governance layer — quality gates, security scanning, risk lifecycle management, and AI-agent guidance — installed with a single command. It works locally through git hooks so every commit is checked before it leaves your machine.

## Features

**Governance bootstrap** — Run `ai-eng install` to scaffold a `.ai-engineering/` governance root in any project. The framework creates standards, state files, and git hooks in one step.

**Automatic quality gates** — Git hooks run `ruff`, `ty`, `gitleaks`, `semgrep`, `pip-audit`, and `pytest` at the right stage (pre-commit, commit-msg, pre-push). No CI dependency for basic quality.

**Risk acceptance lifecycle** — Accept, renew, resolve, and revoke security risks with severity-based expiry. Expired risks block pushes until you remediate or renew.

**Stack and IDE management** — Add technology stacks (e.g. `python`) and IDE integrations (e.g. `vscode`) to generate tailored instruction templates for AI coding agents.

**Framework updates** — Update framework-managed files without touching your team or project content. Dry-run by default so you can review before applying.

**Doctor diagnostics** — Diagnose framework health: validates layout, state integrity, git hooks, and tool availability. Auto-fix hooks and install missing tools.

**Maintenance and reporting** — Generate health reports, clean stale branches, check risk status, and scan CI/CD pipelines for risk governance gates.

**Remote skills** — Sync curated skill libraries from trusted sources with checksum verification and offline fallback.

## Quick start

### Prerequisites

- Python 3.11 or later
- `uv` (recommended) or `pip`
- Git

### Installation

```bash
pip install ai-engineering
```

Or with `uv`:

```bash
uv pip install ai-engineering
```

### First use

Bootstrap governance in your project:

```bash
cd your-project
ai-eng install .
```

This creates the `.ai-engineering/` governance root, installs git hooks, and generates state files. Your next commit automatically runs quality gates.

To install with a specific technology stack and IDE:

```bash
ai-eng install . --stack python --ide vscode
```

Verify the installation:

```bash
ai-eng doctor
```

## Usage

### Core commands

```bash
ai-eng install [TARGET]          # Bootstrap governance framework
ai-eng update [TARGET]           # Preview framework file updates (dry-run)
ai-eng update [TARGET] --apply   # Apply framework file updates
ai-eng doctor [TARGET]           # Diagnose framework health
ai-eng doctor --fix-hooks        # Reinstall git hooks
ai-eng doctor --fix-tools        # Install missing tools
ai-eng version                   # Show installed version
```

### Stack and IDE management

```bash
ai-eng stack add python          # Add a technology stack
ai-eng stack remove python       # Remove a technology stack
ai-eng stack list                # List active stacks

ai-eng ide add vscode            # Add IDE integration
ai-eng ide remove vscode         # Remove IDE integration
ai-eng ide list                  # List active IDEs
```

### Quality gates

Git hooks invoke these automatically, but you can run them manually:

```bash
ai-eng gate pre-commit           # Format, lint, gitleaks
ai-eng gate commit-msg .git/COMMIT_EDITMSG  # Commit message validation
ai-eng gate pre-push             # Semgrep, pip-audit, tests, type-check
ai-eng gate risk-check           # Check risk acceptance status
ai-eng gate risk-check --strict  # Fail on expiring risks too
```

### Skills management

```bash
ai-eng skill list                # List remote skill sources
ai-eng skill sync                # Sync from remote sources
ai-eng skill sync --offline      # Use cached content only
ai-eng skill add <url>           # Add a remote skill source
ai-eng skill remove <url>        # Remove a remote skill source
```

### Maintenance

```bash
ai-eng maintenance report                  # Generate health report
ai-eng maintenance pr                      # Generate report + create PR
ai-eng maintenance branch-cleanup          # Clean merged local branches
ai-eng maintenance branch-cleanup --dry-run  # Preview without deleting
ai-eng maintenance risk-status             # Show risk acceptance status
ai-eng maintenance pipeline-compliance     # Scan pipelines for risk gates
```

## Configuration

ai-engineering uses a content-first approach — configuration lives in the `.ai-engineering/` directory as Markdown, YAML, and JSON files.

**At install time**, you control which stacks and IDEs to enable via `--stack` and `--ide` flags. You can add or remove them later with `ai-eng stack` and `ai-eng ide` commands.

**Updates** are dry-run by default. Run `ai-eng update` to preview changes, then `ai-eng update --apply` to write them. The updater only touches framework-managed files — your team and project content is never overwritten.

**Doctor remediation** gives you `--fix-hooks` to reinstall git hooks and `--fix-tools` to auto-install missing Python tools (`ruff`, `ty`, `gitleaks`, `semgrep`, `pip-audit`).

**Risk lifecycle** supports severity-based expiry:

- `critical` — 15 days
- `high` — 30 days
- `medium` — 60 days
- `low` — 90 days

Expired risks block `git push` until you remediate or renew them (max 2 renewals).

## Architecture

ai-engineering is a **content framework with a minimal CLI**. The governance layer is Markdown, YAML, and JSON documents in `.ai-engineering/`. The Python CLI (`ai-eng`) handles lifecycle operations only — install, update, doctor, and gate enforcement.

```
your-project/
├── .ai-engineering/         # Governance root
│   ├── standards/           # Framework and team standards
│   ├── context/             # Product contracts, specs, learnings
│   ├── skills/              # Procedural skill definitions
│   ├── agents/              # Agent persona definitions
│   └── state/               # Runtime state (JSON/NDJSON)
├── .git/hooks/              # Installed quality gate hooks
└── ...your code
```

**Ownership model** — three clear boundaries:

- **Framework-managed** (`standards/framework/`) — updated by `ai-eng update`, never edit manually.
- **Team-managed** (`standards/team/`) — owned by your team, never overwritten by updates.
- **Project-managed** (`context/`) — living documents you maintain during active work.

**Enforcement** happens locally through git hooks. Pre-commit runs formatting and linting. Commit-msg validates message format. Pre-push runs security scans, dependency audits, tests, and type-checking. No CI pipeline required for baseline quality.

## Tooling baseline

| Tool | Purpose |
|---|---|
| `uv` | Package and runtime management |
| `ruff` | Linting and formatting |
| `ty` | Type checking |
| `pip-audit` | Dependency vulnerability scanning |
| `gitleaks` | Secret detection |
| `semgrep` | Static analysis |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, testing, and pull request guidelines.

## Code of conduct

This project follows the Contributor Covenant Code of Conduct. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE)
