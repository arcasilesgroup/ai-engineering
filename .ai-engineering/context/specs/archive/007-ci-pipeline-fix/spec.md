---
id: "007"
slug: "ci-pipeline-fix"
status: "in-progress"
created: "2026-02-11"
---

# Spec 007 — CI Pipeline Fix

## Problem

All 13 CI jobs in `.github/workflows/ci.yml` fail, and the `release.yml` build job has the same latent defect. The `build` job is skipped (cascading dependency failure). Two root causes:

1. **Dependency resolution (errors 1–12)**: Dev dependencies (`ruff`, `ty`, `pytest`, `pytest-cov`, `pip-audit`, `types-pyyaml`) are declared in `[project.optional-dependencies].dev` (pip extras), but CI uses `uv sync --dev` which resolves `[dependency-groups].dev` (PEP 735). No `[dependency-groups]` section exists in `pyproject.toml`, so no dev tools are installed. Every `uv run <tool>` fails with "Failed to spawn: No such file or directory".

2. **Content integrity (error 13)**: `uv run ai-eng validate` reports 10 broken file references across 6 governance files. These reference deleted directories (backlog/, delivery/) and moved files (dev/create-skill.md → `skills/govern/create-skill.md`). The validator exits with code 1 on any `FAIL`.

The `build` job (`needs: [lint, typecheck, test, security, content-integrity]`) never runs because all upstream jobs fail.

## Solution

1. **Migrate dev dependencies** from `[project.optional-dependencies].dev` to `[dependency-groups].dev` (PEP 735) in `pyproject.toml` and regenerate `uv.lock`.
2. **Fix all 10 broken file references** in governance documents and their template mirrors.
3. **Apply the same fix** to `release.yml` (same `uv sync --dev` pattern — fixed by the `pyproject.toml` change).

## Scope

### In Scope

- Restructure `pyproject.toml` from `[project.optional-dependencies].dev` to `[dependency-groups].dev`.
- Regenerate `uv.lock`.
- Fix broken references in `.ai-engineering/README.md` (structure tree + mirror contract).
- Fix broken references in `.ai-engineering/context/product/framework-contract.md` (target structure + mirror contract).
- Fix broken references in `.ai-engineering/context/specs/001-rewrite-v2/tasks.md` (archived paths).
- Fix broken references in `.ai-engineering/context/specs/002-cross-ref-hardening/tasks.md` (moved paths).
- Sync template mirrors: `src/ai_engineering/templates/.ai-engineering/README.md` and `src/ai_engineering/templates/.ai-engineering/context/product/framework-contract.md`.
- Verify `release.yml` works with the dependency fix (no workflow change needed).

### Out of Scope

- Adding new CI jobs or restructuring the workflow matrix.
- Upgrading tool versions (`ruff`, `ty`, `pytest`, etc.).
- Fixing any test failures that may surface once tools actually install.
- Changing the validator logic or adding reference-ignore capabilities.

## Acceptance Criteria

1. `uv sync --dev && uv run ruff --version` succeeds locally and in CI.
2. `uv sync --dev && uv run ty --version` succeeds locally and in CI.
3. `uv sync --dev && uv run pytest --version` succeeds locally and in CI.
4. `uv sync --dev && uv run pip-audit --version` succeeds locally and in CI.
5. `uv run ai-eng validate` passes 6/6 categories with 0 broken references.
6. All 13 CI jobs in `ci.yml` pass (lint, typecheck, 9× test matrix, security, content-integrity).
7. The `build` job runs and produces a wheel artifact.
8. Template mirrors remain in sync (`mirror-sync` validator category passes).

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Migrate to `[dependency-groups]` instead of changing CI to `--extra dev` | PEP 735 is the modern `uv` convention; `--dev` already targets it; no CI changes needed |
| D2 | Fix archived spec references instead of suppressing in validator | Suppression would hide future real broken refs; minimal edits preserve governance integrity |
| D3 | Keep `release.yml` unchanged | Same `uv sync --dev` command; fixed by the `pyproject.toml` change |
