# Product Contract — ai-engineering

## Update Metadata

- Rationale: expand from 87-line stub to comprehensive living project document. Absorb roadmap and rollout plan from framework-contract.md (which now focuses exclusively on eternal framework rules). Add governance surface summary, architecture snapshot, and spec history so AI agents have complete project context.
- Expected gain: AI agents can determine project state, objectives, and history from a single document. Future implementations reference this for what's built, building, and planned.
- Potential impact: this becomes the primary document for project-specific decisions. Agents MUST update this document when closing specs (done.md).

## 1. Project Identity

- **Name**: ai-engineering
- **Repository**: `arcasilesgroup/ai-engineering`
- **Owner**: arcasilesgroup
- **Status**: Active development (post-rewrite, iterative hardening)
- **License**: MIT
- **Distribution**: PyPI (`py3-none-any` wheel)
- **Primary language**: Python (minimal runtime)
- **Governance model**: content-first, AI-governed
- **Framework contract**: `context/product/framework-contract.md` — defines eternal framework rules

## 2. Roadmap and Release Plan

### 2.1 Roadmap Phases

#### Phase 1 (MVP) — Delivered

- GitHub runtime integration.
- Terminal + VS Code support.
- Cross-OS validation: Windows, macOS, Linux (CI matrix).
- Dogfooding in this repository.
- Stack baseline: Python + Markdown/YAML/JSON/Bash with `uv`, `ruff`, `ty`, `pip-audit`.
- Mandatory system state files: install manifest, ownership map, sources lock, decision store, audit log.
- Remote skills default ON with cache, checksums, and signature metadata scaffolding.
- Azure DevOps VCS provider (delivered ahead of Phase 2).
- Sonar Cloud/SonarQube integration with credential management (delivered ahead of Phase 2).
- 14 stack standards: Python, TypeScript, React, React Native, NestJS, Next.js, Astro, .NET, Rust, Node, Bash/PowerShell, Database, Infrastructure, Azure.
- Exit criteria met: command contract implemented, local enforcement non-bypassable, updater ownership-safe, readiness checks operational.

#### Phase 2 — In Progress

- Stronger signature verification enforcement modes.
- Additional IDE adapters beyond VS Code family and JetBrains.
- Release hardening: SAST remediation to zero medium+ findings.
- OSS documentation gates for governed workflows.

#### Phase 3 — Planned

- Governed parallel subagent orchestration at scale.
- Maintenance agent maturity and policy packs.
- Docs site integration (Nextra) and broader ecosystem work.

### 2.2 Rollout Plan

| Phase | Name | Status |
|-------|------|--------|
| 0 | Rebuild Baseline — clean branch, contract-first structure, minimal runtime | Complete |
| 1 | Content Core + Installability — 50 skills, 19 agents, 14 stacks, Python CLI | Complete |
| 2 | Dogfooding + Hard Validation — E2E validation, cross-OS CI, SAST remediation | In Progress |
| 3 | Release Readiness — freeze contract, validate migrations, publish 0.2.0 | Pending |

Merge to main only after full E2E success.

### 2.3 Release Status

- **Current version**: 0.1.0
- **Next milestone**: 0.2.0 (SAST remediation + coverage hardening + OSS doc gate)
- **Blockers**: 7 semgrep findings must reach 0 medium+ before release
- **Branch**: `main` (rewrite v2 merged; feature branches per spec)

## 3. Product Goals (Current Phase)

This project dogfoods the ai-engineering framework on itself.

### 3.1 Active Objectives

1. Remediate SAST findings (7 semgrep findings: 1 ERROR + 6 WARNING).
2. Harden cross-OS CI evidence (stabilize matrix run history).
3. Reach 95% test coverage (currently 91%, target 90% met).
4. Prepare 0.2.0 release with full E2E validation across platforms.
5. OSS documentation gate enforcement in `/commit`, `/pr`, `/acho` workflows.

### 3.2 Completed Milestones

| Area | Evidence |
|------|----------|
| Governance content | 50/50 skills, 19/19 agents, 14/14 stack standards |
| Python runtime | 75 source files across 17 modules |
| CI/CD | 3 workflows (ci.yml, install-smoke.yml, release.yml) with cross-OS matrix |
| E2E tests | install clean + install existing flows validated |
| Multi-agent model | 4 orchestration patterns, context threading protocol, capability matching |
| VCS providers | GitHub + Azure DevOps with dual-provider abstraction |
| Platform integration | Sonar Cloud/SonarQube with keyring-backed credentials |
| Command contract | `/commit`, `/pr`, `/acho` with full governance enforcement |

### 3.3 Success Criteria

```bash
# All must pass for release readiness:
uv sync && uv run pytest tests/ -v --cov=ai_engineering --cov-fail-under=90  # 90% coverage
uv run ruff check src/ && uv run ruff format --check src/                     # 0 issues
uv run ty check src/                                                           # 0 errors
uv run pip-audit                                                               # 0 vulnerabilities
# Install on clean venv:
ai-eng version && ai-eng doctor && ai-eng install                             # all operational
# Hook enforcement:
# commit with secret → blocked | push without tests → blocked
```

## 4. Active Spec

No active spec — ready for `/create-spec`. Last completed: Spec-026 (Gemini Support).

### Read Sequence

1. `context/specs/_active.md`

## 5. KPIs

| Metric | Target | Current | Trend |
|--------|--------|---------|-------|
| Install adoption (repos using framework) | Tracking | Pre-release | — |
| Quality gate pass rate | 100% on all governed ops | 100% (ruff, ty, format) | → |
| Security scan pass rate | 100% — zero medium+ | 7 semgrep (1E+6W); gitleaks 0; pip-audit 0 | ↑ |
| Tamper resistance score | 100/100 | 85/100 (B3/B4 done, CI stabilizing) | ↑ |
| Agent coverage | 50 skills + 19 agents | 50/50 + 19/19 | → |
| Test coverage | 90% (100% governance-critical) | 91% (889+ tests) | ↑ |
| Cross-OS CI pass | 3x3 matrix green | Implemented, stabilizing | ↑ |
| Token efficiency | >= 95% deferred at session start | 99.19% (500/61,386) | → |

## 6. Governance Surface Summary

### 6.1 Skills (50 total, 6 categories)

| Category | Count | Skills |
|----------|-------|--------|
| workflows | 6 | commit, pr, acho, cleanup, self-improve, create-spec (via govern) |
| dev | 17 | multi-agent, code-review, refactor, debug, test-runner, test-strategy, migration, deps-update, data-modeling, database-ops, api-design, infrastructure, cicd-generate, cli-ux, sonar-gate |
| review | 7 | architecture, security, data-security, performance, accessibility, dast, container-security |
| quality | 7 | audit-code, docs-audit, install-check, release-gate, sbom, test-gap-analysis |
| govern | 11 | create-spec, create-skill, delete-skill, create-agent, delete-agent, integrity-check, ownership-audit, contract-compliance, accept-risk, renew-risk, resolve-risk, adaptive-standards |
| docs | 5 | writer, changelog, explain, simplify, prompt-design |

### 6.2 Agents (19 total, 8 categories)

| Category | Agents |
|----------|--------|
| orchestration | orchestrator |
| analysis | architect, navigator, principal-engineer |
| review | pr-reviewer, security-reviewer, code-simplifier |
| quality | quality-auditor, platform-auditor |
| delivery | devops-engineer, infrastructure-engineer, database-engineer |
| docs | docs-writer |
| governance | governance-steward |
| testing | test-master, verify-app |
| development | api-designer, frontend-specialist, debugger |

### 6.3 Stack Standards (14)

Python, TypeScript, React, React Native, NestJS, Next.js, Astro, .NET, Rust, Node, Bash/PowerShell, Database, Infrastructure, Azure.

### 6.4 Spec History

| Spec | Title | Status |
|------|-------|--------|
| 001 | Framework rewrite from scratch | Complete |
| 002 | Cross-reference hardening + lifecycle skill category | Complete |
| 003 | Governance enforcement — spec-first + content integrity | Complete |
| 004 | Hygiene and risk governance — branch cleanup, risk lifecycle | Complete |
| 005 | Slash command wrappers + codebase lint cleanup | Complete |
| 006 | Agent parity and sync validator | Complete |
| 007 | CI pipeline fix — dependency resolution + broken references | Complete |
| 008 | Claude Code optimization | Complete |
| 009 | Updater hardening — ownership, trees, rollback, diff, tests | Complete |
| 010 | Version lifecycle — deprecation enforcement + upgrade warnings | Complete |
| 011 | Explain skill — Feynman-style code and concept explanations | Complete |
| 012 | Skills taxonomy — activity-based category reorganization | Complete |
| 013 | CLI UX hardening — verify-app findings remediation | Complete |
| 014 | Dual VCS provider (GitHub + Azure DevOps) | Complete |
| 015 | Multi-stack security and quality capabilities | Complete |
| 016 | OpenClaw-inspired skill and standards hardening | Complete |
| 017 | OpenClaw carryover remediation + close 014/015 | Complete |
| 018 | Environment stability and governance hardening | Complete |
| 019 | GitHub Copilot prompt files and custom agents | Complete |
| 020 | Multi-agent model evolution | Complete |
| 021 | Governance + CI/CD evolution | Complete |
| 022 | Test pyramid rewrite — restructure, parallelize, optimize | Complete |
| 023 | Multi-stack expansion + audit-driven hardening | Complete |
| 024 | Sonar platform onboarding and credential management | Complete |
| 025 | OSS documentation gate | Complete |
| 026 | Gemini support | Active |

## 7. Architecture Snapshot

### 7.1 Python Modules

17 modules, 75 source files:

| Module | Purpose |
|--------|---------|
| `cli/` + `cli_commands/` | Typer-based CLI entry point and command handlers |
| `installer/` | Framework installation, template replication, stack detection |
| `updater/` | Framework update with dry-run preview and ownership safety |
| `validator/` | Content integrity validation (6 programmatic categories) |
| `doctor/` | Diagnostics with auto-fix capabilities |
| `platforms/` | VCS provider abstraction (GitHub, Azure DevOps, Sonar) |
| `credentials/` | Keyring-backed credential management |
| `hooks/` | Git hook installation and execution |
| `state/` | Decision store and audit log management |
| `skills/` | Skill discovery and execution runtime |
| `policy/` + `pipeline/` | Governance policy and pipeline execution |

### 7.2 CI/CD Workflows

| Workflow | Purpose |
|----------|---------|
| `ci.yml` | Main CI: lint, type-check, test with coverage, cross-OS matrix |
| `install-smoke.yml` | Install validation on clean environments |
| `release.yml` | Release pipeline with SAST, audit, and publish gates |

### 7.3 Test Suite Summary

- **Unit tests**: 658 tests — pure logic, no I/O
- **Integration tests**: 474 tests — filesystem and git operations
- **E2E tests**: 23 tests — install, CLI, and hook flows
- **Total**: 889+ tests, 91% coverage

## 8. Stakeholders

- **Maintainers**: arcasilesgroup — framework and project ownership.
- **Contributors**: governed by standards and skills.
- **Users**: developers adopting the framework in their repositories.

## 9. Decision Log Summary

All decisions persisted in `state/decision-store.json` (25+ decisions, S0-001 through D025-001).
Agents MUST check the decision store before prompting for any previously decided question.

Last decision: D025-001 (2026-02-27) — OSS documentation gate scope.
