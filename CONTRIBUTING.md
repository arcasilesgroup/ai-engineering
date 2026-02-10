# Contributing to ai-engineering

Thank you for your interest in contributing. This guide covers everything you need to get started — from setting up a development environment to submitting a pull request.

## Development setup

Clone the repository and install the project with development dependencies:

```bash
git clone https://github.com/arcasilesgroup/ai-engineering.git
cd ai-engineering
```

With `uv` (recommended):

```bash
uv sync --all-extras
```

With `pip`:

```bash
pip install -e ".[dev]"
```

Verify the installation:

```bash
ai-eng version
```

## Code style

This project uses strict automated tooling. All checks run locally through git hooks — you don't need to remember them manually.

**Formatting and linting** — `ruff` with a 100-character line length:

```bash
ruff format src/ tests/
ruff check src/ tests/ --fix
```

**Type checking** — `ty`:

```bash
ty check src/
```

**Docstrings** — Google-style on all public functions and classes.

**Type hints** — required on all public APIs. Use `from __future__ import annotations` at the top of every module.

**Imports** — sorted by `ruff` with `isort` rules. First-party package: `ai_engineering`.

## Testing

Run the full test suite with:

```bash
pytest
```

This automatically runs with verbose output and coverage reporting (configured in `pyproject.toml`).

**Test conventions**:

- Follow the AAA pattern (Arrange, Act, Assert).
- Name tests as `test_<unit>_<scenario>_<expected_outcome>`.
- Use `tmp_path` for any filesystem operations.
- Aim for ≥ 80% coverage (≥ 90% for governance-critical modules).
- Tests live in `tests/` with `unit/`, `integration/`, and `e2e/` subdirectories.

Run a specific test file:

```bash
pytest tests/unit/test_installer.py
```

## Pull request process

1. Create a feature branch from `main`:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes. Git hooks enforce quality gates automatically:
   - **Pre-commit** — formatting (`ruff format`), linting (`ruff check`), secret scanning (`gitleaks`).
   - **Commit-msg** — validates the commit message format.
   - **Pre-push** — static analysis (`semgrep`), dependency audit (`pip-audit`), tests (`pytest`), type-check (`ty`).

3. Push your branch and open a pull request against `main`.

4. Include a clear description of what you changed and why. Reference any related issues.

5. All PRs use squash merge with branch deletion.

**Commit message format** — use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): short description

Optional body explaining what and why.
```

Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

## Reporting issues

**Bug reports** — include the following:

- What you expected to happen.
- What actually happened.
- Steps to reproduce (minimal example preferred).
- Your environment: OS, Python version, ai-engineering version (`ai-eng version`).

**Feature requests** — describe the problem you want to solve and your proposed approach. Open an issue before starting significant work so we can discuss the design.

## Project structure

```
src/ai_engineering/
├── cli.py                # CLI entry point
├── cli_factory.py        # Typer app factory
├── paths.py              # Path resolution utilities
├── __version__.py        # Version string
├── cli_commands/         # Command groups (core, gate, maintenance, skills, stack_ide)
├── commands/             # Workflow building blocks (commit, PR, acho)
├── installer/            # Framework bootstrap and stack/IDE operations
├── updater/              # Ownership-safe framework updates
├── doctor/               # Diagnostics and remediation
├── hooks/                # Git hook generation and installation
├── policy/               # Quality gate execution
├── state/                # Pydantic models, JSON/NDJSON I/O, decision logic
├── git/                  # Shared git operations
├── pipeline/             # CI/CD compliance scanning and injection
├── skills/               # Remote skill source management
├── maintenance/          # Health reports and branch cleanup
├── detector/             # Tool readiness detection
└── templates/            # Bundled governance and IDE templates
```

## Code of conduct

This project follows the Contributor Covenant Code of Conduct. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for details.
