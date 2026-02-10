# Framework Python Stack Standards

## Update Metadata

- Rationale: align with framework-contract.md v2 tooling baseline and coding patterns for rewrite.
- Expected gain: predictable Python baseline with explicit patterns for AI-assisted code generation.
- Potential impact: tooling requirements and code patterns become enforceable during generation and review.

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
- Test coverage target: ≥80% overall, ≥90% for governance-critical paths.
- Line length: 100.
- Docstrings: Google-style on all public functions and classes.

## Code Patterns

- **Pydantic for schemas**: all state models use Pydantic v2 `BaseModel`.
- **Typer for CLI**: thin CLI layer, business logic in service modules.
- **Cross-OS**: `pathlib.Path` throughout, Bash + PowerShell hook scripts.
- **Create-only semantics**: installer never overwrites existing files.
- **Ownership safety**: updater only touches framework/system-managed paths.
- **Small focused functions**: <50 lines, single responsibility.
- **Dependency injection**: services receive dependencies through constructors.
- **Project layout**: `src/` layout with `pyproject.toml`.

## Testing Patterns

- One test file per module, AAA pattern (Arrange-Act-Assert).
- `tmp_path` for filesystem operations.
- Integration tests use real `git init`.
- Naming: `test_<unit>_<scenario>_<expected_outcome>`.
- Fixtures shared in `conftest.py`, scoped appropriately.

## Update Contract

This file is framework-managed and may be updated by framework releases.
