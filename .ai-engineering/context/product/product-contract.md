# Product Contract — ai-engineering

## 1. Identity

- **Name**: ai-engineering (`arcasilesgroup/ai-engineering`)
- **Status**: Active development — Phase 2 (dogfooding + hardening)
- **Version**: 0.1.0 — next: 0.2.0
- **Model**: content-first, AI-governed
- 34 skills, 7 agents, 14 stacks (details: CLAUDE.md)

## 2. Roadmap

- **Phase 1 (MVP)**: Delivered.
- **Phase 2 (Current)**: Signature enforcement, IDE adapters, SAST remediation to zero medium+, OSS doc gates.
- **Phase 3 (Planned)**: Parallel subagent orchestration, maintenance agents, docs site (Nextra).

| Phase | Status |
|-------|--------|
| 2 — Dogfooding + Hard Validation | In Progress |
| 3 — Release Readiness (0.2.0) | Pending |

**Blockers**: 7 semgrep findings must reach 0 medium+ before 0.2.0 release.

## 3. Active Objectives

1. Remediate SAST findings (7 semgrep: 1 ERROR + 6 WARNING).
2. Harden cross-OS CI evidence (stabilize matrix run history).
3. Reach 95% test coverage (currently 91%, target 90% met).
4. Prepare 0.2.0 release with full E2E validation.
5. OSS documentation gate enforcement in governed workflows.

### Success Gates

- `uv run pytest tests/ --cov-fail-under=90` — 90% coverage
- `uv run ruff check src/ && ruff format --check src/` — 0 lint issues
- `ai-eng doctor && ai-eng install` — operational on clean venv

## 4. Active Spec

Read: `context/specs/_active.md`. Verify: `ai-eng spec list`. Catalog: `context/specs/_catalog.md`.

## 5. KPIs

| Metric | Target | Current |
|--------|--------|---------|
| Quality gate pass rate | 100% | 100% |
| Security scan (zero medium+) | 0 | 7 semgrep (1E+6W) |
| Tamper resistance | 100/100 | 85/100 |
| Test coverage | 90% | 91% |
| Cross-OS CI matrix | 3x3 green | Stabilizing |
| Token efficiency | >= 95% deferred | 99.19% |
