# Project Identity

## Project
- **Name**: ai-engineering
- **Purpose**: Governance framework for AI-assisted software development. Provides skills, agents, quality gates, and observability for regulated industries across multiple IDEs.
- **Status**: active development

## Services & APIs
- CLI: `ai-eng` (install, validate, doctor, observe, maintenance, signals)
- Skills (40): invoked as `/ai-<name>` across Claude Code, GitHub Copilot, Codex, Gemini
- Agents (9): plan, build, verify, guard, review, explore, guide, simplify, autopilot
- Installer: governance phase seeds `.ai-engineering/` tree into consumer projects

## Dependencies & Consumers
- **Depends on**: Python 3.12+, uv, ruff, gitleaks, pytest, ty, pip-audit
- **Consumed by**: Enterprise development teams in banking, finance, investment, and healthcare

## Boundaries
- Never overwrite team-managed content (`contexts/team/`, `manifest.yml`, `.claude/settings.json`)
- Never weaken quality gate thresholds (coverage >= 80%, duplication <= 3%, complexity <= 10/15)
- Never bypass security scanning (gitleaks, semgrep, pip-audit)
- Coordinate with downstream consumers before changing installer output structure
