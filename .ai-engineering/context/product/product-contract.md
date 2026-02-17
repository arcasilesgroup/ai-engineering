# Product Contract — ai-engineering

## Update Metadata

- Rationale: establish project-managed living document for dogfooding; distinct from framework-contract.md which defines the framework itself.
- Expected gain: AI agents know what THIS project is, its current state, and active goals.
- Potential impact: agents align work to project objectives, not just framework rules.

## Project Identity

- **Name**: ai-engineering
- **Repository**: `arcasilesgroup/ai-engineering`
- **Owner**: arcasilesgroup
- **Status**: Active development (rewrite v2)
- **License**: MIT
- **Distribution**: PyPI (`py3-none-any` wheel)
- **Primary language**: Python (minimal runtime)
- **Governance model**: content-first, AI-governed

## Product Goals (Current Phase)

This project dogfoods the ai-engineering framework on itself.

### Active Objectives

1. Complete governance content: 37 skills, 9 agents, 3 stack instructions.
2. Rewrite all Python modules from scratch following new standards.
3. Achieve CI/CD with cross-OS matrix (Python 3.11/3.12/3.13 × Ubuntu/Windows/macOS).
4. Validate full E2E install/update/doctor cycle.

### Success Criteria

- `uv sync && uv run pytest tests/ -v --cov=ai_engineering` → >80% coverage.
- `uv run ruff check src/ && uv run ruff format --check src/` → 0 issues.
- `uv run ty check src/` → 0 errors.
- `uv run pip-audit` → 0 vulnerabilities.
- Install on clean venv → `ai version`, `ai doctor`, `ai install` work.
- Hooks enforce: commit with secret → blocked, push without tests → blocked.

## Release Status

- **Current version**: 0.1.0
- **Next milestone**: Rewrite v2 merge to main
- **Blockers**: Mega-Phase A (governance content) must complete before Python rewrite
- **Branch**: `rewrite/v2`

## Active Spec

No active spec. All current specs are closed. Check `specs/_active.md` for updates.

## KPIs

| Metric | Target | Current |
|--------|--------|---------|
| Install adoption (repos using framework) | Tracking | Pre-release |
| Quality gate pass rate | 100% on governed ops | Establishing baseline |
| Agent coverage (skills + agents defined) | 37 skills + 9 agents | 37/37 skills, 9/9 agents |
| Test coverage | ≥80% | 85% (429 tests) |
| Cross-OS CI pass | 3×3 matrix green | 6-job pipeline, 3×3 matrix (Ubuntu/Windows/macOS × Python 3.11/3.12/3.13) |

## Stakeholders

- **Maintainers**: arcasilesgroup — framework and project ownership.
- **Contributors**: governed by standards and skills.
- **Users**: developers adopting the framework in their repositories.

## Decision Log Summary

All decisions persisted in `state/decision-store.json`.
Agents must check the decision store before prompting for any previously decided question.
