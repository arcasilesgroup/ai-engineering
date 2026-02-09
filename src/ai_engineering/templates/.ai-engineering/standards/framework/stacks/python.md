# Framework Python Stack Standards

## Update Metadata

- Rationale: lock stack-specific quality/security defaults.
- Expected gain: predictable Python baseline across repos.
- Potential impact: tooling requirements become explicit at install time.

## Stack Scope

- Primary language: Python.
- Supporting formats: Markdown, YAML, JSON, Bash.
- Toolchain baseline: `uv`, `ruff`, `ty`.

## Required Tooling

- Package/runtime: `uv`.
- Lint/format: `ruff`.
- Type checking: `ty`.
- Dependency vulnerability scan: `pip-audit`.

## Minimum Gate Set

- Pre-commit: `ruff format --check`, `ruff check`, `gitleaks`.
- Pre-push: `semgrep`, `pip-audit`, tests, type checks.

## Quality Baseline

- Type hints required in production Python modules.
- Test coverage target is at least 75 percent with higher focus on governance-critical paths.
- Line length target: 100.

## Update Contract

This file is framework-managed and may be updated by framework releases.
