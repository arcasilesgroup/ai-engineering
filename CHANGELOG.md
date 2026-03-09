# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Observe enrichment phase 2** — Security Posture, Test Confidence, and enriched SonarCloud sections in engineer and health dashboards with multi-source fallback chains (SonarCloud → local tools → defaults).
- **SonarCloud measures expansion** — `query_sonar_measures()` calls `/api/measures/component` for coverage, complexity, duplication, and vulnerability metrics with module-level caching.
- **Test confidence with fallback** — `test_confidence_metrics()` resolves coverage from SonarCloud → `coverage.json` → `test_scope` mapping → defaults.
- **Security posture with fallback** — `security_posture_metrics()` resolves vulnerabilities from SonarCloud → `pip-audit` → defaults.
- **Session emitter wired** — checkpoint save now emits `session_metric` audit events automatically.
- **Health trend tracking** — `observe health` persists weekly snapshots to `state/health-history.json` (rolling 12 entries) and shows ↑↓→ direction indicators.
- **Smart actions with score gain** — `observe health` replaces hardcoded actions with dynamic recommendations based on weakest components, showing estimated point gains.
- **AI self-optimization hints** — `observe ai` detects patterns (low decision reuse, high gate failures, missing checkpoints) and surfaces actionable suggestions.

### Fixed
- **SonarCloud token resolution** — `_resolve_sonar_token()` now chains env var → OS keyring (`CredentialService`) → None; previously `query_sonar_quality_gate()` checked config flag but never retrieved the stored token.

- **Observe enrichment phase 1** — 8 new signal aggregators (`code_quality_score`, `decision_health`, `adoption_rate`, `lead_time`, `change_failure_rate`, `session_recovery_rate`, `dependency_health`, `multi_variable_health`) in `lib/signals.py` expand dashboards with data computable from existing sources.
- **VCS context in audit events** — `vcs/repo_context.py` and `git/context.py` add branch, commit SHA, repo URL, and provider to every `AuditEntry` automatically via `_emit()`.
- **Workflow CLI commands** — `ai-eng workflow commit`, `ai-eng workflow pr`, and `ai-eng workflow pr-only` registered as CLI subcommands.
- **Expanded observe dashboards** — engineer, team, AI, DORA, and health dashboards enriched with Code Quality, Decision Health, Adoption, Lead Time, Change Failure Rate, and Session Recovery panels.
- **Spec helpers in `lib/parsing.py`** — `_next_spec_number()` and `_slugify()` moved to shared parsing module for reuse.

### Changed
- **Release orchestrator standardized** — replaced internal `_log_audit_event()` with standard `emit_deploy_event()` for consistent audit trail.

### Removed
- **`ai-eng spec save` CLI command** — replaced by LLM-driven spec creation that preserves rich planning content (Risks, Verification, Architecture sections).

- **Squash-merge detection in cleanup** — cleanup skill v4.1.0 now detects branches merged via squash using `git cherry -v`; local branches are properly deleted after PR squash-merge instead of accumulating as "Local-only development".

### Removed
- **Totals section from cleanup report** — redundant with Branch Detail table; cleanup report now shows only the per-branch table.

### Added
- **SonarCloud Quality Gate integration** — `sonar.qualitygate.wait=true` in `sonar-project.properties` as universal gate; scanner polls QG and fails CI if it doesn't pass. Works identically on GitHub Actions and Azure Pipelines.
- **SonarCloud CI job** — new `sonarcloud` job in `ci.yml` with fork guard, downloads per-tier coverage reports (unit/integration/e2e), and blocks build on QG failure.
- **Coverage export per test tier** — unit, integration, and e2e jobs now generate individual Cobertura XML reports (`coverage-unit.xml`, `coverage-integration.xml`, `coverage-e2e.xml`) uploaded as artifacts for SonarCloud consumption.
- **SonarCloud API quality gate check** — `query_sonar_quality_gate()` in `policy/checks/sonar.py` queries SonarCloud Web API for QG status when scanner unavailable; used by pre-push gate (advisory) and observe dashboard.
- **Sonar metrics in engineer dashboard** — `ai-eng observe engineer` shows SonarCloud Quality Gate status, new code coverage, and condition count (silent-skip when unconfigured).
- **`sonar-project.properties` at repo root** — project configured for `arcasilesgroup/ai-engineering` org on SonarCloud.

### Changed
- **Coverage threshold aligned to SonarCloud Quality Gate** — lowered from 90% to 80% across all governance files, standards, IDE configs, templates, and presentation assets. Source of truth: `standards/framework/quality/core.md`.
- **Branch protection updated** — removed defunct "Coverage Gate" required status check, added "SonarCloud" as required check on `main`.
- **Migrated deprecated GitHub Action** — `SonarSource/sonarcloud-github-action@v3` replaced with unified `SonarSource/sonarqube-scan-action@v4` for both SonarCloud and SonarQube (D038-003).
- **Removed redundant Coverage Gate job** — tests no longer re-run solely for coverage; each tier generates its own report.
- **SonarCloud blocks build** — `sonarcloud` job added to `build.needs` so Quality Gate failure prevents package build.
- **Properties template expanded** — `sonar-project.properties` template now includes `sonar.qualitygate.wait`, `sonar.qualitygate.timeout`, stack-aware coverage paths (Python/dotnet/nextjs), sources, tests, and exclusions.
- **CI/CD generation includes coverage steps** — `_render_github_ci` and `_render_azure_ci` generate coverage report commands per stack when Sonar is configured.

### Fixed
- **CI actionlint SC2012** — replaced `ls coverage-*.xml` with `find` in SonarCloud job's coverage merge step to satisfy shellcheck.

### Changed
- **Branch cleanup now handles squash-merged branches** — `ai-eng maintenance branch-cleanup` detects branches whose remote tracking ref is `[gone]`, verifies they have no unmerged changes via `git diff`, and safely deletes them. Branches with divergent content are skipped with a clear reason.
- **Governance simplification** — removed `learnings.md`, `sources.lock.json`, and legacy Claude/Copilot command files (`cleanup.md`, `commit.md`, `pr.md`) from both canonical and template paths; streamlined `manifest.yml`, `ownership-map.json`, and state defaults accordingly.
- **Skills service refactored** — simplified `skills/service.py` and `cli_commands/skills.py`, removing ~450 lines of unused maintenance and remote-source logic.
- **State models trimmed** — removed obsolete fields from `state/models.py` and `state/defaults.py` (sources lock, learnings references).
- **PR skill v2.0.0** — expanded `/pr` workflow with documentation gate (CHANGELOG, README, product-contract auto-update), spec reset integration, and structured PR description format.
- **Commit skill updated** — added spec-aware commit message format guidance.
- **Cleanup skill updated** — removed spec-reset responsibility (now handled by `/pr`).
- **Presentation assets refreshed** — updated SVGs and speech script to reflect current architecture.

### Removed
- **`learnings.md`** — project learnings file removed from context layer (both canonical and templates).
- **`sources.lock.json`** — remote skill source tracking removed from state layer.
- **Legacy IDE command files** — `.claude/commands/{cleanup,commit,pr}.md` and `.github/prompts/{cleanup,commit,pr}.prompt.md` removed (slash commands via `/ai:<name>` are the canonical path).

### Added
- **`product-contract` skill** — new skill (`/ai:product-contract`) for maintaining product contract documents in sync mode; includes Claude command, Copilot prompt, and Codex agent adaptors.
- **`ai-eng work-item sync` CLI** — syncs specs to external work items (GitHub Issues / Azure DevOps Boards) via new `work_items` service module.
- **VCS issue operations** — `VcsProvider` protocol extended with `create_issue`, `find_issue`, `close_issue`, and `link_issue_to_pr` methods; GitHub and Azure DevOps implementations included.
- **Explain analysis playbook** — reference document (`skills/explain/references/analysis-playbook.md`) for structured code analysis.
- **Solution intent doc** — `docs/solution-intent.md` architectural documentation.
- **Work-item backfill scripts** — `scripts/work_items_backfill.py` and validation script for bulk sync.

### Changed
- **Explain skill v2.0.0** — rewritten from Feynman-style to engineer-grade technical explanations with ASCII diagrams, execution traces, and complexity analysis; scope changed from read-write to read-only.
- **Product contract expanded** — comprehensive update to `.ai-engineering/context/product/product-contract.md` with extended functional requirements, integration details, and KPIs.
- **Framework contract updated** — governance surface and framework-managed paths refreshed.
- **Manifest expanded** — new `work-item` CLI command registered, product-contract skill added to governance surface.
- **Executor runbook enriched** — extended with detailed dispatch and coordination procedures.
- **PR review runbook expanded** — added structured review criteria and automation hooks.
- **GitHub issue templates improved** — bug, feature, and task forms refined with better field definitions.
- **PR template extended** — additional checklist items for product-contract and work-item checks.
- **Template sync** — all project/installer templates synchronized with canonical skill definitions.

### Added
- **Codex/Gemini platform adaptors** — 41 adaptor files (`.agents/skills/*/SKILL.md`) pointing to canonical skill/agent definitions; 7 agent adaptors use `-agent` suffix to avoid name collisions.
- **Automation runbooks** — 13 platform-agnostic runbooks (`.ai-engineering/runbooks/*.md`) across 4 layers: scanner (6), triage (2), executor (2), reporting (3). Ready for Codex, Devin, cron+CLI, or GitHub Actions.
- **GitHub issue/PR templates** — bug, feature, task issue forms (`.github/ISSUE_TEMPLATE/*.yml`) and PR template (`.github/pull_request_template.md`); blank issues disabled.
- **VCS-aware installer** — `copy_project_templates()` accepts `vcs_provider` parameter; GitHub platform copies issue/PR templates automatically.
- **Issue Definition Standard** — `work-item` skill extended with required fields, priority mapping (P0→p1-critical), size guide (S/M/L/XL), and spec URL format.
- **Platform Adaptors + Runbooks in AGENTS.md** — new sections documenting adaptor paths/counts and runbook layers/schedules.
- **Manifest governance surface** — `runbooks/**` framework-managed, `.agents/**` + GitHub templates external-framework-managed, `issue_standard` schema.

### Changed
- **Agent/skill shared-rule normalization** — `plan`, `observe`, and `write/docs` now use canonical shared rules in skills (`PLAN-*`, `OBS-*`, `DOC-*`) with agent contracts referencing rules instead of duplicating procedures.
- **Plan no-execution enforcement** — `/ai:plan` contract now explicitly maps to `PLAN-B1` and requires handoff to `/ai:execute` for execution.
- **Copilot plan agent metadata alignment** — `Plan` agent description synchronized to advisory-planning semantics across GitHub and project templates.
- **PR description format** — `build_pr_description()` now generates What/Why/How/Checklist/Stats sections (matching PR #91 convention) instead of the old Spec/Changes format. Reads `spec.md` sections (Problem, Solution) to auto-populate What and Why.
- **Archive-aware spec URLs** — `_build_spec_url()` checks both active (`specs/{slug}/`) and archived (`specs/archive/{slug}/`) paths on disk; URLs stay valid after spec-reset archives the directory.
- **Spec lifecycle closure** — `done.md` created for specs 035 and 036; both archived via spec-reset; `_active.md` cleared.
- **PR workflow upsert hardening** — `/pr` and `/pr --only` now use deterministic create-or-update behavior with existing-PR detection, append-only body extension (`## Additional Changes`), and file-backed body transport in provider implementations.

### Added
- **Feature-gap wiring detection** — `feature-gap` skill (v1.1.0) extended with step 5.5 to detect disconnected implementations: exported-but-never-imported functions, unregistered endpoints/handlers/CLI commands, and orphaned modules. New "Disconnected" category and Wiring Matrix output section.
- **Scan agent wiring thresholds** — `scan` agent feature-gap mode now covers wiring gaps; threshold table adds ">5 unwired exports" as critical.

### Added
- **`ai-eng spec` CLI commands** — `verify` (auto-correct task counters), `catalog` (regenerate `_catalog.md`), `list` (show active spec with progress), `compact` (prune old archived specs).
- **`ai-eng decision record`** — dual-write protocol: persists new decisions to `decision-store.json` AND `audit-log.ndjson` in a single CLI command.
- **Shared frontmatter parser** — `lib/parsing.py` with `parse_frontmatter()` and `count_checkboxes()` as single source of truth, replacing duplicated inline parsers.
- **Spec `_catalog.md`** — auto-generated catalog of all archived specs with tag index.
- **`StateService.save_decisions()`** — convenience method for writing decision store.

### Changed
- **Spec closure normalization** — `done.md` is now mandatory for spec completion; `completed==total` alone produces a warning, not closure.
- **Validator regex fix** — `manifest_coherence.py` handles unquoted `null`/`none`/`~` in `_active.md` and looks up specs in both `context/specs/` and `context/specs/archive/`.
- **Spec skill enriched frontmatter** — scaffold now includes `size`, `tags`, `branch`, `pipeline`, `decisions` fields.
- **Commit skill updated** — `ai-eng spec verify` runs before each commit.
- **PR skill updated** — `ai-eng spec verify` + `ai-eng spec catalog` run at PR creation.
- **Cleanup skill updated** — `ai-eng spec compact --dry-run` runs during cleanup flow.
- **`standards/framework/core.md` expanded** — documents enriched frontmatter schema and new CLI commands.
- **Mirror sync** — 84 mirror files synchronized (Claude commands, Copilot prompts, Copilot agents, governance templates); fixed pre-existing template desyncs.

### Added
- **`execute` agent** — reads approved plan, dispatches specialized agents, coordinates execution, checkpoints progress, and reports results.
- **`plan` skill** — standalone planning skill (`/ai:plan`) with input classification, pipeline strategy, and spec creation.
- **`/ai:plan` and `/ai:execute` command contract** — plan pipeline (classify → discover → risk → spec → execution plan → STOP) and execute dispatcher documented in CLAUDE.md.
- **Audit prompt catalog** — `.ai-engineering/references/audit-prompt-catalog.md` reference for structured audit prompts.
- **State service** — `state/service.py` centralized state management module.
- **`doctor/models.py`** — extracted `CheckResult`, `CheckStatus`, `DoctorReport` from `doctor/service.py` to break circular imports between doctor modules.
- **`.gitattributes`** — LF line-ending enforcement for `.sh`, `.py`, `.yml`, `.yaml`, `.md`, `.json` files (cross-OS reliability).
- **CI maintenance cron** — `.github/workflows/maintenance.yml` runs `ai-eng maintenance all` weekly (Monday 06:00 UTC).
- **SSRF semgrep rule** — `ssrf-request` rule in `.semgrep.yml` detects `requests.$METHOD($URL)` with non-literal URLs (CWE-918).

### Changed
- **Doctor service refactored** — monolithic `doctor/service.py` decomposed into 8 focused check modules (`doctor/checks/`): tools, hooks, layout, state_files, venv, branch_policy, readiness, version_check.
- **Gates refactored** — monolithic `policy/gates.py` decomposed into 5 check modules (`policy/checks/`): branch_protection, commit_msg, risk, sonar, stack_runner.
- **Validator refactored** — monolithic `validator/service.py` decomposed into shared utilities (`_shared.py`) and 7 category modules (`validator/categories/`): counter_accuracy, cross_references, file_existence, instruction_consistency, manifest_coherence, mirror_sync, skill_frontmatter.
- **CLI commands updated** — minor improvements across cicd, decisions, gate, guide, maintenance, signals, vcs command modules and cli_ui.
- **CLAUDE.md** — skills 33→34 (added `plan`), agents 6→7 (added `execute`), expanded command contract.
- **Plan agent updated** — refined purpose to planning pipeline that STOPS before execution.
- **README.md + GEMINI.md synced to v3** — 34 skills, 7 agents, 37 slash commands, updated agent table and skill list.
- **Template mirrors synced** — `manifest.yml` and `README.md` templates match canonical (7 agents, 34 skills).
- **Governance skill CLI references fixed** — `ai-eng integrity` → `ai-eng validate --category integrity`.
- **Validator `CheckStatus` renamed to `IntegrityStatus`** — resolves naming collision with `doctor/models.py::CheckStatus`.
- **Mirror sync expanded** — `mirror_sync.py` now covers root-level `manifest.yml` and `README.md` (64 mirror pairs total).
- **Tool-availability consolidated** — `doctor/checks/tools.py` delegates to `detector/readiness.py` instead of duplicating `shutil.which` + pip/uv logic.
- **`check_platforms()` wired into `diagnose()`** — callable via `--check-platforms` flag.
- **`install-manifest.json` updated** — `frameworkVersion` 0.1.0→0.2.0, `schemaVersion` 1.1→1.2, added `aiProviders`, `cicd`, `branchPolicy`, `operationalReadiness`, `release` fields.
- **`decision-store.json` key fixed** — `schema_version` → `schemaVersion` (camelCase consistency).
- **Windows venv paths** — template `settings.json` includes `.venv\Scripts\*` alongside Unix `.venv/bin/*`.

### Removed
- **`acho` skill** — removed alias command and all mirrors (`.claude/commands/ai/acho.md`, `.github/prompts/ai-acho.prompt.md`, template mirrors).
- **Stale audit log entries** — cleaned up `state/audit-log.ndjson`.
- **Backward-compat shims** — removed `__getattr__` lazy re-exports from `gates.py` (~65 LOC) and wrapper functions from `doctor/service.py` (~80 LOC). All imports migrated to direct `policy.checks.*` and `doctor.checks.*` paths.
- **Re-exported constants** — removed `_REQUIRED_DIRS`, `_TOOLS`, `_VCS_TOOLS`, `_PROTECTED_BRANCHES` from `doctor/service.py`.

### Fixed
- **Gitleaks command** — `workflows.py` changed from `gitleaks detect --staged` to `gitleaks protect --staged` (security regression fix).
- **6 test stubs filled** — `test_version_check_fail_when_deprecated`, `test_returns_false_on_all_failures`, `test_project_template_root_missing_raises`, `test_skills_cli_branches`, `test_returns_python_when_manifest_empty_stacks`, `test_pr_creation_returns_false_on_failure` — all replaced with real assertions.
- **`ownership-map.json` regenerated** — added missing `.github/prompts/**`, `.github/agents/**`, `.claude/**`, `state/session-checkpoint.json` paths.

### Added
- **ai-engineering v3 architecture** — full redesign with 6 bounded-context agents (plan, build, scan, release, write, observe) and 33 skills (down from 47).
- **11 new skills**: `architecture`, `code-simplifier`, `create`, `delete`, `feature-gap`, `governance`, `observe`, `perf`, `quality`, `security`, `test` — each consolidating multiple v2 skills into mode-based designs.
- **2 new agents**: `observe` (observatory with 5 dashboard modes: engineer/team/ai/dora/health) and `release` (ALM + GitOps lifecycle).
- **Python CLI observability layer** — `ai-eng observe`, `ai-eng signals`, `ai-eng checkpoint`, `ai-eng decisions`, `ai-eng metrics`, `ai-eng scan-report` commands for token-free deterministic metrics.
- **Load-once signal pattern** — `load_all_events()` + `filter_events()` + `*_from()` variants eliminate redundant audit-log reads (8-9x I/O reduction per CLI invocation).
- **Gate instrumentation** — `run_gate()` now emits `gate_result` audit events after each execution, enabling real metrics instead of seed data.
- **AuditEntry enriched detail** — `detail` field evolved from `str | None` to `str | dict[str, Any] | None` for structured event payloads.
- **Structured audit emitters** — `emit_gate_event()`, `emit_scan_event()`, `emit_build_event()`, `emit_deploy_event()`, `emit_session_event()` in `state/audit.py`.
- **VCS commands reference** (`skills/references/vcs-commands.md`) — single-source command mapping for GitHub (`gh`) and Azure DevOps (`az repos`) CLI operations used across skills.
- **Plan agent input classification** — `raw-idea`, `structured-request`, and `pre-made-plan` input types with adaptive discovery/risk/test depth per type.
- **Plan agent pipeline data flow** — explicit data flow table and pipeline guards documenting what each step consumes, produces, and gates on.

### Changed
- **47→33 skill consolidation** — merged overlapping skills: `test-plan`+`test-run`+`test-gap` → `test`; `sec-review`+`sec-deep`+`sbom`+`deps` → `security`; `integrity`+`compliance`+`ownership` → `governance`; `audit`+`sonar`+`code-review` → `quality`; `arch-review` → `architecture`; `perf-review` → `perf`; `docs`+`simplify` → `docs` (modes); `agent-lifecycle`+`skill-lifecycle`+`agent-card` → `create`+`delete`.
- **6→6 agent restructure** — replaced `review` (God Object with 14 modes) and `triage` agents with bounded-context `scan` (7 assessment modes), `release` (ALM+GitOps), and `observe` (observatory).
- **Cross-reference cleanup** — all skill/agent references updated from v2 names to v3 across 13+ governance files.
- **`.github/agents/` synced** — removed `review.agent.md` and `triage.agent.md`, added `observe.agent.md` and `release.agent.md`.
- **`.github/prompts/` synced** — removed 27 stale v2 prompt files, added 11 new v3 prompt files.
- **README.md updated** — flat skill layout (33 skills) replacing v2 category directories.
- **Security hardening** — replaced 3 bare `except: pass` patterns with `logger.debug()` calls; replaced 2 `assert` statements with explicit `raise AssertionError`.
- **Framework contract restructured** — rewritten as concise enforcement document with MUST/MUST NOT directives; removed temporal content (moved to product-contract).
- **Product contract simplified** — reduced to focused product model with architecture patterns and growth roadmap.
- **Plan agent enhanced** — added architecture review, triage, test-plan, and risk skills to pipeline; added input classification and pipeline guards.
- **PR skill updated** — added VCS commands reference, documentation gate, and existing PR upsert logic.
- **Git helpers extended** — added VCS provider detection helpers.

### Removed
- **14 skills eliminated** — `agent-card`, `agent-lifecycle`, `arch-review`, `audit`, `code-review`, `compliance`, `data-model`, `deps`, `docs-audit`, `improve`, `install`, `integrity`, `multi-agent`, `ownership`, `perf-review`, `prompt`, `sbom`, `sec-deep`, `sec-review`, `simplify`, `skill-lifecycle`, `sonar`, `test-gap`, `test-plan`, `test-run`, `triage` — capabilities absorbed into consolidated v3 skills.
- **2 agents removed** — `review` (absorbed by `scan` + `release`) and `triage` (absorbed by `release` work-item mode).
- **Skill reference files** — removed `skills/references/` directory (9 files: api-design-patterns, behavioral-patterns, database-patterns, delivery-platform-patterns, git-helpers, language-framework-patterns, platform-detect, token-inventory, vcs-commands).

### Added
- **`ai-eng guide` command** — re-displays branch policy setup instructions on demand. Reads guide text from install manifest instead of generating files.
- **AI provider selection** — `ai-eng install --provider claude_code --provider github_copilot` deploys only the files needed for chosen providers. Defaults to `claude_code` when omitted.
- **`ai-eng provider` subcommand** — `add`, `remove`, and `list` commands for managing AI providers post-install. Supports `claude_code`, `github_copilot`, `gemini`, and `codex`.
- **Interactive VCS prompt** — when no git remote is detected, `ai-eng install` now prompts for VCS provider instead of silently defaulting to GitHub.
- **VCS CI/CD regeneration** — `ai-eng vcs set-primary` auto-regenerates CI/CD pipelines for the new provider (opt-out with `--no-cicd`).
- **Deferred setup for empty projects** — installs without stacks set `deferredSetup: true` in manifest, signaling AI agents to configure tooling on first interaction.
- **SonarLint auto-configuration** — install automatically configures SonarLint Connected Mode when Sonar is enabled and IDE markers are detected.

### Changed
- **Minimalist command descriptions** — rewrote first line of all 53 `/ai:*` command files (`.claude/commands/ai/*.md`) with short, actionable descriptions that display in autocomplete. Synchronized descriptions to `.github/prompts/ai-*.prompt.md` frontmatter, template mirrors, and both `GEMINI.md` files.
- **Command Contract added to GEMINI.md** — inserted `## Command Contract` section in root and template `GEMINI.md` matching the existing section in `CLAUDE.md`.
- **Provider-aware templates** — `copy_project_templates` and `remove_provider_templates` now operate per-provider with shared-file deduplication (e.g., AGENTS.md shared by copilot/gemini/codex).
- **Schema version 1.2** — `InstallManifest` adds `aiProviders` config with `primary` and `enabled` fields, and `deferredSetup` to `operationalReadiness`.
- **Security tool auto-install** — install attempts `ensure_tool()` for gitleaks and semgrep before falling back to manual step instructions.
- **Branch policy guide repositioned** — guide now appears after suggested next steps with clearer messaging about manual configuration requirement.
- **`/ai:plan` spec creation enforced** — plan agent pipeline step 4 (spec creation) marked as MANDATORY to ensure traceability.

### Removed
- **`GEMINI.md` template** — Gemini CLI reads `AGENTS.md` natively. Removed dedicated `GEMINI.md` template and ownership entry.
- **Branch policy guides moved to console output** — install no longer creates `.ai-engineering/guides/` directory. Guide text is shown inline during install and stored in the manifest for `ai-eng guide` retrieval.

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
