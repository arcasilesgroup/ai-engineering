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
| 1 | Content Core + Installability — 47 skills, 6 agents, 14 stacks, Python CLI | Complete |
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
| Governance content | 47/47 skills, 6/6 agents, 14/14 stack standards |
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

Spec-031: Architecture Refactor — Agents, Skills & Standards (19 → 6 agents, flat skills, `ai:` namespace). Branch: `spec/031-framework-optimization`.

### Read Sequence

1. `context/specs/_active.md`

## 5. KPIs

| Metric | Target | Current | Trend |
|--------|--------|---------|-------|
| Install adoption (repos using framework) | Tracking | Pre-release | — |
| Quality gate pass rate | 100% on all governed ops | 100% (ruff, ty, format) | → |
| Security scan pass rate | 100% — zero medium+ | 7 semgrep (1E+6W); gitleaks 0; pip-audit 0 | ↑ |
| Tamper resistance score | 100/100 | 85/100 (B3/B4 done, CI stabilizing) | ↑ |
| Agent coverage | 47 skills + 6 agents | 47/47 + 6/6 | → |
| Test coverage | 90% (100% governance-critical) | 91% (889+ tests) | ↑ |
| Cross-OS CI pass | 3x3 matrix green | Implemented, stabilizing | ↑ |
| Token efficiency | >= 95% deferred at session start | 99.19% (500/61,386) | → |

## 6. Governance Surface Summary

### 6.1 Skills (47 total, flat organization)

Path: `skills/<name>/SKILL.md` — no category subdirectories.

| Skills (alphabetical) |
|-----------------------|
| a11y, agent-card, agent-lifecycle, api, arch-review, audit, changelog, cicd, cleanup, cli, code-review, commit, compliance, data-model, db, debug, deps, discover, docs, docs-audit, explain, improve, infra, install, integrity, migrate, multi-agent, ownership, perf-review, pr, prompt, refactor, release, risk, sbom, sec-deep, sec-review, simplify, skill-lifecycle, sonar, spec, standards, test-gap, test-plan, test-run, triage, work-item |

### 6.2 Agents (6 total, role-based)

| Agent | Purpose | Scope |
|-------|---------|-------|
| plan | Orchestration, planning pipeline, dispatch, work-item sync | read-write |
| build | Implementation across all stacks (ONLY code write agent) | read-write |
| review | All reviews, security, quality, governance (14 individual modes) | read-only |
| scan | Spec-vs-code gap analysis, architecture drift detection | read-only |
| write | Documentation, changelogs, explanations | read-write (docs only) |
| triage | Auto-prioritize work items, backlog grooming | read-write (work items only) |

### 6.3 Stack Standards (14)

Python, TypeScript, React, React Native, NestJS, Next.js, Astro, .NET (expanded: ASP.NET Core, EF Core, C# conventions), Rust, Node, Bash/PowerShell, Database, Infrastructure, Azure (expanded: Functions, App Service, Logic Apps, WAF, cloud patterns).

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
| 026 | Gemini support | Complete |
| 028 | .NET & Azure standards expansion + principal engineer evolution | Active |

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

### 7.4 Architecture Patterns

| Pattern | Source | Implementation |
|---------|--------|---------------|
| Scanner/Executor separation | DevExpert | Agent `scope` field (read-only vs read-write) separates analysis from modification |
| Single-system-multiple-access-points | Spotify | One canonical skill/agent, multiple access surfaces (Claude, Copilot, Gemini, CLI) |
| Finding deduplication | DevExpert | `state/decision-store.json` checked before reporting duplicate findings |
| Context Threading Protocol | Multi-agent research | Structured context summaries (`Findings`, `Dependencies`, `Risks`, `Recommendations`) |
| Progressive disclosure | Token efficiency | Three-level loading: metadata → body → resources |
| Mode dispatch | Consolidation | Single skill with mode argument replaces multiple atomic skills |

## 8. Stakeholders

- **Maintainers**: arcasilesgroup — framework and project ownership.
- **Contributors**: governed by standards and skills.
- **Users**: developers adopting the framework in their repositories.

## 9. Decision Log Summary

All decisions persisted in `state/decision-store.json` (25+ decisions, S0-001 through D025-001).
Agents MUST check the decision store before prompting for any previously decided question.

Last decision: D028-001 (2026-03-01) — .NET standards expansion strategy: expand existing standards as single source of truth, zero new skills.
