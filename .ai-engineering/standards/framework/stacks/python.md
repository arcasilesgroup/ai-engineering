# Framework Python Stack Standards

## Update Metadata

- Rationale: add Python version pinning and venv stability requirements for deterministic environment resolution.
- Expected gain: eliminates intermittent tool resolution failures caused by PATH and venv invalidation.
- Potential impact: `.python-version` becomes a required file; venv health is checked by `ai-eng doctor`.

## Stack Scope

- Primary language: Python 3.11+.
- Supporting formats: Markdown, YAML, JSON, Bash.
- Toolchain baseline: `uv`, `ruff`, `ty`.
- Distribution: PyPI wheel (`py3-none-any`).

## Required Tooling

- Package/runtime: `uv` (no direct pip usage).
- Lint/format: `ruff` (line-length 100).
- Type checking: `ty`.
- Dependency vulnerability scan: `pip-audit`.
- Security SAST: `semgrep` (OWASP-oriented), `gitleaks` (secret detection).

## Minimum Gate Set

- Pre-commit: `ruff format --check`, `ruff check`, `gitleaks`.
- Pre-push: `semgrep`, `pip-audit`, `pytest`, `ty check`.

## Quality Baseline

- Type hints required on all public APIs: `from __future__ import annotations`.
- Test coverage target: per `standards/framework/quality/core.md` (90% overall, 100% governance-critical).
- Line length: 100.
- Docstrings: Google-style on all public functions and classes.

## Python Version Pinning

- A `.python-version` file MUST exist at the repository root.
- Content: major.minor only (e.g., `3.12`), no patch version.
- `uv` reads this file to resolve the correct Python binary across all contexts (terminal, hooks, subprocesses).
- The pinned version must satisfy `pyproject.toml requires-python`.

## Venv Stability

- The project venv at `.venv/` is created via `uv venv --python <version>`.
- `ai-eng doctor` validates venv health by checking that `.venv/pyvenv.cfg` `home` path exists on disk.
- If the home path becomes stale (e.g., after `brew upgrade python`), `ai-eng doctor --fix-tools` recreates the venv.
- Prefer `uv python install <version>` for standalone Python (independent of system package manager) to avoid venv invalidation on system upgrades.

## Code Patterns

- **Pydantic for schemas**: all state models use Pydantic v2 `BaseModel`.
- **Typer for CLI**: thin CLI layer, business logic in service modules.
- **Cross-OS**: `pathlib.Path` throughout, Bash + PowerShell hook scripts.
- **Create-only semantics**: installer never overwrites existing files.
- **Ownership safety**: updater only touches framework/system-managed paths.
- **Small focused functions**: <50 lines, single responsibility.
- **Dependency injection**: services receive dependencies through constructors.
- **Project layout**: `src/` layout with `pyproject.toml`.

## Test Tiers

| Tier | Marker | I/O | Gate | Description |
|------|--------|-----|------|-------------|
| Unit | `@pytest.mark.unit` | None | Pre-commit | Pure logic, no I/O, fast (<1s per test) |
| Integration | `@pytest.mark.integration` | Local (filesystem, git) | Pre-push | Tests with local I/O (tmp_path, git init) |
| E2E | `@pytest.mark.e2e` | Full stack | PR gate | End-to-end flows (install, CLI commands, hooks) |
| Live | `@pytest.mark.live` | External APIs | Opt-in | Requires `AI_ENG_LIVE_TEST=1` env var |

- Tests without an explicit marker are treated as **unit** by default.
- Live tests are excluded from CI unless the environment variable is set.
- Coverage targets apply to unit + integration tiers combined.
- E2E tests validate behavior, not line coverage.

## Testing Patterns

See `skills/dev/test-runner/SKILL.md` for full testing patterns and references.

Summary:
- One test file per module, AAA pattern (Arrange-Act-Assert).
- `tmp_path` for filesystem operations.
- Integration tests use real `git init`.
- Naming: `test_<unit>_<scenario>_<expected_outcome>`.
- Fixtures shared in `conftest.py`, scoped appropriately.

## Update Contract

This file is framework-managed and may be updated by framework releases.
