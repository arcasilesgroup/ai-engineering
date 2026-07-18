# Contributing to ai-engineering

Thank you for contributing. This guide covers development setup through opening a pull request.

## Development setup

Clone the repository:

```bash
git clone https://github.com/arcasilesgroup/ai-engineering.git
cd ai-engineering
```

### With uv (recommended)

```bash
uv sync --all-extras
```

This creates a virtual environment and installs all dependencies automatically.

### With pip

Create and activate a virtual environment first:

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

Install in editable mode with dev dependencies:

```bash
pip install -e ".[dev]"
```

### Verify the installation

```bash
ai-eng version
```

Run the test suite and linter to confirm everything works:

```bash
pytest tests/unit/ -v
ruff check .
```

## Code style

Automated tooling runs locally through git hooks — you don't need to run these manually.

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

Run the full test suite in parallel (mirrors CI) with:

```bash
make test
```

Scoped targets: `make test-unit`, `make test-integration`, `make test-e2e`. These run `pytest -n auto --dist worksteal` via `pytest-xdist`. Bare `pytest` still works and runs serially — prefer it for focused, `--pdb`-friendly runs.

**Test conventions**:

- Follow the AAA pattern (Arrange, Act, Assert).
- Name tests as `test_<unit>_<scenario>_<expected_outcome>`.
- Use `tmp_path` for any filesystem operations.
- Aim for 100% coverage.
- Tests live in `tests/` with `unit/`, `integration/`, and `e2e/` subdirectories.

Run a specific test file:

```bash
pytest tests/unit/test_installer.py
```

Diagnose local skill requirements (tools/env/config/os):

```bash
ai-eng skill status --all
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

**Bug reports** — include expected vs. actual behaviour, minimal repro steps, and your environment (OS, Python version, `ai-eng version`).

**Feature requests** — describe the problem you want to solve and your proposed approach. Open an issue before starting significant work so we can discuss the design.

## Project structure

Top-level: `src/ai_engineering/` (CLI, installer, updater, doctor, hooks, policy, state, git, pipeline, skills, maintenance, detector, and bundled templates); `tests/` (unit, integration, e2e, architecture, conformance, perf, mirrors, adapters, docs); `.ai-engineering/` (governance root: reference, evals, runtime, scripts, specs, state, team); `.claude/` plus the `.github/`, `.codex/`, `.agents/`, `.opencode/` IDE mirrors (skills + agents); consumer-project templates bundled at `src/ai_engineering/templates/project/`; `scripts/` (sync utilities, mirror generation); `tools/` (linters, no-suppression gate); `docs/` (human-facing docs: getting started, architecture, persistence doctrine, CI and supply-chain references; framework reference content lives under `.ai-engineering/reference/`).

See [AGENTS.md](AGENTS.md) for the full architecture map and canonical chain.

## Code of conduct

This project follows the Contributor Covenant Code of Conduct. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for details.
