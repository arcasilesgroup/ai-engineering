# Spec 007: CI Pipeline Fix — Done

## Completion Date

2026-02-11

## Summary

Fixed all 13 failing CI jobs by migrating dev dependencies from `[project.optional-dependencies].dev` to `[dependency-groups].dev` (PEP 735) and fixing 10 broken file references in governance documents.

## Changes Delivered

- **pyproject.toml**: migrated dev dependencies to PEP 735 `[dependency-groups].dev` section
- **uv.lock**: regenerated to reflect dependency structure change
- **Governance doc fixes**: corrected 10 broken file references across `.ai-engineering/README.md`, `framework-contract.md`, `specs/001-*/tasks.md`, `specs/002-*/tasks.md`
- **Template mirrors**: synced `templates/.ai-engineering/README.md` and `templates/.ai-engineering/context/product/framework-contract.md`

## Quality Gate

- All 13 CI jobs pass (lint, typecheck, 9x test matrix, security, content-integrity)
- `build` job runs successfully and produces wheel artifact
- `uv run ai-eng validate` passes 6/6 categories with 0 broken references
- Template mirrors in sync (mirror-sync validator category passes)
- `release.yml` compatible without changes (same `uv sync --dev` pattern)

## Decision References

- D1: Migrate to `[dependency-groups]` (PEP 735 is the modern uv convention)
- D2: Fix references instead of suppressing in validator
- D3: Keep `release.yml` unchanged (fixed by pyproject.toml change)
