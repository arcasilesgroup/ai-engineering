# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Minimalist command descriptions** — rewrote first line of all 53 `/ai:*` command files (`.claude/commands/ai/*.md`) with short, actionable descriptions that display in autocomplete. Synchronized descriptions to `.github/prompts/ai-*.prompt.md` frontmatter, template mirrors, and both `GEMINI.md` files.
- **Command Contract added to GEMINI.md** — inserted `## Command Contract` section in root and template `GEMINI.md` matching the existing section in `CLAUDE.md`.

### Added
- **3 new skills** — `work-item` (Azure Boards + GitHub Issues bidirectional sync), `agent-card` (platform-portable agent descriptors for Copilot/Foundry/AgentKit/Vertex), `triage` (auto-prioritization with p1/p2/p3 rules and throttle at 10+ open items).
- **`ai:scan` agent** — feature scanner that cross-references specs against code to detect unimplemented features, architecture drift, missing tests, dead specifications, and dependency gaps.
- **`ai:triage` agent** — auto-prioritization agent that scans work items using priority rules (security > bugs > features > perf > tests > arch > dx).
- **`ai:plan` planning pipeline** — default 6-step pipeline: triage check → discovery → prompt design → spec creation → work-item sync → dispatch.
- **`ai:review` individual modes** — 14 review modes invokable individually: `security`, `performance`, `architecture`, `accessibility`, `quality`, `pr`, `smoke`, `platform`, `release`, `dx`, `integrity`, `compliance`, `ownership`.
- **Work-item integration** — manifest.yml `work_items` section supporting GitHub Issues and Azure Boards with bidirectional spec sync and auto-transition.
- **Discovery interrogation skill** (`discover`) — structured requirements elicitation through 8-dimension completeness checks, 5 Whys probing, and KNOWN/ASSUMED/UNKNOWN classification.
- **Architecture patterns table** in product-contract.md section 7.4 — documents scanner/executor separation, single-system-multiple-access-points, finding deduplication, context threading, progressive disclosure, and mode dispatch patterns.
- **Performance and Security growth headers** added to 8 thin stack standards (react-native, astro, nextjs, node, typescript, nestjs, rust, react) as future extension points.

### Changed
- **Skill frontmatter schema aligned** — moved `version` and `tags` from top-level frontmatter keys to `metadata.version` and `metadata.tags` across all 47 skills and template mirrors for stricter Anthropic guide compatibility.
- **Top skill usage examples added** — added `## Examples` sections to 10 frequently used skills (`commit`, `cleanup`, `spec`, `pr`, `code-review`, `test-run`, `debug`, `audit`, `release`, `discover`) and mirrored templates.
- **Validator compatibility updated** — integrity validator now accepts skill version from `metadata.version` (with backward compatibility), preserving `skill-frontmatter` checks after schema alignment.
- **Agent scope model refined** — `ai:review` and `ai:scan` now use `read-write (work items only)` scope to create/sync follow-up work items in Azure Boards or GitHub Issues/Projects while keeping code and governance content non-editable by these agents.
- **Review/scan behavior contracts updated** — agent definitions and template mirrors now include explicit work-item synchronization steps via `skills/work-item/SKILL.md`, preserving finding-to-work-item traceability.
- **README governance section expanded** — added the full skills table (47 skills) under the Skills section and aligned agent scope text with the updated non-code work-item write model.
- **Consolidated 19 agents to 6** — `ai:plan` (orchestration + planning pipeline), `ai:build` (implementation across all stacks, merges 8 agents), `ai:review` (reviews + governance, merges 6 agents), `ai:scan` (feature scanner), `ai:write` (documentation), `ai:triage` (auto-prioritization). Only `ai:build` has code write permissions.
- **Flat skill organization** — restructured 44 skills from 6 nested categories (`workflows/`, `dev/`, `review/`, `docs/`, `govern/`, `quality/`) to flat `skills/<name>/` layout. Added 3 new skills for 47 total. Removed `category` from frontmatter schema; replaced with optional `tags` array.
- **Unified `ai:` command namespace** — replaced 7 prefixes (`dev:`, `review:`, `docs:`, `govern:`, `quality:`, `workflows:`, `agent:`) with single `ai:` prefix. All slash commands now use `/ai:<name>` format.
- **Skill rename map** — 10 skills renamed for clarity: `test-strategy` → `test-plan`, `test-runner` → `test-run`, `data-modeling` → `data-model`, `deps-update` → `deps`, `cicd-generate` → `cicd`, `cli-ux` → `cli`, `api-design` → `api`, `infrastructure` → `infra`, `database-ops` → `db`, `sonar-gate` → `sonar`, `discovery-interrogation` → `discover`, `self-improve` → `improve`, `writer` → `docs`, `prompt-design` → `prompt`, and 14 review/govern/quality renames.
- **Consolidated 50 skills to 44** (prior spec) — merged accept-risk + resolve-risk + renew-risk into `risk` (mode: accept/resolve/renew); create-agent + delete-agent into `agent-lifecycle` (mode: create/delete); create-skill + delete-skill into `skill-lifecycle` (mode: create/delete); dast + container-security + data-security into `sec-deep` (mode: dast/container/data). Removed standalone acho skill (redirected to commit/pr).
- **Compacted CLAUDE.md** from 280 to 114 lines (~810 tokens). Replaced verbose skill/agent path lists with compact table format. Propagated to all 6 instruction file mirrors.
- **Enhanced all 19 agent personas** with 5-element framework: specific role + seniority, industry/domain context, named methodologies, explicit constraints, and output format specification. Identity-only changes; capabilities and behavior unchanged.
- **Deduplicated core.md** — removed ~85 lines of overlap with skills-schema.md.
- **Added finding deduplication baseline** to `framework/core.md` — agents must check decision-store before reporting duplicate findings.
- **Added remediation priority order** to `quality/core.md` — security > reliability > correctness > performance > maintainability > testability > docs > style.
- **Updated registration cascade** across all artifacts: instruction files, manifest.yml, product-contract.md, slash commands, Copilot prompt files, agent frontmatter references, template mirrors, and test fixtures.

### Removed
- **19 old agent files** — api-designer, architect, code-simplifier, database-engineer, debugger, devops-engineer, docs-writer, frontend-specialist, governance-steward, infrastructure-engineer, navigator, orchestrator, platform-auditor, pr-reviewer, principal-engineer, quality-auditor, security-reviewer, test-master, verify-app. Capabilities absorbed into 6 new agents.
- **6 skill category directories** — `workflows/`, `dev/`, `review/`, `docs/`, `govern/`, `quality/` replaced by flat `skills/<name>/` structure.
- **7 command prefixes** — `dev:`, `review:`, `docs:`, `govern:`, `quality:`, `workflows:`, `agent:` replaced by unified `ai:` prefix.
- Standalone skills (prior spec): `govern/accept-risk`, `govern/resolve-risk`, `govern/renew-risk`, `govern/create-agent`, `govern/delete-agent`, `govern/create-skill`, `govern/delete-skill`, `review/dast`, `review/container-security`, `review/data-security`, `workflows/acho` (11 skills removed, 4 consolidated replacements + 1 new = net -6).

### Fixed
- **Framework smoke Python install resilience** — `.github/workflows/ci.yml` now retries `uv python install` up to 3 times with backoff in `framework-smoke`, reducing transient GitHub network/download failures across matrix runners.
- **Content Integrity counter parsing** — `ai-eng validate` now correctly counts skills/agents from current instruction table format (`## Skills (N)` + markdown tables), fixing false `counter-accuracy` failures in CI.
- **Moved spec reset from `/cleanup` to `/pr`** — `/pr` now runs conditional Step 0 (`spec-reset --dry-run` then `spec-reset` when complete) so archived specs and cleared `_active.md` are committed on the PR branch and reach `origin/main` on merge; `/cleanup` v3.0.0 now focuses on status/sync/prune/branch cleanup only.
- **Expanded `dotnet.md` standard** (57 -> ~300 lines) — production-grade .NET 10 patterns: SDK version pinning, NuGet Central Package Management, 20+ code patterns (async, DI, minimal APIs, middleware, ProblemDetails, structured logging, health checks), EF Core patterns (DbContext pooling, no-tracking, keyset pagination, compiled queries, interceptors, bulk operations), test tiers with NUnit, testing patterns (WebApplicationFactory, TestContainers, NSubstitute, FluentAssertions, NetArchTest), performance patterns (ArrayPool, BenchmarkDotNet, output caching), C# coding conventions.
- **Expanded `azure.md` standard** (70 -> ~150 lines) — Azure Functions patterns (isolated worker, triggers, Durable Functions, cold start), App Service patterns (deployment slots, auto-scaling, managed identity), Logic Apps patterns (Standard vs Consumption, connectors, error handling), Well-Architected Framework 5-pillar references, 17 cloud design patterns (Circuit Breaker, CQRS, Saga, Strangler Fig, etc.).
- **Evolved `principal-engineer` agent** (v1 -> v2) — scope upgraded from `read-only` to `read-write`. Added implementation, architecture-design, performance-optimization, testing-strategy, migration-planning capabilities. Stack detection step (`.csproj` -> dotnet.md, `pyproject.toml` -> python.md, `package.json` -> typescript.md). Post-edit validation per stack. References expanded with `dotnet.md`, `azure.md`, `database.md`, and 5 additional dev skills.
- **Updated skill references** — `test-runner` now includes .NET test tiers alongside Python tiers. `database-ops` references EF Core patterns from `dotnet.md`. `data-modeling` references EF Core entity mapping patterns. `performance` references .NET performance patterns (ArrayPool, BenchmarkDotNet, output caching).

## [0.1.0] - 2026-03-01

*First MVP release (Phase 1)*

### Added
- **CLI UX skill** (`dev/cli-ux`) — agent-first CLI design patterns: JSON envelopes, Rich human output, dual-mode routing, progress indicators.
- **CLI UX modules** — `cli_envelope.py` (structured JSON envelopes with NextAction), `cli_output.py` (JSON mode detection), `cli_progress.py` (Rich spinners), `cli_ui.py` (terminal formatting helpers: error, info, kv, success).
- **Spec-026: Gemini CLI Support** — `GEMINI.md` instruction file for Gemini CLI, enabling governed AI workflows with the same skills and agents as Claude Code, Copilot, and Codex.
- Installer deploys `GEMINI.md` alongside other provider instruction files on `ai-eng install`.
- Ownership entry for `GEMINI.md` in defaults (framework-managed).
- Validator includes `GEMINI.md` and its template mirror in instruction file sync checks.
- Template mirror: `src/ai_engineering/templates/project/GEMINI.md`.
- Presentation materials updated with Gemini CLI as a supported AI provider.
- **Enhanced `/cleanup` skill (v2.0.0)** — single repository hygiene primitive with 5 phases: Status, Sync, Prune, Cleanup, Spec Reset.
- Repository status module (`maintenance/repo_status.py`): remote branch analysis, ahead/behind tracking, open PR listing via `gh`, stale branch detection (>30 days).
- Spec reset module (`maintenance/spec_reset.py`): active spec detection, completed spec archival to `specs/archive/`, `_active.md` reset.
- CLI commands: `ai-eng maintenance repo-status`, `ai-eng maintenance spec-reset`.
- `/create-spec` now composes `/cleanup` before branch creation for automatic pre-spec hygiene.
- **Spec-025: OSS Documentation Gate** — mandatory documentation gate in `/commit`, `/pr`, and `/acho` workflows for OSS GitHub users.
- Documentation gate classifies changes as user-visible vs internal-only and enforces CHANGELOG.md and README.md updates for user-visible changes.
- External documentation portal support: asks for docs repo URL, clones, updates documentation, creates PR with auto-complete.
- PR checklist expanded with CHANGELOG, README, and external docs items.
- **Spec-024: Sonar Scanner Integration & Platform Credential Onboarding** — platform credential management with keyring, Sonar quality gate skill, and guided onboarding CLI.
- New `credentials` module (`models.py`, `service.py`) for OS-native secret storage via keyring.
- New `platforms` module (`detector.py`, `github.py`, `sonar.py`, `azure_devops.py`) for platform detection and API-validated credential setup.
- New `ai-eng setup` CLI subgroup with `platforms`, `github`, `sonar`, `azure-devops` commands.
- `ai-eng doctor --check-platforms` flag for credential health checks via platform APIs.
- Post-install platform onboarding prompt (opt-in, D024-003).
- New skill: `dev:sonar-gate` — Sonar quality gate integration with skip-if-unconfigured semantics.
- Sonar gate scripts (`sonar-pre-gate.sh`, `sonar-pre-gate.ps1`) with `--skip-if-unconfigured` flag.
- Sonar threshold mapping reference (`sonar-threshold-mapping.md`).
- Sonar quality gate integrated as optional dimension in `quality:release-gate`, `quality:audit-code`, and `quality:install-check`.
- Claude Code command wrapper and Copilot prompt for `dev:sonar-gate`.
- Template mirrors for all new modules, skills, and wrappers.
- **SonarLint IDE Configuration** — `ai-eng setup sonarlint` auto-configures Connected Mode for VS Code family (VS Code, Cursor, Windsurf, Antigravity), JetBrains family (IntelliJ, Rider, WebStorm, PyCharm, GoLand), and Visual Studio 2022.
- New `platforms/sonarlint.py` module with IDE detection, per-family configurators, and merge-safe JSON/XML generation.
- `sonarlint.md` quality standard extended with per-IDE integration guidance and Connected Mode rationale.
- **Spec-023: Multi-Stack Expansion + Audit-Driven Hardening** — comprehensive multi-stack governance from 35+ AI tool audit.
- 8 new stack standards: `typescript.md`, `react.md`, `react-native.md`, `nestjs.md`, `astro.md`, `rust.md`, `node.md`, `bash-powershell.md`.
- 3 cross-cutting standards: `azure.md`, `infrastructure.md`, `database.md`.
- 4 new agents: `infrastructure-engineer`, `database-engineer`, `frontend-specialist`, `api-designer`.
- 4 new skills: `dev:api-design`, `dev:infrastructure`, `dev:database-ops`, `review:accessibility`.
- 3 behavioral baselines added to framework core: Holistic Analysis Before Action, Exhaustiveness Requirement, Parallel-First Tool Execution.
- 6 reference files expanded with substantive content: delivery-platform-patterns, language-framework-patterns, database-patterns, api-design-patterns, platform-detect, git-helpers.
- Claude Code command wrappers and Copilot prompt/agent wrappers for all new agents and skills.
- Template mirrors for all new agents, skills, and stack standards.
- GitHub Copilot prompt files (`.github/prompts/`) — 46 prompt wrappers mapping to all skills, available as `/command` in Copilot Chat.
- GitHub Copilot custom agents (`.github/agents/`) — 9 agent wrappers available in VS Code agent dropdown.
- Copilot prompts and agents mirror-sync validation in `ai-eng validate`.
- Installer deploys `.github/prompts/` and `.github/agents/` on `ai-eng install`.
- Cleanup workflow skill for branch cleanup and stale branch removal (`/cleanup`).
- Contract-compliance skill for clause-by-clause framework contract validation.
- Ownership-audit skill for ownership boundary and updater safety validation.
- Docs-audit skill for documentation and content quality auditing.
- Test-gap-analysis skill for capability-to-test risk mapping.
- Release-gate skill for aggregated release readiness GO/NO-GO verdicts.
- Platform-auditor agent for full-spectrum audit orchestration across all quality dimensions.
- Command contract compliance validation in verify-app agent.
- Feature inventory mode in codebase-mapper agent.
- Architecture drift detection in architect agent.
- Enforcement tamper resistance analysis in security-reviewer agent.
- Module value classification mode in code-simplifier agent.
- Explain skill for Feynman-style code and concept explanations with 3-tier depth.
- Risk acceptance lifecycle: `accept-risk`, `resolve-risk`, `renew-risk` lifecycle skills with severity-based expiry (C=15d/H=30d/M=60d/L=90d) and max 2 renewals.
- Pre-implementation workflow skill for branch hygiene before new implementation work.
- Branch cleanup module (`maintenance/branch_cleanup.py`): fetch, prune, delete merged branches.
- Pipeline compliance module (`pipeline/compliance.py`, `pipeline/injector.py`): scan GitHub Actions and Azure DevOps pipelines for risk governance gates.
- Pipeline risk gate templates for GitHub Actions and Azure DevOps.
- Shared git operations module (`git/operations.py`): `run_git()`, `current_branch()`, `is_branch_pushed()`, `is_on_protected_branch()`.
- Risk governance gate checks: pre-commit warning for expiring acceptances, pre-push blocking for expired acceptances.
- CLI commands: `ai-eng gate risk-check`, `ai-eng maintenance branch-cleanup`, `ai-eng maintenance risk-status`, `ai-eng maintenance pipeline-compliance`.
- Decision model extended with `riskCategory`, `severity`, `acceptedBy`, `followUpAction`, `status`, `renewedFrom`, `renewalCount` fields (all optional, backward compatible).
- `DecisionStore.risk_decisions()` helper method.
- Risk lifecycle functions in `decision_logic.py`: `create_risk_acceptance()`, `renew_decision()`, `revoke_decision()`, `mark_remediated()`, `list_expired_decisions()`, `list_expiring_soon()`.
- `MaintenanceReport` extended with risk acceptance and branch status fields.
- Create-spec skill for spec creation with branch-first workflow.
- Delete-skill skill for safe skill removal with dependency checks.
- Delete-agent skill for safe agent removal with dependency checks.
- Content-integrity skill for governance content validation (6-category check).
- Spec-First Enforcement section in framework core standards.
- Content Integrity Enforcement section in framework core standards.
- Content integrity capability in verify-app agent.
- Create-skill skill for definitive skill authoring and registration procedure.
- Create-agent skill for definitive agent authoring and registration procedure.
- Changelog documentation skill for generating user-friendly changelogs and release notes from git history.
- Doc-writer skill for open-source documentation generation from codebase knowledge.
- Canonical/template mirror contract for `.ai-engineering` governance artifacts.
- Installer coverage for full bundled non-state governance template tree.

### Changed
- **CLI commands migrated to UX modules** — all 10 CLI command modules (`cicd`, `core`, `gate`, `maintenance`, `review`, `setup`, `skills`, `stack_ide`, `validate`, `vcs`) refactored to use `cli_envelope`, `cli_output`, `cli_progress`, and `cli_ui` for consistent terminal output, JSON mode support, and Rich spinners.
- **Governance surface: 49→50 skills** — `dev/cli-ux` registered across all instruction files (CLAUDE.md, AGENTS.md, GEMINI.md, copilot-instructions.md).
- **Documentation gate always evaluates** — removed binary "internal-only → skip" classification from `/commit`, `/pr`, and `/acho` workflows. The gate now classifies scope (CHANGELOG + README, CHANGELOG only, or no updates needed) but never auto-skips entirely. Skill, agent, and governance surface changes are no longer blanket-exempt.
- **`/cleanup` mandates CLI commands** — Phase 0 (repo-status), Phase 3 (branch-cleanup), and Phase 4 (spec-reset) now require `uv run ai-eng maintenance <command>` instead of ad-hoc shell commands. Prevents zsh `!=` operator escaping failures during stale branch detection.
- `/cleanup` upgraded from branch-only cleanup to full repository hygiene primitive (status + sync + prune + cleanup + spec reset).
- Session Start Protocol updated: "Run `/cleanup`" replaces "Run `/pre-implementation`" across all provider instruction files.
- Maintenance report includes remote branch, open PR, and stale branch counts.
- 6 existing agents improved: devops-engineer (Azure Pipelines, Railway, Cloudflare), architect (infra architecture), security-reviewer (cloud security, IaC scanning), orchestrator (parallel-first), principal-engineer (exhaustiveness), test-master (multi-stack).
- 3 existing skills improved: cicd-generate (Azure Pipelines, Railway, Cloudflare), deps-update (multi-stack detection), security (cloud + IaC scanning).
- `nextjs.md` stack standard updated with TypeScript base reference.
- Governance surface: 45→49 skills, 15→19 agents, 5→14 stack standards.
- Refactored git operations out of `workflows.py` and `gates.py` into shared `git/operations.py`.
- Decision store schema bumped from 1.0 to 1.1 (backward compatible).
- Gate pre-commit now includes risk expiry warnings.
- Gate pre-push now blocks on expired risk acceptances.
- Aligned `.ai-engineering` and `src/ai_engineering/templates/.ai-engineering` non-state content.
- Installer template mapping now discovers bundled governance files dynamically.
- Updated governance metadata versions from `0.1.0-dev` to `0.1.0`.

### Removed
- `/pre-implementation` skill — functionality absorbed into `/cleanup` and `/create-spec`.
- `poetry.lock` and empty e2e test package placeholder.

### Fixed
- **Template product-contract.md** — committed version shipped ai-engineering-specific content instead of generic `<project-name>` placeholders, causing `ai-eng install` to copy project-specific data to new installations.
- **12 template mirrors synced** — agents, skills, standards, and project templates restored to generic form for clean installations.
- Content Integrity CI: synced `create-spec/SKILL.md` template mirror with canonical (missing cleanup step).
- Content Integrity CI: corrected skill count in `product-contract.md` from 50 to 49.
- `ai-eng install` no longer crashes (exit code 1) when platform onboarding prompt is aborted or running in non-interactive mode.
- Setup CLI commands now correctly registered on module-level Typer instance (fixes unit test isolation).
- Doctor platform check test uses correct patch path for `GitHubSetup`.
- Template mirror for `dev/sonar-gate/SKILL.md` synced with canonical source.
- Lint fixes: `str, Enum` → `StrEnum`, combined `with` statements, ternary simplifications.
