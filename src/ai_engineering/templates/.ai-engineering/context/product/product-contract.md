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

1. Complete governance content: 45 skills, 15 agents, 5 stack instructions.
2. Rewrite all Python modules from scratch following new standards.
3. Achieve CI/CD with cross-OS matrix (Python 3.11/3.12/3.13 × Ubuntu/Windows/macOS).
4. Validate full E2E install/update/doctor cycle.

### Success Criteria

- `uv sync && uv run pytest tests/ -v --cov=ai_engineering --cov-fail-under=90` → 90% coverage (100% governance-critical).
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

Spec-021: Governance + CI/CD Evolution. Last completed: Spec-020.

### Read Sequence

1. `context/specs/_active.md`
2. `context/specs/021-governance-cicd-evolution/spec.md`
3. `context/specs/021-governance-cicd-evolution/plan.md`
4. `context/specs/021-governance-cicd-evolution/tasks.md`

## KPIs

| Metric | Target | Current |
|--------|--------|---------|
| Install adoption (repos using framework) | Tracking | Pre-release |
| Quality gate pass rate | 100% on all governed ops | 100% (all tools pass) |
| Security scan pass rate | 100% — zero medium+ findings | 100% (0 critical/high, 1 medium SAST to remediate) |
| Tamper resistance score | 100/100 | 85/100 (B3/B4 implemented, pending CI evidence stabilization) |
| Agent coverage (skills + agents defined) | 45 skills + 15 agents | 45/45 skills, 15/15 agents |
| Test coverage | 90% (100% governance-critical) | 87% (530 tests) |
| Cross-OS CI pass | 3×3 matrix green | In progress (matrix workflow implemented; awaiting run history) |
| Token efficiency (progressive disclosure) | ≥ 95% deferred at session start | 99.14% (500 / 58,278 tokens loaded) |

## Stakeholders

- **Maintainers**: arcasilesgroup — framework and project ownership.
- **Contributors**: governed by standards and skills.
- **Users**: developers adopting the framework in their repositories.

## Decision Log Summary

All decisions persisted in `state/decision-store.json`.
Agents must check the decision store before prompting for any previously decided question.
