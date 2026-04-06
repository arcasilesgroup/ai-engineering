# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Runtime, install, doctor, and remediation unification (spec-102)** -- added an early CLI bootstrap preflight before full app import, shared environment classification and remediation contracts, feed preflight before install and repair, dependency-closure validation for framework runtime, and a tool capability matrix with explicit Windows `semgrep` guidance.
- **TLS-aware dependency audit path (spec-102)** -- added a Windows-friendly `pip-audit` wrapper that respects enterprise trust stores and wired it through verify, policy gates, CI, documentation, skills, and template mirrors.

### Fixed
- **Security verification fail-closed hardening (spec-102)** -- verify now fails closed when the `pip-audit` wrapper exits without usable JSON output instead of treating the audit as inconclusive.
- **Private feed preflight hardening (spec-102)** -- feed reachability checks now allow authentication-gated private feeds instead of blocking install or repair as unreachable.
- **Version alignment (spec-100)** -- `pyproject.toml` now matches latest PyPI release (was stuck at `0.1.0` while PyPI had `0.3.0`). `version/registry.json` backfilled with all three published versions.
- **CHANGELOG reorganization (spec-100)** -- entries assigned to correct `[0.3.0]` and `[0.2.0]` version headers. Previously everything was under `[Unreleased]` with no release boundaries.
- **CI version commit-back (spec-100)** -- `ci-build.yml` now commits version bump back to main via Git Data API after tag creation, preventing version drift. Added `[skip ci]` guard on `workflow_run` trigger to prevent infinite loops.

### Changed
- **Install documentation (spec-100)** -- README Install section now recommends `pipx` (primary) and `uv tool` (alternative) instead of bare `pip install`. Prerequisites listed before install commands. Documents that `ai-eng install` auto-installs missing tools.
- **GETTING_STARTED.md (spec-100)** -- added install preamble with link to README Install section.

### Removed
- **Spanish documentation (spec-100)** -- deleted 2 internal Spanish-language documents from `docs/` (`trabajo-humano-era-ai-native-2026-2031.md`, `ai-engineering-auditoria-diagramas.md`). All documentation is now English-only.

## [0.3.0] - 2026-04-02

### Fixed
- **Wizard empty selection (spec-099)** -- `questionary.checkbox` prompts now validate non-empty selection with re-prompt and display spacebar usage hint. Prevents silent empty stacks/providers/IDEs in manifest.
- **VCS provider state gap (spec-099)** -- `state.vcs_provider` persisted during install, eliminating persistent VCS mismatch warning in doctor.
- **Duplicate VCS warnings (spec-099)** -- removed ToolsPhase warning promotion from `_summary_to_install_result()`, VCS tool warnings now appear once.
- **Pipeline step display order (spec-099)** -- `_render_pipeline_steps` imports `PHASE_ORDER` instead of hardcoding phase sequence.
- **Hardcoded Python gate paths (spec-099)** -- pre-push gate checks (`stack-tests`, `ty-check`) use dynamic path detection from `pyproject.toml` instead of hardcoded `src/ai_engineering` and `tests/unit/`. Checks gracefully skip when target path does not exist.

### Added
- **Project validation (spec-099)** -- `install_cmd()` validates target directory looks like a software project before proceeding. Warns and confirms in interactive mode, aborts in `--non-interactive`.
- **Contributor install flow (spec-099)** -- CONTRIBUTING.md documents `git clone` + source install + test workflow.
- **Branch policy help text (spec-099)** -- expanded with actionable setup steps for GitHub and Azure DevOps.

### Removed
- **Duplication checker from user gates (spec-099)** -- `python -m ai_engineering.policy.duplication` targeted ai-engineering's own source tree, not user projects. Kept in CI only.
- **Project-specific CVE exemption (spec-099)** -- removed `--ignore-vuln CVE-2026-4539` from user-facing `pip-audit` gate. Exemption moved to `pyproject.toml` for ai-engineering's own CI.

## [0.2.0] - 2026-04-01

### Changed
- **CLI branded banner** -- Rich-powered banner with version, branch, and Python info on all `ai-eng` commands. Consistent visual identity across CLI surface.
- **README ecosystem rewrite (spec-098)** -- rewrote `README.md` as GitHub landing page, `.ai-engineering/README.md` as post-install reference guide, and created `GETTING_STARTED.md` as progressive discovery tutorial (5-min win → problem-based → advanced).
- **Verify simplification** -- removed `verify_performance` and `verify_a11y` specialists (always N/A for non-UI/non-benchmark projects). Reduced verify from 8 to 6 specialists. Updated verify-deterministic agent and all IDE mirrors.
- **Canvas refinement** -- upgraded self-review criterion to "museum-quality" bar, formatting cleanup.
- **CI/CD Redesign (spec-097)** -- split 760-line `ci.yml` monolith into `ci-check.yml` (validation + dry build, PR + main) and `ci-build.yml` (build + supply chain, main only via `workflow_run`). Deprecated old `ci.yml`.
- **Artifact-driven releases (spec-097)** -- rewrote `release.yml` from tag-triggered to `workflow_dispatch` with version input (default: latest tag). Supports rollback by dispatching with an older version.
- **Conventional commits (spec-097)** -- adopted `feat(scope):` / `fix(scope):` format replacing `spec-NNN:` prefix. Updated `/ai-commit`, `/ai-pr` skills and all mirrors.
- **Single version source (spec-097)** -- eliminated `__version__.py`, version now read from `pyproject.toml` via `importlib.metadata`. Simplified `version_bump.py` to single-file management.

### Added
- **GETTING_STARTED.md (spec-098)** -- progressive discovery tutorial with 3 phases: "5-minute win" (/ai-start, /ai-guide), "What do you want to do?" (problem-based), and "Unlock the full power" (autopilot, run, instinct, learn). Separate CLI and slash command references.
- **python-semantic-release (spec-097)** -- automatic version bumping from conventional commits integrated into ci-build.yml. Creates tags and draft GitHub Releases on version bump.
- **SLSA Build attestations (spec-097)** -- `actions/attest-build-provenance` generates provenance in the same job as `uv build`, verifiable via `gh attestation verify`.
- **CycloneDX SBOM (spec-097)** -- generates `sbom.json` from production-only dependencies, attached to every release.
- **SHA-256 checksums (spec-097)** -- `CHECKSUMS-SHA256.txt` generated and attached to every release.
- **GitHub hardening (spec-097)** -- branch protection (1 required approval, code owner review, enforce for admins), tag protection (`v*` restricted to admins), PyPI environment restricted to main, Actions allowlist.

### Removed
- **`__version__.py` (spec-097)** -- replaced by `importlib.metadata.version("ai-engineering")`.
- **`ci.yml` monolith (spec-097)** -- replaced by `ci-check.yml` + `ci-build.yml`.

### Fixed
- **Commit-msg gate too strict (spec-097)** -- raised first-line length limit from 72 to 100 characters (aligned with Angular/commitlint conventions). Improved error messages to show the invalid input, valid types, and a corrective example.
- **`ai-eng update` provider filtering (spec-096)** -- update now reads `ai_providers.enabled` from manifest.yml instead of processing all 4 providers. Previously ignored manifest configuration and installed/updated files for all providers regardless of user selection.
- **Validator manifest-driven resolution (spec-096)** -- `_BASE_INSTRUCTION_FILES` in `_shared.py` and `_check_instruction_parity` in `mirror_sync.py` now dynamically resolve instruction files from `ai_providers.enabled` instead of hardcoding CLAUDE.md/AGENTS.md/copilot-instructions.md.
- **Obsolete path pattern (spec-096)** -- `_PATH_REF_PATTERN` in `_shared.py` dropped the `context/` (singular) branch, keeping only `contexts/` (plural) matching the actual directory structure.

### Added
- **Orphan file detection and cleanup (spec-096)** -- `ai-eng update` detects files from disabled providers as orphans, displays them in the tree with `orphan` state (dim magenta), and removes them on user confirmation. Shared files (e.g., AGENTS.md used by multiple providers) are only orphaned when no active provider needs them.
- **Missing instruction file validation (spec-096)** -- validator emits actionable error when an enabled provider's instruction file is missing: "Fix: run ai-eng update or ai-eng install --reconfigure".
- **Platform-filtered instruction files (spec-096)** -- expanded Copilot-only filter to include Gemini instruction files, correctly handling platforms with different skill counts.

### Added
- **`/ai-start` skill (spec-095)** -- session bootstrap with welcome dashboard, recent activity, board status, and available commands. Replaces `/ai-onboard`.

### Changed
- **`ai-board-discover` skill (spec-095)** -- improved board detection and configuration.
- **`ai-board-sync` skill (spec-095)** -- updated board sync script with better error handling.
- **`ai-constitution` skill (spec-095)** -- minor content refinements.
- **`ai-guide` skill (spec-095)** -- updated onboarding guidance.
- **`session-governance.md` (spec-095)** -- updated session governance context.
- **`stack-context.md` (spec-095)** -- updated stack context.
- **`manifest.yml` schema (spec-095)** -- updated manifest schema definition.
- **Hook scripts (spec-095)** -- updated `copilot-skill.ps1`, `copilot-skill.sh`, and `telemetry-skill.py` hook emitters.
- **CLAUDE.md, AGENTS.md, GEMINI.md, copilot-instructions.md (spec-095)** -- refreshed multi-IDE instruction files with latest skill set (47 skills).
- **`sync_command_mirrors.py` (spec-095)** -- improved mirror sync script.
- **Instincts v2 system (spec-095)** -- updated `instincts.yml`, `meta.json`, and `proposals.md`.

### Removed
- **`/ai-onboard` skill (spec-095)** -- replaced by `/ai-start`.

### Added
- **LESSONS.md relocated to `.ai-engineering/LESSONS.md` (spec-090 sub-001)** -- consolidated from `contexts/team/lessons.md` into a top-level framework artifact. Contains 30+ correction patterns, rules, and learning entries. All CLAUDE.md, AGENTS.md, GEMINI.md, and copilot-instructions references updated to the new path. Template mirrors updated accordingly.
- **Instincts v2 schema (spec-090 sub-002)** -- schema version bumped from `1.0` to `2.0`. Replaced `toolSequences`/`errorRecoveries`/`skillAgentPreferences` families with `corrections`/`recoveries`/`workflows`. Each entry now carries `trigger`, `action`, and `confidence` fields. Added confidence scoring (evidence-count tiers: 0.3/0.5/0.7/0.85), weekly decay (`-0.02/week`), and low-confidence pruning. Automatic v1-to-v2 migration preserves high-evidence entries.
- **Instinct skill workflow detection (spec-090 sub-002)** -- new `_detect_skill_workflows` reads `framework-events.ndjson` for `skill_invoked` events, groups by session, and counts sequential skill pairs to populate the `workflows` family.
- **`/ai-instinct` skill rewrite (spec-090 sub-003)** -- redesigned with two modes: passive listening (session start, observe corrections/recoveries silently) and active review (`--review` flag, extracts patterns, enriches with confidence, writes proposals). Replaced `status|review` argument with `--review` flag.
- **Improvement funnel with `proposals.md` (spec-090 sub-004)** -- new `.ai-engineering/instincts/proposals.md` generated by `/ai-instinct --review`. Cross-references instinct evidence with LESSONS.md to surface actionable improvement proposals.
- **`/ai-run` skill** -- autonomous backlog orchestrator that normalizes work items (GitHub Issues, Azure Boards, local markdown), plans safely from architectural evidence via `ai-explore`, executes through `ai-build`, consolidates locally, and delivers through PRs. Includes handlers and reference files.
- **`ai-run-orchestrator` agent** -- 10th agent (orchestrator role). Delegates to Build, Explorer, Verify, Review, and Guard subagents for autonomous backlog execution without human checkpoints after invocation.
- **`/ai-platform-audit` skill** -- verifies IDE platform support is genuinely wired, not just assumed. Checks hooks, skills, agents, and mirrors for Claude Code, GitHub Copilot, Codex, and Gemini CLI. Detects orphaned hooks, missing mirrors, and stale registrations.
- **`/ai-skill-evolve` skill** -- improves existing skills based on real project pain. Reads decision-store, LESSONS.md, instincts, and proposals to understand what actually hurts, evaluates skills against realistic test prompts, and grades quality.
- **`runbooks/handlers/dedup-check.md` (spec-092)** -- shared deduplication handler for all item-creating runbooks. Defines a Finding contract (`domain_label`, `title`, `severity`, `body`, plus optional `file_path`, `rule_id`, `symbol`, `package_name`). Implements a 3-level dedup cascade: check consolidated issues first, then individual issues, then create new items.
- **`work-item-audit` runbook** -- audits non-functional work items against repo reality before consolidation. Closes invalid noise, rewrites mixed items, runs weekly in the hygiene cycle before the consolidation runbook.
- **CONSTITUTION.md** -- new foundational governance document at `.ai-engineering/CONSTITUTION.md`. Replaces `project-identity.md` with a principles-first design: Identity, Mission, 8 Principles (Content Over Code, Gate Integrity, Single Source of Truth, Simplicity First, Verify Before Done, Fix Root Causes, Cross-Platform by Default, Autonomous Execution), 10 explicit Prohibitions, Quality Gates table, Boundaries, and Governance with semantic versioning. TEAM_MANAGED, never overwritten by framework updates.
- **`/ai-constitution` skill** -- new skill for generating and amending CONSTITUTION.md. Supports `generate` (auto-detect + interview), `update` (targeted section edits), and `amend` (formal version-bump process). Called by the installer governance phase and `/ai-onboard`.

### Changed
- **9 item-creating runbooks migrated to shared dedup handler (spec-092)** -- architecture-drift, code-quality, dependency-health, docs-freshness, feature-scanner, governance-drift, performance, security-scan, and wiring-scanner runbooks no longer contain inline dedup logic. Each now maps findings to the Finding contract and routes through `handlers/dedup-check.md`.
- **Consolidate runbook propagates domain labels (spec-092)** -- consolidated issues now carry the union of domain-specific labels from grouped originals (e.g., `tech-debt`, `architecture-drift`). Azure DevOps `System.Tags` updated similarly. Ensures consolidated issues are discoverable by the dedup handler.
- **`/ai-instinct` redesigned from `status|review` to listening + `--review` (spec-090 sub-003)** -- the skill no longer has a `status` mode. Default invocation activates passive listening; `--review` triggers extraction, enrichment, and proposal writing.
- **`/ai-learn` skill updated for LESSONS.md relocation (spec-090 sub-005)** -- all references to `contexts/team/lessons.md` updated to `.ai-engineering/LESSONS.md`.
- **`/ai-create` skill expanded** -- now scaffolds skills with `references/` directories alongside `handlers/` and `scripts/`.
- **Instincts state module v2 (spec-090 sub-002)** -- `src/ai_engineering/state/instincts.py` and hook library `_lib/instincts.py` rewritten for v2 schema. Removed `_select_context_items`, `needs_context_refresh`, `refresh_instinct_context`, `maybe_refresh_instinct_context`, and `instinct_context_path`. Removed `skillAgentPreferences` detection. Added `confidence_for_count`, `apply_confidence_decay`, `prune_low_confidence`, `_detect_skill_workflows`, and `_migrate_v1_to_v2`.
- **`InstinctMeta` model simplified (spec-090 sub-002)** -- removed `last_context_generated_at`, `pending_context_refresh`, and `context_max_age_hours` fields from Pydantic model.
- **Manifest registry updated** -- skill count 41 -> 44, agent count 9 -> 10. New skills (`ai-run`, `ai-platform-audit`, `ai-skill-evolve`) and agent (`run-orchestrator`) registered. Ownership `system` scope simplified (removed `learnings/`).
- **Sync script extended (spec-090 sub-005)** -- `sync_command_mirrors.py` now discovers and mirrors `references/` directories alongside `handlers/` and `scripts/`. Added `run-orchestrator` to `AGENT_METADATA`. Copilot-compatible skill count calculation fixed. Install template Codex surfaces (`hooks.json`, `config.toml`) now mirrored.
- **CLAUDE.md, AGENTS.md, GEMINI.md, copilot-instructions** -- agent table expanded with `run-orchestrator` row. Skill count updated to 44. Enterprise and Meta groups expanded with new skills. Effort table updated.
- **Audit hook Codex compatibility** -- `passthrough_stdin` in `_lib/audit.py` now skips stdout echo when `AIENG_HOOK_ENGINE=codex` to avoid Codex structured-output validation errors.
- **All IDE mirrors updated (spec-090 sub-005)** -- `.claude/`, `.codex/`, `.gemini/`, `.github/`, and template mirrors regenerated for all modified skills (`ai-instinct`, `ai-learn`, `ai-brainstorm`, `ai-commit`, `ai-create`, `ai-onboard`, `ai-pr`) and new skills/agents.
- **`project-identity.md` → `CONSTITUTION.md`** -- file relocated from `.ai-engineering/contexts/` to `.ai-engineering/` root to reflect its foundational status. Content redesigned from scratch (removed metadata tables derivable from `pyproject.toml`; added Principles and Prohibitions sections). All skill references, Step 0 protocol, IDE mirrors (Claude, Copilot, Gemini, Codex), and template project copies updated.
- **`ai-project-identity` → `ai-constitution`** -- skill renamed across all 8 directories (4 live IDE mirrors + 4 template copies). Context class name updated from `project-identity` to `constitution` in observability and state systems.

### Removed
- **`instincts/context.md` (spec-090 sub-002)** -- the generated context file is no longer used. Instincts are now consumed directly from `instincts.yml` v2 schema. Context refresh logic (`needs_context_refresh`, `refresh_instinct_context`, `maybe_refresh_instinct_context`) removed from both hook library and state module.
- **`consolidate.py` scripts (spec-090 sub-003)** -- deleted from all 4 IDE mirrors (`.claude/`, `.codex/`, `.gemini/`, `.github/`) and 4 template copies. The v1 consolidation summary script is replaced by the skill's built-in `--review` mode.
- **`contexts/team/lessons.md` content (spec-090 sub-001)** -- content moved to `.ai-engineering/LESSONS.md`. The file now contains only new lessons captured after the migration (autonomous orchestrator patterns).
- **Instincts v1 schema families** -- `toolSequences`, `errorRecoveries`, and `skillAgentPreferences` replaced by v2 families (`corrections`, `recoveries`, `workflows`). Migration path preserves high-evidence entries.

### Added
- **Label-sync infrastructure** -- canonical `.github/labels.yml` defines all labels (type, priority, severity, status, handoff, lifecycle, findings, protected, utility). GitHub Action (`label-sync.yml`) syncs labels on push to main using `EndBug/label-sync@v2.3.3` with SHA-pinned action.

### Changed
- **Label normalization** -- replaced colon-based labels (`type:bug`, `status:ready`, `handoff:ai-eng`) with hyphen-based (`bug`, `status-ready`, `handoff-ai-eng`) across all runbooks, skills, issue templates, and templates. GitHub does not allow colons in label names.
- **GitHub Projects v2 configuration** -- populated `manifest.yml` with real project board field IDs (status, priority, size, estimate, dates), status option IDs, and state mappings. Enables `/ai-board-sync` to move items across project columns.
- **Issue templates simplified** -- removed Size dropdown from bug/feature/task templates (moved to GitHub Projects custom fields). Added `p4-low` priority option to task template.
- **Native IDE directory architecture (spec-087)** -- eliminated the `.agents/` directory entirely; Codex content now lives in native `.codex/` with `hooks.json` and `config.toml`. Gemini hooks rewritten to official nested `matcher/hooks` format with `hooksConfig`. GitHub Copilot hooks added under `.github/hooks/`. Installer, sync script, and validator updated for the new structure.

### Changed
- **ai-eng update UX (spec-081)** -- the update command now presents an install-style preview in interactive terminals, explains protected files with structured reasons, and requires confirmation before applying writes while keeping JSON and non-TTY flows prompt-free.
- **Hook simplification and instinct learning (spec-080)** -- retained hook automation is now focused on `auto-format`, `strategic-compact`, `instinct-observe`, and `instinct-extract`, with project-local instinct artifacts under `.ai-engineering/instincts/` and no `cost-tracker`.

### Added
- **Codex/Copilot instruction parity (spec-080)** -- sync now generates live `.github/instructions/*.instructions.md` surfaces alongside template instructions, keeping language guidance aligned across installed projects and the dogfooded repo.

### Changed
- **Codex governance surfaces (spec-080)** -- instruction counts, provider tables, active integrations, and agent invocation guidance are now derived and mirrored consistently across `CLAUDE.md`, `AGENTS.md`, template instructions, and `.ai-engineering/README.md`.
- **Repo dogfooding config (spec-080)** -- `.ai-engineering/manifest.yml`, install state, and ownership map now model Codex as an active integration and cover project identity in readiness checks.
- **Skill status scanning (spec-080)** -- modern `.claude/` and `.agents/` skill directories only treat `SKILL.md` as executable, while legacy flat markdown scanning remains limited to `.ai-engineering/skills`.

### Fixed
- **Codex provider autodetect (spec-080)** -- installer discovery now recognizes `AGENTS.md` and `.agents/` surfaces as Codex integrations instead of reporting only Claude/Copilot.
- **Agent/skill taxonomy drift (spec-080)** -- `guard`, `explore`, and `simplify` guidance no longer advertises nonexistent slash skills; mirrors now point to direct dispatch where those capabilities are agent-only.
- **Mirror sync integrity (spec-080)** -- generated `AGENTS.md` preserves Claude-specific platform rows, source-of-truth counts, and cross-reference validation for templated skill paths.

### Added
- **Copilot Skills system (spec-077)** -- replaced `.github/prompts/*.prompt.md` (34 files) with native `.github/skills/ai-*/SKILL.md` directory structure (37 skills). Each skill now has its own directory mirroring `.claude/skills/` and `.agents/skills/`. Sync pipeline generates Copilot-native format directly instead of concatenated prompt files.
- **`STYLE_PRESETS.md` for `/ai-slides`** -- reusable style presets for HTML presentation generation.
- **`.ai-engineering/reviews/` directory** -- persistent storage for code review artifacts.

### Removed
- **`.github/prompts/` directory (spec-077)** -- 34 prompt.md files replaced by `.github/skills/` native format. Template mirrors also cleaned.
- **Autopilot sub-specs** -- removed stale `.ai-engineering/specs/autopilot/` (manifest + 8 sub-specs) from completed autopilot v2 execution.
- **`spec-066-hooks-relocation.md`** -- completed spec artifact cleaned up.
- **`health-history.json` + `test_health_history.py` (spec-068)** -- unused state file and its tests removed as part of state unification.
- **Health check signals** -- removed obsolete `health_check_signals` from `src/ai_engineering/lib/signals.py`.

### Changed
- **Sync script → skills output (spec-077)** -- `sync_command_mirrors.py` now generates `.github/skills/ai-*/SKILL.md` directories instead of `.github/prompts/*.prompt.md` files. Template mirrors updated accordingly.
- **Validator mirror sync** -- `mirror_sync.py` validates skills directories across all IDE trees instead of prompt file parity.
- **`test_template_prompt_parity.py` → `test_template_skill_parity.py`** -- renamed and rewritten to validate skill directory parity instead of prompt file byte-equality.
- **Autopilot v2 handlers** -- quality, deep-plan, implement, decompose, orchestrate, and deliver handlers updated across all 3 IDE mirrors (`.claude/`, `.github/`, `.agents/`) with improved parallel execution and convergence loop.
- **All 9 agent instructions updated** -- autopilot, build, explore, guard, guide, plan, review, simplify, verify agents refined for skills-based routing.
- **CODEOWNERS, CLAUDE.md, AGENTS.md, copilot-instructions.md** -- updated references for skills system.

### Fixed
- **`git init -b main` (spec-078)** -- all `git init` calls in installer (`detect.py`, `service.py`), CI workflows (`ci.yml`, `install-smoke.yml`), and test fixtures (`test_install_matrix.py`) now explicitly set default branch to `main`.

### Added
- **Install flow redesign (spec-064)** -- replaced 4 hostile free-text prompts with auto-detection + `questionary` checkbox wizard. Auto-detects stacks (13 markers), AI providers (claude_code, github_copilot), IDEs (.vscode, .idea), and VCS (git remote). Empty repos show wizard with nothing preselected. CLI flags (`--stack`, `--provider`, `--ide`, `--vcs`) skip wizard for automation. Removed CI/CD URL prompt from install.
- **Copilot subagent orchestration (spec-064)** -- full parity with Claude Code multi-agent delegation. 5 orchestrator agents (Autopilot, Build, Plan, Review, Verify) can now delegate to subagents via `agents` property, `handoffs` (guided transitions), and per-agent `hooks`. Sync pipeline injects Copilot-specific properties via `AGENT_METADATA` — canonical `.claude/` sources remain clean. Works across VS Code, CLI, and Coding Agent.
- **`docs/copilot-subagents.md`** -- comprehensive guide covering sync architecture, Copilot properties, usage examples for all 3 environments, capabilities matrix, and handoff chain diagram.
- **DEC-024** -- Copilot subagent orchestration via sync pipeline (architecture decision, active, high criticality).
- **`/ai-autopilot` skill (spec-063)** -- multi-spec autonomous orchestrator that splits large specs into focused sub-specs, executes sequentially with fresh-context agents, verifies anti-hallucination gates, and delivers via PR. 5 phase handlers (split, explore, execute, verify, pr) with `--resume` and `--no-watch` flags.
- **`ai-autopilot` agent** -- 9th agent (orchestrator role), read-only + bash tools, delegates all code changes to subagents.
- **DEC-023 governance override** -- autopilot invocation is approval for the full pipeline; internal gates are automatic with 2-failure stop.
- **ECC integration skills (spec-062)** -- 4 new skills: `/ai-slides` (HTML presentations with style presets, PPT conversion), `/ai-media` (AI media generation via fal.ai), `/ai-video-editing` (FFmpeg + Remotion pipeline), `/ai-eval` (eval-driven development with pass@k metrics). Total skills: 37.
- **Test skill handlers** -- `handlers/e2e.md` (end-to-end testing patterns) and `handlers/tdd.md` (RED-GREEN-REFACTOR cycle) added to `/ai-test`.
- **Write skill handlers** -- `handlers/investor-outreach.md` and `handlers/x-api.md` added to `/ai-write`.
- **Framework contexts** -- 8 new context files: `api-design.md`, `backend-patterns.md`, `bun.md`, `claude-api.md`, `mcp-sdk.md`, `nextjs.md`, `universal.md` (languages), `mcp-integrations.md` (team).
- **Strategic compact hook** -- `scripts/hooks/strategic-compact.py` with Claude Code `Edit|Write|MultiEdit` hook for strategic context management during long sessions.

### Removed
- **`TEST_SCOPE_RULES` system (spec-069)** -- deleted manual test-selection engine (760 LOC, 25 rules), `check_test_mapping.py` integrity script, and all consumers. CI now runs full suite unconditionally per tier with `paths-ignore` for docs-only changes. Suite speed (24s unit, 5m integration) makes selective filtering unnecessary.

### Changed
- **Hooks relocated (spec-066)** -- moved `scripts/hooks/` to `.ai-engineering/scripts/hooks/` for both templates and dogfooding. Updated all path references in settings.json, hooks.json, shell/PowerShell dirname navigation, installer, and tests. Added `_migrate_hooks_dir()` to updater for automatic migration of existing projects.
- **Sync script (`sync_command_mirrors.py`)** -- extended `AgentMeta` dataclass with `copilot_agents`, `copilot_handoffs`, `copilot_hooks` fields; `generate_copilot_agent()` serializes new frontmatter properties for 5 orchestrator agents.
- **Canonical agent instructions** -- replaced `Dispatch Agent(X)` syntax with "Use the X agent" pattern in `ai-autopilot.md` and `ai-build.md`; added "Subagent Orchestration" section to autopilot; added Guard/Explorer delegation references to Build.
- **Copilot instructions** -- added "Subagent Orchestration" section to `.github/copilot-instructions.md` with orchestrator delegation table.
- **Manifest registry** -- skill count 32 -> 37, agent count 8 -> 9, all new skills registered with types and tags.
- **Skill frontmatter validator** -- added `mcp` and `skills` as valid keys in `requires` block.
- **All IDE mirrors updated** -- `.claude/`, `.github/`, `.agents/`, and template mirrors regenerated for all new and modified skills.

### Fixed
- **Autopilot skill cross-platform path bug** -- `.claude/skills/ai-pr/handlers/watch.md` handler path in `phase-pr.md` replaced with `.claude/skills/ai-pr/SKILL.md step 14` (handler paths aren't translated by sync regex).
- **Dispatch skill agent names** -- normalized generic "subagent" references to canonical agent names (`ai-build`, `ai-verify`, `ai-guard`) for consistent cross-platform translation.
- **Mirror sync: 46 handler files added to `.agents/` mirrors** -- write (4), review (8), debug (8), create (3), solution-intent (3) handlers were missing from Codex/Gemini mirrors (root + template). Routing tables referenced nonexistent files.
- **Skill count synced to 32 across all instruction files** -- CLAUDE.md, AGENTS.md, copilot-instructions.md, and template manifest updated. `ai-instinct` added to Meta group and Effort Levels table (max: 8 -> 9).
- **Handler separators in sync script** -- `sync_command_mirrors.py` now inserts `---` between handler sections in concatenated `.prompt.md` files, matching the existing `ai-debug` convention.
- **`deployment-patterns.md` mirror** -- canonical governance context file was missing its template mirror.

### Added
- **`test_handler_routing_completeness`** -- 90 parametrized tests verifying every handler referenced in SKILL.md routing tables exists on disk across all 4 IDE mirror trees.
- **`test_template_prompt_parity`** -- 35 tests ensuring `.github/prompts/` and template prompt files stay byte-for-byte identical.

### Fixed
- **CI false positives eliminated** — Dependabot PRs that change workflow YAML now trigger full CI (paths-filter expanded). Snyk job reports `skipped` instead of vacuous `success` when token is absent. Gate Trailer verification checks ALL non-merge PR commits (not just HEAD). SonarCloud fails when zero coverage reports exist. Semgrep skip ratio capped at 50%.
- **Install Smoke false positives eliminated** — `ai-eng doctor` now exits 0 (ok), 1 (fail), or 2 (warnings only) instead of always 0. `ai-eng version` output validated against expected pattern. Doctor JSON output parsed and asserted. Git config sets `init.defaultBranch main`.

### Added
- **`--non-interactive` flag for `ai-eng install`** — suppresses all 5 interactive prompts, uses defaults. Required for CI smoke tests.
- **Cross-platform Install Smoke** — workflow now runs on ubuntu, windows, and macos (was ubuntu-only).
- **`DoctorReport.has_warnings` property** — True when warnings exist with no failures.
- **Error boundary expansion** — `json.JSONDecodeError` and `pydantic.ValidationError` now caught by CLI error boundary for clean error messages.

### Added
- **CI/CD standards URL in manifest** -- new `cicd.standards_url` field in `manifest.yml` allows teams to reference their CI/CD documentation. `/ai-pipeline generate` reads this URL to produce compliant pipelines; falls back to AI best practices when unset.

### Removed
- **Programmatic pipeline generator** -- removed `installer/cicd.py`, `pipeline/` module (compliance, injector), and `templates/pipeline/` directory. Pipeline generation is now fully AI-driven via `/ai-pipeline`.
- **`ai-eng cicd regenerate` command** -- replaced by `/ai-pipeline generate` as the single entry point for pipeline creation.
- **`ai-eng maintenance pipeline-compliance`** -- compliance checking delegated to `/ai-pipeline validate`.
- **`--no-cicd` flag on `ai-eng vcs set-provider`** -- no longer needed since pipelines aren't auto-generated.
- **Pipeline auto-generation during install** -- `ai-eng install` no longer generates CI/CD pipelines. Users invoke `/ai-pipeline` when ready.

### Added
- **GitHub Copilot hooks parity** — migrated `.github/hooks/hooks.json` from broken flat-array format to Copilot's native `{ version: 1, hooks: { eventType: [...] } }` schema with all 6 hook types: `sessionStart`, `sessionEnd`, `userPromptSubmitted`, `preToolUse`, `postToolUse`, `errorOccurred`.
- **Copilot preToolUse deny-list** — new `copilot-deny.sh` script enforces the same 13 dangerous-operation patterns blocked by Claude Code's `settings.json` (force push, `rm -rf *`, `--no-verify`, etc.) via Copilot's native `preToolUse` hook with `permissionDecision: "deny"` output.
- **Copilot telemetry scripts** — 5 new hook scripts (`copilot-skill.sh`, `copilot-agent.sh`, `copilot-session-start.sh`, `copilot-session-end.sh`, `copilot-error.sh`) emit NDJSON events to `audit-log.ndjson` matching existing Claude telemetry format. Each has a PowerShell fail-open stub.
- **Codex handler parity** — adapted 6 missing handler files for `.agents/skills/` (create: 3, solution-intent: 3) from Claude sources with provider-neutral paths (zero `.claude/` references).
- **Manifest ownership expansion** — `ownership.framework` now includes `.github/agents/**`, `.github/prompts/**`, `.github/hooks/**`, `.github/copilot-instructions.md`, and `.agents/**`.

### Changed
- **copilot-instructions.md** — Observability section now lists all 6 Copilot-native camelCase hook event types instead of old `post_tool_call`/`session_end` naming.

### Added
- **Watch & fix loop for /ai-pr** — step 14 now autonomously monitors PR until merge: diagnoses and fixes failing CI checks, resolves merge conflicts via rebase, and handles review comments (team/org-internal bot = autonomous, external = user confirmation). Polls every 1 min (active) or 3 min (passive). Escalates after 3 failed fix attempts. Full GitHub and Azure DevOps VCS support. New `handlers/watch.md` handler with 7-step procedure.
- **Work items integration** — expanded `manifest.yml` `work_items` section with provider-specific config (Azure DevOps `area_path`, GitHub `team_label`), hierarchy rules (`never_close` for features, `close_on_pr` for user stories/tasks/bugs), and spec frontmatter `refs` for traceability from specs to work items.
- **Sprint review skill** — new `/ai-sprint-review` skill (31st skill) that gathers sprint data from work items and git, generates a python-pptx script with the ai-engineering dark-mode brand, and produces a PowerPoint slide deck for stakeholders.
- **PR work item linking** — `/ai-pr` now reads spec frontmatter `refs` and adds hierarchy-aware work item references to PR descriptions (closes user stories/tasks/bugs, mentions features without closing).
- **Brainstorm work item context** — `/ai-brainstorm` can accept a work item ID to fetch hierarchy (Feature > User Story > Task) from Azure DevOps or GitHub Issues, pre-filling spec refs and reducing interrogation questions.
- **Manifest enforcement** — pre-conditions added to `/ai-sprint`, `/ai-standup`, `/ai-commit`, and `/ai-write` docs handler requiring manifest `work_items` and `documentation` config reads before acting.
- **Recursive README updates** — `documentation.auto_update.readme: true` now explicitly scans ALL README*.md files recursively, updating each in context of its directory.

### Fixed
- **Skill telemetry hook** — replaced `PostToolUse(Skill)` hook with `UserPromptSubmit(/ai-*)` to capture slash command invocations. `PostToolUse(Skill)` never fired because Claude Code expands skills as prompts without calling the Skill tool.
- **Installer copilot template** — removed stale `("copilot", ".github/copilot")` tree mapping from `templates.py` after the `copilot/` template directory was deleted in spec-055.

### Added
- **Dev-setup scripts** — `scripts/dev-setup.sh` (bash) and `scripts/dev-setup.ps1` (PowerShell) for one-command editable install of `ai-eng` as a global tool via `uv tool install`.
- **CI Result gate job** — context-aware `ci-result` aggregator in `ci.yml` that becomes the sole required Branch Protection check. Categorizes jobs as always-required, code-conditional, PR-only, or optional — unblocking docs-only PRs, Dependabot PRs, and external contributions (DEC-054-06).
- **Dependabot auto-lock workflow** — `dependabot-auto-lock.yml` regenerates `uv.lock` when Dependabot updates `pyproject.toml`, eliminating manual lock-file maintenance.
- **CICD standards expansion** — 7 new policy sections in `cicd/core.md`: action version pinning, Dependabot contract, Azure Pipelines standards, reusable components contract, environment protection, concurrency/performance, and required check strategy.
- **Sprint review presentation** — `generate_sprint_review.py` produces a 12-slide dark-mode `.pptx` covering Feb 16 - Mar 16, 2026 sprint (architecture v3, IDE mirrors, observability, security, testing, CI/CD, quality metrics, governance surface, risks, and next sprint).
- **Telemetry hooks** — 4 cross-platform scripts (`telemetry-session.sh/ps1`, `telemetry-skill.sh/ps1`) emit `session_end` and `skill_invoked` events automatically via Claude Code `PostToolUse(Skill)` and `Stop` hooks.
- **Guard telemetry** — `guard_advisory`, `guard_gate`, and `guard_drift` event emitters in `audit.py` with matching aggregators in `signals.py` for guard-mode observability.
- **Common installer templates** — `.gitleaks.toml` and `.semgrep.yml` now deploy to every target project regardless of AI provider; `scripts/hooks/` deploys observability hooks for all providers.
- **Project scaffolding templates** — `CODEOWNERS`, `dependabot.yml`, SonarQube MCP instructions, and VCS hook configs added to the project template set.
- **Telemetry canary test** — integration test verifying end-to-end hook telemetry emission.
- **Audit auto-enrichment** — events now auto-attach `spec_id` and `stack` from project context, plus `duration_ms` on gate and scan events, eliminating manual field wiring.
- **Agent telemetry hooks** — `telemetry-agent.sh/ps1` scripts for agent dispatch event emission.
- **Gate duration tracking** — `run_gate()` now measures and emits `duration_ms` on every gate event for performance observability.
- **Validate sync mode** — `ai-eng validate --mode sync` checks all mirrors are up-to-date (moved from separate `ai-eng sync --check`).

### Changed
- **Pipeline skill v2** — comprehensive rewrite with GitHub Actions (12 sections: CI result gate, reusable workflows, composite actions, SHA pinning, concurrency, matrix, caching, environments, merge queue, badges, Dependabot) and Azure Pipelines (11 sections: template composition, manager pattern, variable groups, KeyVault, environment gates, deployment strategies, SonarCloud, artifact promotion, branch-conditional deployment, self-hosted agents) at full parity.
- **Dependabot config** — added `commit-message.prefix` for conventional commits (`chore(deps)`, `chore(deps-dev)`, `ci(deps)`).
- **Installer template maps** — removed legacy Copilot instruction file maps, added `_COMMON_FILE_MAPS` and `_COMMON_TREE_MAPS` for provider-agnostic deployment, moved Copilot subtrees to tree maps.
- **Observe dashboard** — guard advisory and drift metrics added to the AI dashboard mode.
- **Evolve skill** — updated across all IDE mirrors (Claude, Copilot, Agents).
- **Instruction files** — added Observability section to `CLAUDE.md` and `copilot-instructions.md` documenting automatic telemetry hooks.
- **Checkpoint command removed** — `ai-eng checkpoint` CLI subgroup deleted; checkpoint state file removed from defaults.
- **Observe simplified** — removed `session_metrics_from` and `checkpoint_status` aggregators; observe modes streamlined to use direct event queries.
- **Audit emitters consolidated** — `emit_session_event` removed; replaced by richer auto-enriched event model with `_enrich()` helper.
- **Agent/skill mirrors updated** — all 8 agents and governance-related skills refreshed across Claude, Copilot, and Agents IDE mirrors.

### Removed
- **Legacy evals directory** — `templates/.ai-engineering/evals/` (README.md, benchmarks, registry.json) removed.
- **Legacy semgrep location** — `templates/.semgrep.yml` relocated to `templates/project/.semgrep.yml`.
- **Checkpoint CLI** — `ai-eng checkpoint save/load/status` commands removed (session-checkpoint.json deleted).

### Added — Architecture v3 (spec-051)
- **3 new agents** — guard (proactive governance), guide (developer growth), operate (SRE/runbooks).
- **7 new skills** — guard, dispatch, guide, onboard, evolve, ops, lifecycle.
- **Self-improvement mechanism** — evolve skill analyzes audit-log and proposes improvements.
- **Guard integration** — guard.advise runs as post-edit validation step in build agent.
- **Feature gap reviewer** — verify.gap `--framework` mode audits promise vs reality.
- **Agent-model standard** — new governance standard defining dispatch protocol and context handoff.

### Changed — Architecture v3 (spec-051)
- **Agent renames** — scan→verify, release→ship (clearer developer communication).
- **Skill renames** — build→code, db→schema, cicd→pipeline, a11y→accessibility, feature-gap→gap, code-simplifier→simplify, perf→performance, docs→document, observe→dashboard, product-contract→contract, work-item→triage.
- **Skill merges** — create+delete merged into lifecycle.
- **5 stub skills expanded** — security (58→216L), quality (45→175L), governance (48→153L), build (45→257L), perf (46→150L).
- **Explain skill reassigned** — from orphan to guide agent (primary owner).
- **All 5 runbooks** — assigned `owner: operate` in frontmatter (consolidated from 13).
- **Agent count**: 7→10. **Skill count**: 35→40.
- **IDE adapters** — all Claude commands, Copilot prompts, and Copilot agents renamed to match new skill/agent names. 7 new command files created.
- **Template mirror** — full sync of 10 agents, 40 skills, 5 runbooks, standards, and IDE adapters to `src/ai_engineering/templates/`.
- **Contracts rewritten** — framework-contract.md (10 agents, dispatch schema, guard integration, evolve loop) and product-contract.md (v0.3.0, updated roadmap and KPIs).

### Fixed
- **Dependabot CI gate** — exempted `dependabot[bot]` from `verify-gate-trailers` check; Dependabot creates commits server-side and cannot satisfy the local hook trailer requirement (DEC-020).
- **Dependabot PR noise** — grouped all dependency updates by ecosystem (pip, github-actions) to consolidate ~7 individual PRs into max 2 per week.

### Fixed — Architecture v3 (spec-051)
- **Sonar BLOCKER** — path traversal validation in checkpoint.py (S5145).
- **CI manifest check** — support `governance_surface` nested structure.
- **Test mapping** — 3 unmapped test files added to scope rules.
- **Instruction file counts** — updated "Skills (35)" → "(40)" and "Agents (7)" → "(10)" in all 8 IDE instruction files.

### Changed
- **Release zero-rebuild** — `release.yml` no longer rebuilds the package; instead downloads the CI-validated `dist/` artifact and publishes it directly to PyPI and GitHub Releases, guaranteeing bit-identical output between CI and release.
- **CI artifact retention** — `dist/` artifact in CI now has `retention-days: 5` to ensure availability for release workflow.
- **Release CI verification** — new `verify-ci` job in release workflow checks CI status with retry/backoff before proceeding (handles race condition when tag pushed before CI finishes).
- **Observe Rich dashboards** — all 5 `ai-eng observe` modes now render with Rich-formatted output (progress bars, score badges, color-coded metrics, section headers) instead of raw markdown strings.
- **Observe dual-output** — `ai-eng observe <mode> --json` outputs structured JSON via SuccessEnvelope with HATEOAS next actions; human output goes to stderr per CLIG.
- **Observe data-first architecture** — mode functions return structured dicts enabling both JSON and Rich rendering from the same data.
- **4 new cli_ui primitives** — `section()`, `progress_bar()`, `score_badge()`, `metric_table()` added to the shared CLI output module for dashboard rendering.
- **Slim root instructions** — deduplicated CLAUDE.md (-64%), AGENTS.md (-53%), and copilot-instructions.md (-47%); all duplicated content now lives in `framework-contract.md` or `product-contract.md`.
- **On-demand contract loading** — plan agent, spec skill, and PR skill now explicitly read product/framework contracts when needed.
- **Validator pointer format** — counter-accuracy and instruction-consistency validators support pointer format and use `product-contract.md` as canonical source.

### Added
- **Snyk optional CI/CD integration** — new `snyk-security` job in CI workflow runs `snyk test` (dependency vulnerabilities), `snyk code test` (SAST), and `snyk monitor` (continuous monitoring on main). All steps conditional on `SNYK_TOKEN` secret; non-gating (`continue-on-error: true`). Registered as optional tool in `manifest.yml` and documented in CI/CD standards and security skill.
- **Skill & agent telemetry** — cross-IDE usage tracking via `ai-eng signals emit skill_invoked` and `agent_dispatched` directives in all 35 skills and 7 agents; new `skill_usage_from()` and `agent_dispatch_from()` aggregators; observe team/ai dashboards now show Skill Usage, Agent Dispatch, and Skill & Agent Efficiency sections.
- **Emit infrastructure** — gate events now include `fixable_failures` field tracking auto-fixable check failures (ruff-format, ruff-lint); `noise_ratio_from()` aggregator computes noise ratio from gate history.
- **Enriched session events** — checkpoint save now passes spec ID, task progress, and skills context to `emit_session_event()` instead of bare `checkpoint_saved=True`.
- **Team dashboard expansion** — Token Economy and Noise Ratio sections show session token usage and gate failure quality metrics.
- **AI dashboard enrichment** — Context Efficiency now shows average tokens per session.
- **Health score: Gate signal quality** — noise ratio (inverse) added as optional health component; high noise lowers health score.
- **Observe enrichment phase 2** — Security Posture, Test Confidence, and enriched SonarCloud sections in engineer and health dashboards with multi-source fallback chains (SonarCloud → local tools → defaults).
- **SonarCloud measures expansion** — `query_sonar_measures()` calls `/api/measures/component` for coverage, complexity, duplication, and vulnerability metrics with module-level caching.
- **Test confidence with fallback** — `test_confidence_metrics()` resolves coverage from SonarCloud → `coverage.json` → `test_scope` mapping → defaults.
- **Security posture with fallback** — `security_posture_metrics()` resolves vulnerabilities from SonarCloud → `pip-audit` → defaults.
- **Session emitter wired** — checkpoint save now emits `session_metric` audit events automatically.
- **Health trend tracking** — `observe health` persists weekly snapshots to `state/health-history.json` (rolling 12 entries) and shows ↑↓→ direction indicators.
- **Smart actions with score gain** — `observe health` replaces hardcoded actions with dynamic recommendations based on weakest components, showing estimated point gains.
- **AI self-optimization hints** — `observe ai` detects patterns (low decision reuse, high gate failures, missing checkpoints) and surfaces actionable suggestions.

### Fixed
- **Install UX: VCS alias** — `ai-eng install --vcs azdo` now accepted as shorthand for `azure_devops`; normalizes internally, displays `azdo` in output.
- **Install UX: clean output** — removed inline branch policy guide text from install output; guide accessible via `ai-eng guide`.
- **Install UX: platform filtering** — platform setup no longer offers the opposite VCS provider (e.g., Azure DevOps when GitHub is selected).
- **Install UX: Sonar URL normalization** — Sonar token validation now strips path from user-entered URLs before API call; helpful error on JSON parse failure.
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
- **Legacy IDE command files** — `.claude/commands/{cleanup,commit,pr}.md` and `.github/prompts/{cleanup,commit,pr}.prompt.md` removed (slash commands via `/ai-<name>` are the canonical path).

### Added
- **`product-contract` skill** — new skill (`/ai-product-contract`) for maintaining product contract documents in sync mode; includes Claude command, Copilot prompt, and Codex agent adaptors.
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
- **Automation runbooks** — 5 operational runbooks (`.ai-engineering/runbooks/*.md`): code-simplifier, dependency-upgrade, governance-drift-repair, incident-response, security-incident. Recurring automation moved to GitHub Agentic Workflows.
- **GitHub issue/PR templates** — bug, feature, task issue forms (`.github/ISSUE_TEMPLATE/*.yml`) and PR template (`.github/pull_request_template.md`); blank issues disabled.
- **VCS-aware installer** — `copy_project_templates()` accepts `vcs_provider` parameter; GitHub platform copies issue/PR templates automatically.
- **Issue Definition Standard** — `work-item` skill extended with required fields, priority mapping (P0→p1-critical), size guide (S/M/L/XL), and spec URL format.
- **Platform Adaptors + Runbooks in AGENTS.md** — new sections documenting adaptor paths/counts and runbook layers/schedules.
- **Manifest governance surface** — `runbooks/**` framework-managed, `.agents/**` + GitHub templates external-framework-managed, `issue_standard` schema.

### Changed
- **Agent/skill shared-rule normalization** — `plan`, `observe`, and `write/docs` now use canonical shared rules in skills (`PLAN-*`, `OBS-*`, `DOC-*`) with agent contracts referencing rules instead of duplicating procedures.
- **Plan no-execution enforcement** — `/ai-plan` contract now explicitly maps to `PLAN-B1` and requires handoff to `/ai-execute` for execution.
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
- **`plan` skill** — standalone planning skill (`/ai-plan`) with input classification, pipeline strategy, and spec creation.
- **`/ai-plan` and `/ai-execute` command contract** — plan pipeline (classify → discover → risk → spec → execution plan → STOP) and execute dispatcher documented in CLAUDE.md.
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
- **Minimalist command descriptions** — rewrote first line of all 53 `/ai-*` command files (`.claude/commands/ai/*.md`) with short, actionable descriptions that display in autocomplete. Synchronized descriptions to `.github/prompts/ai-*.prompt.md` frontmatter, template mirrors, and both `GEMINI.md` files.
- **Command Contract added to GEMINI.md** — inserted `## Command Contract` section in root and template `GEMINI.md` matching the existing section in `CLAUDE.md`.
- **Provider-aware templates** — `copy_project_templates` and `remove_provider_templates` now operate per-provider with shared-file deduplication (e.g., AGENTS.md shared by copilot/gemini/codex).
- **Schema version 1.2** — `InstallManifest` adds `aiProviders` config with `primary` and `enabled` fields, and `deferredSetup` to `operationalReadiness`.
- **Security tool auto-install** — install attempts `ensure_tool()` for gitleaks and semgrep before falling back to manual step instructions.
- **Branch policy guide repositioned** — guide now appears after suggested next steps with clearer messaging about manual configuration requirement.
- **`/ai-plan` spec creation enforced** — plan agent pipeline step 4 (spec creation) marked as MANDATORY to ensure traceability.

### Removed
- **`GEMINI.md` template** — Gemini CLI reads `AGENTS.md` natively. Removed dedicated `GEMINI.md` template and ownership entry.
- **Branch policy guides moved to console output** — install no longer creates `.ai-engineering/guides/` directory. Guide text is shown inline during install and stored in the manifest for `ai-eng guide` retrieval.

### Added
- **3 new skills** — `work-item` (Azure Boards + GitHub Issues bidirectional sync), `agent-card` (platform-portable agent descriptors for Copilot/Foundry/AgentKit/Vertex), `triage` (auto-prioritization with p1/p2/p3 rules and throttle at 10+ open items).
- **`ai-scan` agent** — feature scanner that cross-references specs against code to detect unimplemented features, architecture drift, missing tests, dead specifications, and dependency gaps.
- **`ai-triage` agent** — auto-prioritization agent that scans work items using priority rules (security > bugs > features > perf > tests > arch > dx).
- **`ai-plan` planning pipeline** — default 6-step pipeline: triage check → discovery → prompt design → spec creation → work-item sync → dispatch.
- **`ai-review` individual modes** — 14 review modes invokable individually: `security`, `performance`, `architecture`, `accessibility`, `quality`, `pr`, `smoke`, `platform`, `release`, `dx`, `integrity`, `compliance`, `ownership`.
- **Work-item integration** — manifest.yml `work_items` section supporting GitHub Issues and Azure Boards with bidirectional spec sync and auto-transition.
- **Discovery interrogation skill** (`discover`) — structured requirements elicitation through 8-dimension completeness checks, 5 Whys probing, and KNOWN/ASSUMED/UNKNOWN classification.
- **Architecture patterns table** in product-contract.md section 7.4 — documents scanner/executor separation, single-system-multiple-access-points, finding deduplication, context threading, progressive disclosure, and mode dispatch patterns.
- **Performance and Security growth headers** added to 8 thin stack standards (react-native, astro, nextjs, node, typescript, nestjs, rust, react) as future extension points.

### Changed
- **Skill frontmatter schema aligned** — moved `version` and `tags` from top-level frontmatter keys to `metadata.version` and `metadata.tags` across all 47 skills and template mirrors for stricter Anthropic guide compatibility.
- **Top skill usage examples added** — added `## Examples` sections to 10 frequently used skills (`commit`, `cleanup`, `spec`, `pr`, `code-review`, `test-run`, `debug`, `audit`, `release`, `discover`) and mirrored templates.
- **Validator compatibility updated** — integrity validator now accepts skill version from `metadata.version` (with backward compatibility), preserving `skill-frontmatter` checks after schema alignment.
- **Agent scope model refined** — `ai-review` and `ai-scan` now use `read-write (work items only)` scope to create/sync follow-up work items in Azure Boards or GitHub Issues/Projects while keeping code and governance content non-editable by these agents.
- **Review/scan behavior contracts updated** — agent definitions and template mirrors now include explicit work-item synchronization steps via `skills/work-item/SKILL.md`, preserving finding-to-work-item traceability.
- **README governance section expanded** — added the full skills table (47 skills) under the Skills section and aligned agent scope text with the updated non-code work-item write model.
- **Consolidated 19 agents to 6** — `ai-plan` (orchestration + planning pipeline), `ai-build` (implementation across all stacks, merges 8 agents), `ai-review` (reviews + governance, merges 6 agents), `ai-scan` (feature scanner), `ai-write` (documentation), `ai-triage` (auto-prioritization). Only `ai-build` has code write permissions.
- **Flat skill organization** — restructured 44 skills from 6 nested categories (`workflows/`, `dev/`, `review/`, `docs/`, `govern/`, `quality/`) to flat `skills/<name>/` layout. Added 3 new skills for 47 total. Removed `category` from frontmatter schema; replaced with optional `tags` array.
- **Unified `ai-` command namespace** — replaced 7 prefixes (`dev:`, `review:`, `docs:`, `govern:`, `quality:`, `workflows:`, `agent:`) with single `ai-` prefix. All slash commands now use `/ai-<name>` format.
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
- **7 command prefixes** — `dev:`, `review:`, `docs:`, `govern:`, `quality:`, `workflows:`, `agent:` replaced by unified `ai-` prefix.
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
