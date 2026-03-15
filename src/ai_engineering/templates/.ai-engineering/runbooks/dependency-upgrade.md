# Runbook: Dependency Upgrade

## Purpose

Guide major version bumps and dependency upgrades safely.

## Procedure

1. **Audit current state**: Run `uv run pip-audit` to identify known vulnerabilities.
2. **Review changelog**: Read the dependency's CHANGELOG for breaking changes.
3. **Update lock file**: `uv lock --upgrade-package <name>`.
4. **Run tests**: `uv run pytest tests/` — full suite, not scoped.
5. **Check type compatibility**: `uv run ty check src/`.
6. **Review API changes**: Search codebase for deprecated APIs mentioned in changelog.
7. **Update code**: Fix any breaking changes identified.
8. **Verify gates pass**: `uv run ai-eng gate all`.
9. **Record decision**: If the upgrade introduces risk, record in `state/decision-store.json`.

## When to Upgrade

- **Immediately**: Security vulnerabilities (CVE with exploit).
- **Weekly**: Patch versions (via Dependabot).
- **Monthly**: Minor versions (manual review).
- **Quarterly**: Major versions (full evaluation).

## Rollback

If the upgrade causes issues:
1. `uv lock --upgrade-package <name>==<old-version>`
2. `uv sync --dev`
3. Verify tests pass
4. Record the rollback reason
