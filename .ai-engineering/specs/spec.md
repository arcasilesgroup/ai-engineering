---
spec: spec-133
slug: surface-primitive-rearch
title: spec-133 — Surface Primitive Re-architecture (CLI UX + Cross-IDE)
status: approved
approved_at: 2026-05-12
approved_by: operator
effort: large
branch: spec-128/context-overrides-refactor
pr: arcasilesgroup/ai-engineering#509
target_dispatch: /ai-autopilot
source_brief: .ai-engineering/specs/drafts/cli-ux-cross-ide-rearch-brief.md
chains_after: spec-132 (CLI UX & Architecture Overhaul — same PR aggregate)
---

## Summary

ai-engineering today installs but breaks on first skill use across every supported IDE: 9 root framework scripts referenced by skills are never deployed to the consumer's `.ai-engineering/scripts/` template tree (`session_bootstrap.py`, `spec_lifecycle.py`, `commit_compose.py`, `branch_slug.py`, `doc_gate.py`, `pr_body_compose.py`, `runtime_rotate.py`, `regenerate-hooks-manifest.py`, `plan_tasks.py`). The installer wizard asks 4 questions where 2 (`providers.ides` + `ai_providers.enabled`) are conceptually orthogonal but semantically coupled — operators install Claude Code as a unit, never "claude-code AI provider" + "terminal IDE" separately. Antigravity, OpenCode, and Cursor are declared in `_KNOWN_IDES`/`_IDE_POPULARITY` but lack any provider entry, tree, or hook adapter; all three are silently unsupported. CLI verbs duplicate skill scopes (`ai-eng verify` vs `/ai-verify`; `ai-eng guide` vs `/ai-guide`; `ai-eng maintenance branch-cleanup` vs `/ai-cleanup`) without a disambiguation contract. The hexagonal layer contract whitelists 4 baseline import-linter ignores (`cli_ui → updater`, `updater → installer.templates`, `policy.checks.stack_runner → installer.launchers`, `validator._shared → installer.templates`) plus 6 in-band CLI hex violations (sqlite/typer/print interleaved with business logic). The `.ai-engineering/` tree carries 4 orphaned directories that survived prior refactors: `adapters/` (post-rename), `contexts/frameworks/` (15 files, spec-128 D-128-01 declared deleted but never executed), `contexts/languages/` (14 files, same), `.claude/skills/ai-debug/handlers/` (8 stack-routed files duplicating `overrides/<stack>/`) and `.claude/skills/ai-review/handlers/` (10 stack-routed `lang-*.md` files, same anti-pattern). On a greenfield install (`stacks=[]`) doctor silently coerces to `["python"]` and emits false-positive warnings; if a user later adds project markers (`Cargo.toml`, `pyproject.toml`, `*.csproj`, etc.) and forgets `ai-eng doctor --fix`, the toolchain (pytest/pip-audit, vitest/npm-audit, cargo test/cargo-audit, dotnet test/dotnet list package --vulnerable, etc.) silently never runs.

The cure is a conceptual reframe: collapse "AI Provider" and "IDE Integration" into a single first-class domain primitive — the **Surface** — and rebuild the installer, manifest, wizard, and mirror-sync around that primitive. Hexagonal layering becomes enforceable (zero-whitelist). The wizard collapses to one question. OpenCode and Cursor become full surfaces wired to hook adapters (evidence-anchored: OpenCode plugin API, Cursor 1.7+ native hooks). Antigravity stays mirror-only (Google upstream confirmed workaround-only). 9 root scripts deploy to templates. Stack content consolidates: `.ai-engineering/overrides/<stack>/` is the **single canonical home** for stack-specific guidance — skill `handlers/<stack>.md` is deleted as a DRY violation. 4 orphaned directories purged. Greenfield mode robust end-to-end. Quality bar: every new CLI verb + deterministic primitive is production-grade (idempotent, exit-coded per category, audit-event-emitting, `--json` structured, `--dry-run` universal, TDD per mode). Delivered on branch `spec-128/context-overrides-refactor`, joining the active PR #509 aggregate (spec-128 + spec-129 + spec-131 + spec-132). No new branch, no new PR. Hard renames, hard deletes, no backwards-compat shims per CONSTITUTION + hard-rule §13.3.

## Goals

### Functional goals (acceptance-verifiable)

1. **7 Surfaces install standalone.** `ai-eng install --surface <ID>` succeeds end-to-end for each of: `claude-code` (full), `codex` (full), `gemini-cli` (full), `github-copilot` (full), `opencode` (full, hook adapter), `cursor` (full, hook adapter), `antigravity` (mirror-only). Verified by `tests/integration/installer/test_install_per_surface.py` 7-surface matrix.
2. **Wizard collapses to 1 question.** `wizard.py` prompts only "Which Surface(s) do you use?" (multi-select from `_SURFACE_REGISTRY`). Stack and VCS are silent auto-detect with `--stack` / `--vcs` overrides. Verified by golden snapshot `tests/unit/installer/test_wizard.py`.
3. **`ai-eng cleanup` covers 90-100% of git branch cleanup.** Top-level command with subcommands `branches` (7 modes: `--pruned`/`--merged`/`--squashed`/`--stale`/`--untracked`/`--reset`/`--all`), `runtime`, `specs`, `all`. Universal flags `--dry-run`/`--json`/`--strict`/`--tracked`. Honors `gt.exclude` config + manifest `cleanup.protected_branches`. Refuses detached HEAD; never deletes HEAD. Verified by per-mode unit tests + integration `tests/integration/cli/test_cleanup_branches.py`.
4. **`ai-eng guide` DELETED.** `/ai-guide` is the canonical onboarding surface. Verified by absence in `tests/unit/cli/test_help_snapshots.py`.
5. **`ai-eng verify` preserved.** Doc clarifies scope distinction vs `/ai-verify` skill (skill = LLM 4-specialist orchestration; CLI = deterministic gate). No rename. Same engine + `--json` contract locked. Verified by `tests/architecture/test_surface_parity.py`.
6. **Surface Axiom + No-Twin Axiom documented.** `CLAUDE.md` §16 (new section) carries A1 (expose CLI iff scriptable ∧ deterministic ∧ structured-output-capable) + A2 (same verb iff same engine + identical contract). `tests/architecture/test_surface_parity.py` enforces.
7. **Help-on-empty universal.** Every `ai-eng <group>` (`spec`, `audit`, `risk`, `decision`, `issue`, `maintenance`, `skill`, `setup`, `config`, `gate`, `cleanup`) prints `--help` when invoked without subcommand. Verified by parametrised test iterating `app.registered_groups`.
8. **Manifest schema hard-migrated.** `surfaces.enabled: list[str]` replaces `providers.ides` + `ai_providers.enabled` + `ai_providers.primary`. Closed enum: `{claude-code, codex, gemini-cli, github-copilot, opencode, cursor, antigravity}`. Framework's own `.ai-engineering/manifest.yml` rewritten. Verified by `tests/unit/config/test_manifest_surface_schema.py`.
9. **9 root framework scripts deployed.** `src/ai_engineering/templates/.ai-engineering/scripts/` carries all 9 root scripts (including `plan_tasks.py` — NOT orphan, has 2 callers in `/ai-autopilot`). Installer phase `ScriptsPhase` deploys full tree. Pristine-install smoke per Surface verifies `/ai-start` exits 0 immediately post-install.
10. **`.ai-engineering/overrides/` carries 12 stacks + `_shared/sql.md`.** T1 (8): python, typescript, go, rust, java, csharp, kotlin, swift. T2 (4): php, ruby, flutter, react-native. Cross-cut: `_shared/sql.md`. Each stack carries `conventions.md`, `security_floor.md`, `tdd_harness.md` (+ `examples/` where applicable). Verified by `tests/unit/overrides/test_stack_inventory.py`.
11. **4 orphan directories purged.** `.ai-engineering/adapters/`, `.ai-engineering/contexts/frameworks/`, `.ai-engineering/contexts/languages/`, `.claude/skills/ai-debug/handlers/`, `.claude/skills/ai-review/handlers/` deleted. Mirror-sync regenerates Surface trees without these paths.
12. **`/ai-explore` skill created.** Thin-wrapper `.claude/skills/ai-explore/SKILL.md` dispatches the existing `.claude/agents/ai-explore.md` agent. Sync mirrors propagate (subject to `applies_to_surfaces`).
13. **OpenCode + Cursor hook adapters.** `.ai-engineering/scripts/hooks/opencode-hook-bridge.ts` (TS plugin shim) + `.ai-engineering/scripts/hooks/cursor-hook-bridge.py` (stdio JSON). Both emit `framework-events.ndjson` envelopes (`engine: "opencode"` / `engine: "cursor"`). 11 canonical hook events mapped per Surface.
14. **Mirror sync targets added.** `scripts/sync_mirrors/{opencode_target,cursor_target,antigravity_target}.py`. `applies_to_surfaces` SKILL.md frontmatter (B12) filters per-Surface restrictions. `ai-analyze-permissions` declares `applies_to_surfaces: [claude-code]`; non-Claude Surfaces carry 47 skills (48 minus claude-only).
15. **B16 greenfield robustness end-to-end.** (a) `doctor/phases/tools.py` drops `or ["python"]` coercion; (b) `ai-eng doctor --fix` opt-in updates manifest + reinstalls toolchain on stack-drift finding; (c) `default.md` handlers in `ai-debug` and `ai-pipeline` (now stack-agnostic via overrides); (d) CLI middleware on every `ai-eng <cmd>` emits structured stack-drift warning, `AIENG_STACK_DRIFT_STRICT=1` blocks commit/pr/gate; (e) structured exit-code-78 contract + `/ai-commit` + `/ai-pr` SKILL.md "Stack drift recovery" subsection. 13 stack markers covered by deterministic test; 6 stacks (python/typescript/rust/csharp/go/java) covered by AI eval `evals/cli-ux-cross-ide/test_drift_recovery_flow.md`.
16. **`cli_ui.skill_ref()` helper + lint.** Zero naked `/ai-<name>` literals in CLI output paths. `tools/skill_lint/checks/cli_output_skill_refs.py` AST-walks `cli_commands/` + `cli_ui/` + `phases/` and fails on violations.
17. **Hex contract zero-whitelist.** `pyproject.toml` `[tool.importlinter] ignore_imports` empty. Domain ports introduced: `ManifestPort`, `OutputPort`, `ConfirmPort`, `AuditStorePort`. 6 in-band CLI hex violations unwound (`core.py:366-381` sqlite3, `core.py:344` raw `print`, `core.py:519-557` typer-interleaved confirms, `spec_cmd.py:133` click.echo, `spec_cmd.py:84` filesystem write, `audit_cmd.py:38` sqlite3 module-level). Verified by `tests/architecture/test_hexagonal.py` exit 0.
18. **Surface domain primitive.** `src/ai_engineering/domain/surface.py` `Surface` frozen dataclass + `_SURFACE_REGISTRY` constant for 7 Surfaces. Zero infrastructure imports in `domain/`. Verified by import-linter contract.
19. **Cursor `.cursor/rules/`.** 47 skills (or 46 per `applies_to_surfaces`) as `.mdc` files regenerated from `.claude/skills/<name>/SKILL.md` by sync_mirrors. Plus topic-level rules from canonical CLAUDE.md payload (§10 principles, hot-path discipline, hooks summary).
20. **Cursor MCP deferred.** No `.cursor/mcp.json` shipped this spec (out-of-scope per Q8).

### Quality goals

21. **TDD throughout.** Every code-bearing task RED → GREEN → REFACTOR. New test count ≥ 120 (Surface domain 10 / port adapters 14 / cleanup CLI 35 / scripts deployment 8 / per-surface install 14 / wizard golden 4 / manifest schema 6 / overrides inventory 12 / hook adapters 8 / mirror sync targets 9).
22. **Production-grade quality bar** for all new CLI verbs / deterministic primitives: idempotent (running twice = no-op second time), exit-coded per category (0=clean / 1=found-and-acted / 2=blocked-by-protection / 78=stack-drift), audit-event-emitting (one event per deletion / install / repair via `OutputPort`), `--json` structured output universal, `--dry-run` universal where state-changing, refuse detached HEAD, never delete current branch.
23. **`/ai-review --full` clean.** Zero BLOCKER findings, zero unresolved CRITICAL after one converge round per D-131-05.
24. **`/ai-verify --full` ≥ 95.** Governance + architecture + feature dimensions.
25. **CHANGELOG documents every break.** `[Breaking changes]` section enumerates: manifest schema hard-migration, `ai-eng guide` deletion, `ai-eng maintenance branch-cleanup` → `ai-eng cleanup`, `--ide`/`--provider` → `--surface` flag rename, 4 orphan directories deleted, ai-debug/ai-review handlers consolidated to overrides, new Surfaces (OpenCode/Cursor full + Antigravity mirror-only).
26. **Hot-path budgets preserved.** Pre-commit < 1s, pre-push < 5s. Verified by `tests/perf/test_hotpath_budgets.py`.

## Non-Goals

The following are explicitly OUT OF SCOPE for spec-133. Track as follow-ups if value justifies.

1. **Skill + agent naming reform** (B8 + B14 from brief). `ai-gtm`, `ai-board`, `ai-eval`, `ai-note`, `ai-observe`, `ai-learn`, `ai-prompt`, `ai-standup`, `verify-deterministic` agent — operator-locked deferred 2026-05-12. CLI verb renames stay in scope; skill/agent renames defer.
2. **JetBrains-as-Surface, terminal-as-Surface, Aider, Continue.** User editors without a framework-driveable instruction surface. Add only when an operator request lands.
3. **Cursor MCP wiring (`.cursor/mcp.json`).** Deferred to follow-up unless explicit operator request.
4. **Standalone `dart` overrides bucket.** Subsumed by `flutter` per evidence (Flutter docs ship combined Flutter+Dart; Aider repo has `flutter/` with no separate `dart/`).
5. **`javascript` standalone overrides.** Collapses into `typescript` (no operator signal for plain JS).
6. **`elixir` overrides.** Marker stays in autodetect for future `doctor --fix`; no override directory pre-created.
7. **Physical mass relocation** of `src/ai_engineering/` flat tree to `core/` + `adapters/` layout. spec-132 sub-005 landed the import-linter contract + scaffold; layout migration deferred to a follow-up spec.
8. **Renaming `ai-eng verify` to `ai-eng gate verify` or merging into `ai-eng check`.** Operator-locked Q1=C: verb stays, doc clarifies scope vs `/ai-verify` skill.
9. **New hook events.** The 11 canonical hook events stay (D-122-27, CI-guarded).
10. **`/ai-explore` agent rename or capability expansion.** Skill is a thin wrapper only.

## Decisions

### D-133-01 — `ai-eng verify` preserved; no rename
Operator-locked Q1=C. `ai-eng verify` keeps top-level placement. `/ai-verify` skill remains the LLM 4-specialist orchestration surface. Documentation in `CLAUDE.md` + `docs/cli-reference.md` explicitly distinguishes scopes (deterministic gate vs LLM judgment). Locks shared engine + `--json` contract via `tests/architecture/test_surface_parity.py` so future drift fails CI.

**Rationale**: scope difference is real; rename would not eliminate confusion, only relocate it. Documentation + parity test resolve the B17 risk without surface churn.

### D-133-02 — `ai-eng guide` DELETED entirely
Operator-locked Q2. Hard removal from `cli_factory.py:263` + `cli_commands/guide.py` handler. `/ai-guide` skill is the canonical onboarding surface. No rename to `ai-eng policy show` (operator declined). Branch-policy setup logic, if useful from shell, is relocated to `ai-eng setup` subgroup.

**Rationale**: `/ai-guide` is interactive, AI-judgment-heavy (architecture tour, decision archaeology) — fails Surface Axiom A1 (no scriptable shell use case). No deterministic primitive to expose.

### D-133-03 — `ai-eng cleanup` 7-mode git-trim taxonomy
Operator-decided. Replaces `ai-eng maintenance branch-cleanup`. Top-level command `ai-eng cleanup` with subcommands `branches` (7 modes: `--pruned`/`--merged`/`--squashed`/`--stale`/`--untracked`/`--reset`/`--all`), `runtime` (calls `runtime_rotate.py`), `specs` (calls `spec_lifecycle.py consolidate_shipped`), `all` (composite). Universal flags `--dry-run`, `--json`, `--strict`, `--tracked`, `--force`. Protected-branches via `gt.exclude` git config + manifest `cleanup.protected_branches`. Refuses detached HEAD; never deletes current branch.

**Rationale**: Context7 evidence (git-trim taxonomy `/jasonmccreary/git-trim` + git-scm docs) confirms 7 modes are the complete set of canonical branch-cleanup scenarios. Squash-merge detection (via `merge-base` + `commit-tree`) catches GitHub/GitLab "Squash and merge" branches that `git branch --merged` misses — the operator's specific concern.

### D-133-04 — Surface Axiom (A1) + No-Twin Axiom (A2) documented in `CLAUDE.md` §16
**A1:** A capability MAY expose a `ai-eng <verb>` CLI iff (scriptable from shell/CI) ∧ (deterministic happy-path needs zero AI judgment for default args) ∧ (output is structured-machine-readable). Otherwise it lives only as a skill. **A2:** A capability has one canonical surface per role. Skill = chat entry; CLI = shell entry. Same verb iff same engine + identical contract; distinct verbs otherwise.

**Rationale**: prevents skill/CLI confusion (B17 root cause) at the design layer, not just the lint layer. `/ai-start` is a deterministic display, not data — fails A1.c, correctly remains skill-only. `/ai-cleanup` skill orchestrates AI judgment over the deterministic `ai-eng cleanup` CLI — distinct verbs by A2 design.

### D-133-05 — Help-on-empty universal
Every `ai-eng <group>` (`spec`, `audit`, `risk`, `decision`, `issue`, `maintenance`, `skill`, `setup`, `config`, `gate`, `cleanup`) prints `--help` when invoked with no subcommand. Implemented via `@no_args_help` decorator (spec-132 sub-003 carried universal version; this spec extends to remaining groups).

**Rationale**: surfaces should self-document per §10.7 Clean Code.

### D-133-06 — OpenCode + Cursor = FULL Surfaces; Antigravity = MIRROR-ONLY
Evidence-anchored (research artifact `.ai-engineering/research/ide-hook-engines-2026-05-12.md`). OpenCode exposes plugin API (`tool.execute.before`/`after`, `session.*`, 25+ events) + `.opencode/commands/` slash commands + `opencode run` non-interactive CLI. Cursor 1.7+ ships native hooks beta (`preToolUse`, `postToolUse`, `sessionStart`, `beforeShellExecution`, etc. with stdio JSON contract). Antigravity (Google) explicitly confirmed by staff (forum thread Feb 2026) as workaround-only — no hooks, no CLI, no slash commands; only `GEMINI.md` (priority 1) + `AGENTS.md` (v1.20.3+).

**Rationale**: OpenCode + Cursor warrant full-surface investment (hook adapter + tree + audit probe); Antigravity is forced to mirror-only by upstream until Google ships hooks.

### D-133-07 — Cursor `.cursor/rules/` granular (1 `.mdc` per skill)
47 skills (or 46 per `applies_to_surfaces`) regenerated as individual `.mdc` files from `.claude/skills/<name>/SKILL.md` by `sync_mirrors`. Plus topic-level rules from canonical `CLAUDE.md` payload (§10 principles, hot-path discipline, hooks summary).

**Rationale**: Cursor's per-rule selective application (`@`-mention) only works when rules are granular. Single-file `.mdc` loses this UX.

### D-133-08 — Cursor MCP `.cursor/mcp.json` DEFERRED
Operator-locked Q8=NO. Installer does NOT create `.cursor/mcp.json`. Users wire their own MCPs when needed.

**Rationale**: no opinionated MCP set; Engram removed by spec-132; Context7 is opt-in; no clear default to pre-install.

### D-133-09 — `/ai-explore` skill thin-wrapper
Operator-locked Q9=SÍ. Create `.claude/skills/ai-explore/SKILL.md` whose only procedure is dispatching the existing `.claude/agents/ai-explore.md` agent. Sync mirrors propagate to non-Claude Surfaces.

**Rationale**: users discover commands via `/ai-` autocomplete; agent-only surface fails discoverability. UX consistency justifies the thin wrapper despite the duplication concern (Principal Architect's SKIP recommendation rejected by operator).

### D-133-10 — DELETE `ai-debug/handlers/` + `ai-review/handlers/`; consolidate to overrides
Operator-decided. `.claude/skills/ai-debug/handlers/` (8 stack-routed files: cpp/go/java/kotlin/python-build/pytorch/rust/typescript-build) and `.claude/skills/ai-review/handlers/` (10 stack-routed files: lang-cpp/lang-flutter/lang-go/lang-java/lang-kotlin/lang-python/lang-rust/lang-typescript + lang-generic + review.md) are DELETED. Stack-specific debug + review guidance migrates to `.ai-engineering/overrides/<stack>/debug.md` and `.ai-engineering/overrides/<stack>/review.md`. SKILL.md procedures become stack-agnostic and reference `overrides/<stack>/` dynamically. Greenfield mode (stacks=[]) → generic procedure + hint "add a project file and run `ai-eng doctor --fix`".

**Rationale**: §10.4 DRY — `.ai-engineering/overrides/` is the **single canonical home** for stack-specific content. Skill `handlers/` are action-routed (e.g. `deliver.md`, `quality.md`), never stack-routed. spec-128 D-128-01 contract enforced.

### D-133-11 — AI eval matrix = 6 stacks
Operator-locked Q11=C. `evals/cli-ux-cross-ide/test_drift_recovery_flow.md` simulates drift-recovery flow for python, typescript, rust, csharp, go, **java**. Other 7 stacks (kotlin, swift, ruby, dart, php, flutter, react-native — plus elixir marker-only) pass via deterministic CLI test only (`tests/integration/cli/test_stack_drift_middleware.py`).

**Rationale**: 6-stack matrix covers diverse toolchain shapes (pip/npm/cargo/dotnet/go/maven|gradle) including JVM tier-1 (java) — relevant to enterprise/regulated target audience.

### D-133-12 — Stack expansion: 12 stacks + `_shared/sql.md`
**T1 (8):** python, typescript, go, rust, java (NEW), csharp, kotlin, swift. **T2 (4):** php (NEW), ruby (NEW override dir; marker already in autodetect), flutter (NEW), react-native (NEW). **Cross-cutting:** `_shared/sql.md` (NOT a standalone stack; SQL coexists with host stack). Each stack carries `conventions.md`, `security_floor.md`, `tdd_harness.md` (+ `examples/` where deltas exist + `debug.md` + `review.md` from D-133-10 consolidation).

**Rationale**: research-anchored in `.ai-engineering/research/stack-classification-2026-05-12.md`. Flutter docs ship combined Flutter+Dart (operator-confirmed); Aider repo has `flutter/`+`nextjs-ts` framework-as-stack pattern; Cursor community embeds SQL inside DB-specific rules, never standalone. dart-standalone + javascript-standalone + elixir excluded per YAGNI.

### D-133-13 — M-cleanup: DELETE 4 orphan directories
Hard deletes (per CONSTITUTION + hard-rule §13.3, no shims):

1. `.ai-engineering/adapters/` — orphan post spec-128 D-128-01 rename; content differs from `overrides/` (drift confirmed via `diff -q`).
2. `.ai-engineering/contexts/frameworks/` — 15 files (android/react/django/etc.); spec-128 D-128-01 declared deleted but never executed.
3. `.ai-engineering/contexts/languages/` — 14 files (python/typescript/etc.); same spec-128 incomplete.
4. `.claude/skills/ai-debug/handlers/` + `.claude/skills/ai-review/handlers/` — D-133-10.

Mirror-sync regenerates Surface trees without these paths. `tools/skill_lint/checks/no_orphan_dirs.py` (NEW) enforces absence.

**Rationale**: spec-128 D-128-01 contract specified deletion of `contexts/{frameworks,languages}/` and rename of `adapters/` to `overrides/` — those deletions never landed. spec-133 closes the gap. CONSTITUTION §13.3 forbids backwards-compat shims; hard deletes per policy.

### D-133-14 — `plan_tasks.py` NOT orphan (corrects brief B6)
Brief claim "plan_tasks.py has 0 skill refs" is wrong. Grep confirms 2 callers: `.claude/skills/ai-autopilot/handlers/phase-implement.md` and `.claude/skills/ai-autopilot/handlers/phase-deep-plan.md` invoke `python .ai-engineering/scripts/plan_tasks.py sync` and `python .ai-engineering/scripts/plan_tasks.py validate`. Script is preserved + deploys to templates per D-133-21.

**Rationale**: brief auditor missed handler files; verified via fresh grep 2026-05-12.

### D-133-15 — Surface domain primitive
`src/ai_engineering/domain/surface.py` (NEW). `Surface` frozen dataclass with fields: `id`, `display_name`, `instruction_files`, `tree_dir`, `hook_engine`, `audit_capability`, `autodetect_marker`. `_SURFACE_REGISTRY` constant with 7 entries (claude-code, codex, gemini-cli, github-copilot, opencode, cursor, antigravity). `domain/` has zero infrastructure imports (lint-imports enforced).

**Rationale**: §10.3 SOLID (Single Responsibility); §10.8 Hexagonal (domain inward-only); single source of truth for Surface capability matrix.

### D-133-16 — Manifest schema hard-migration
`SurfacesConfig(enabled: list[str])` added. `AiProvidersConfig` deleted (incl. `primary` — YAGNI per §10.2). `ProvidersConfig.ides` field deleted. `ProvidersConfig.stacks` + `ProvidersConfig.vcs` preserved (real consumers: doctor, policy, tools). Framework's own `.ai-engineering/manifest.yml` rewritten in same commit as schema change. CHANGELOG `[Breaking changes]` documents migration steps (`ai-eng install --reconfigure` flows for consumer repos).

**Rationale**: §10.4 DRY (one truth — Surface list); §10.6 SDD (decision row; no drive-by); CONSTITUTION §13.3 no-shim.

### D-133-17 — Wizard collapses to 1 question
`wizard.py` prompts only: `"Which Surface(s) do you use?"` (multi-select from `_SURFACE_REGISTRY`, pre-selected from autodetect when markers present). Stack auto-detect silent; VCS auto-detect silent (default `github`). Old prompts for `Select technology stacks` / `Select AI providers` / `Select IDE integrations` / `Select VCS provider` DELETED.

**Rationale**: §10.1 KISS; operator feedback: separate AI-provider + IDE prompts are conceptually broken (B4 root cause).

### D-133-18 — `--surface/-S` replaces `--ide` and `--provider`
`install_cmd` adds `--surface/-S` repeatable flag accepting Surface IDs from `_SURFACE_REGISTRY` enum. `--ide/-i` and `--provider/-p` flags DELETED. Hard rename; no compat aliases. Help text updated. Golden snapshot test (`tests/unit/cli/test_help_snapshots.py`) verifies.

**Rationale**: §13.3 no shim; conceptual collapse (D-133-15 + D-133-16).

### D-133-19 — `applies_to_surfaces` frontmatter for per-Surface skill restrictions
SKILL.md gains optional `applies_to_surfaces: [list]` field. `ai-analyze-permissions` declares `applies_to_surfaces: [claude-code]` (audits Claude Code `settings.local.json`, no analogue elsewhere). `scripts/sync_mirrors/core.py` filters per-Surface based on this field. `tools/skill_lint/checks/md_mirror.py` excludes restricted skills from sha256 parity checks. Non-Claude Surfaces carry 47 skills (48 minus claude-only `ai-analyze-permissions`; new `ai-explore` skill = +1 net per D-133-09).

**Rationale**: §10.4 DRY (restriction declared at source, not buried in script); operator-confirmed per-design exclusion (B12).

### D-133-20 — Hex contract zero-whitelist
`pyproject.toml` `[tool.importlinter] ignore_imports` shrinks to empty (or contains only documented externally-enforced exceptions). 4 baseline ignores eliminated: `cli_ui → updater.service` (route via `OutputPort`); `updater.service → installer.templates` (extract `TemplateRegistryPort`); `policy.checks.stack_runner → installer.launchers` (extract `LauncherPort`); `validator._shared → installer.templates` (same `TemplateRegistryPort`). 6 in-band CLI hex violations unwound: `core.py:366-381` `_is_reinstall` sqlite3 → `AuditStorePort`; `core.py:344` raw `print` → `OutputPort`; `core.py:519-557` confirm helpers → `ConfirmPort` + extract pure helpers ≤30 lines per §10.7; `spec_cmd.py:133` `click.echo` → `OutputPort`; `spec_cmd.py:84` filesystem write → application-layer use case; `audit_cmd.py:38` module-level sqlite3 → `adapters/storage/`.

**Rationale**: §10.8 Hexagonal — adapter↔core boundary physically enforceable; tests/architecture/test_hexagonal.py with empty whitelist.

### D-133-21 — Templates deploy 9 root framework scripts
New installer phase `ScriptsPhase` deploys full `.ai-engineering/scripts/` tree (root + `skills/` subdir) into consumer's tree. 9 root scripts: `session_bootstrap.py`, `spec_lifecycle.py`, `commit_compose.py`, `branch_slug.py`, `doc_gate.py`, `pr_body_compose.py`, `runtime_rotate.py`, `regenerate-hooks-manifest.py`, `plan_tasks.py`. Test: `tests/unit/installer/test_phases_scripts_deploy.py` asserts deployment per Surface. Pristine-install smoke per Surface (`tests/integration/installer/test_pristine_install_smoke.py`) verifies `/ai-start` exits 0 immediately.

**Rationale**: every skill referencing `python .ai-engineering/scripts/<x>.py` must succeed on first call (B1 highest-ROI fix).

### D-133-22 — `cli_ui.skill_ref()` helper + lint
`src/ai_engineering/cli_ui/skill_ref.py` (NEW). Returns canonical render of in-chat slash command reference: `"the /ai-NAME skill (run in your AI surface chat, not shell)"` (or tight variant `"/ai-NAME (in your AI surface)"`). Replaces every naked `/ai-<name>` in `cli_commands/`, `cli_ui/`, `phases/`, error formatters, post-install hints. `tools/skill_lint/checks/cli_output_skill_refs.py` AST-walks the CLI tree, fails on naked literals in `print` / `typer.echo` / `OutputPort.emit` calls.

**Rationale**: prior incident (operator pasted `/ai-start` into shell) — B17 design + lint layer fix.

### D-133-23 — B16 Gap 4 CLI middleware
`cli_factory.py` adds middleware running on every `ai-eng <cmd>` (except `install`, `doctor`, `version`). Reads `manifest.providers.stacks`, runs `autodetect.detect_stacks(...)`, compares. On drift, emits structured warning via `OutputPort` listing detected markers + missing toolchains. Honors `AIENG_STACK_DRIFT_STRICT=1` env (or `--strict` flag on `commit`/`pr`/`gate`) to block command (exit 78). Default: warn-only. Test `tests/integration/cli/test_stack_drift_middleware.py` covers all 13 marker types (python/typescript/javascript/go/rust/java/kotlin/swift/csharp/ruby/dart/elixir/php).

**Rationale**: closes silent toolchain-absence gap (B16 root risk).

### D-133-24 — B16 Gap 5 AI cognitive contract
Exit code 78 (`stack-drift-block`) with fixed format: Reason / Detected stack(s) / Missing toolchain(s) / Recovery (shell) / Then retry (in AI surface). `.claude/skills/ai-commit/SKILL.md` and `.claude/skills/ai-pr/SKILL.md` gain a verbatim "Stack drift recovery" subsection. Sync mirrors propagate. Eval `evals/cli-ux-cross-ide/test_drift_recovery_flow.md` simulates the loop for 6 stacks (D-133-11), asserts AI runs `ai-eng doctor --fix`, retries commit, hook output contains stack-specific tools (pytest+pip-audit / vitest+npm-audit / cargo-test+cargo-audit / dotnet-test+dotnet-list-vulnerable / go-test+govulncheck / mvn-test+mvn-dependency-check).

**Rationale**: structured machine-readable contract per "deterministic-first" principle — AI consumes structured exit envelope, no free-form heuristics.

### D-133-25 — B16 Gap 1+2 greenfield mode
`doctor/phases/tools.py:112-113`: drop `or ["python"]` coercion. Doctor operates in greenfield mode when `stacks=[]` (skip stack-specific tool probes; report baseline only — gitleaks, semgrep, jq). `ai-eng doctor --fix` opt-in flag: when `stack-drift` finding triggers, automatically updates `manifest.providers.stacks` with autodetect result, re-invokes `phases.sdk_prereqs` + `phases.tools` for newly-detected stacks. Idempotent. Test `tests/integration/doctor/test_doctor_fix_stack_drift.py`.

**Rationale**: deterministic-first (CI-stable) per operator Q3 default; opt-in keeps doctor side-effect-free.

### D-133-26 — Quality bar: production-grade for every new deterministic primitive
Every new CLI verb / script ships with: idempotency (re-run = no-op when no drift), exit-coded per category (0/1/2/78), audit events via `OutputPort` per state-change, `--json` structured output universal, `--dry-run` where state-changing, refuse detached HEAD, never delete current branch, TDD per mode (RED-first). Acceptance gates ≤ 95 on `/ai-verify --full`. Hot-path budgets enforced.

**Rationale**: operator quality bar "bootstrap-mínimo level" — these become the framework's deterministic spine.

## Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R-133-01 | Manifest schema break orphans consumer `.ai-engineering/manifest.yml` files | Medium | High | CHANGELOG `[Breaking changes]` documents; `ai-eng install --reconfigure` re-runs wizard against new schema. No shim per §13.3. PR #509 is the only delivery vehicle until release. |
| R-133-02 | Hard renames break downstream tooling (decision-store IDs, Engram lookups already removed by spec-132) | Medium | Medium | Decision-store rows updated in same commit as rename. CHANGELOG breaking section enumerates all. Sync mirrors regenerate idempotently as part of acceptance. |
| R-133-03 | OpenCode hook adapter (TS plugin shim) is a new language surface for the framework | Medium | Medium | Scope contained to `.ai-engineering/scripts/hooks/opencode-hook-bridge.ts` + `package.json` install step. Plugin contract isomorphic to Claude Code stdio JSON (event-name translation table); adapter is thin. Per-event smoke test in `tests/integration/hooks/test_opencode_bridge.py`. |
| R-133-04 | Cursor hooks are beta (Cursor 1.7+, Sept 2025) — event shape may evolve | Medium | Low | Pin event-name translation table in `cursor-hook-bridge.py`; doc states beta status; community-monitored. If Cursor breaks contract, single adapter file changes. |
| R-133-05 | Antigravity stays mirror-only — operator may expect "full support" | High | Low | D-133-06 documents upstream limitation (Google staff explicit). CHANGELOG + `docs/integrations/antigravity.md` carry the rationale + monitoring link. |
| R-133-06 | Hex extraction inadvertently breaks installer hot-path (4 whitelisted edges may be load-bearing) | Medium | Medium | M6 is the **last** milestone — 5 prior have green tests; hex extraction only refactors layout, not behavior. Per-milestone `pytest` gate. Hot-path budgets enforced. |
| R-133-07 | Stack-drift CLI middleware adds latency to every `ai-eng <cmd>` | Medium | Low | Detection is cheap (`os.walk` with `_WALK_EXCLUDE`, sub-second on typical repos). Benchmarked in `tests/perf/test_stack_drift_middleware_budget.py` (< 100ms p95). Hot-path budgets preserved. |
| R-133-08 | Stack content migration (ai-debug/handlers + ai-review/handlers → overrides/<stack>/) may lose nuance | Medium | Medium | Per spec-128 D-128-03 (hard delete + start fresh, no migration), the existing handler content is NOT carried over verbatim. Operator-confirmed: training-redundant content survives in LLM priors. New `overrides/<stack>/{debug,review}.md` files written only when concrete project-specific deltas identified. YAGNI for empty files. |
| R-133-09 | New `ai-eng cleanup --squashed` mode misidentifies branches in repos with non-standard merge workflows | Low | Medium | git-trim algorithm (merge-base + commit-tree) is industry-validated. `--dry-run` default for first run + explicit confirmation per session. Test `tests/integration/cli/test_cleanup_squashed_edge_cases.py` covers fast-forward + rebase-merge + cherry-pick scenarios. |
| R-133-10 | 12-stack inventory expands maintenance burden | Medium | Low | Each stack ships minimum content (`conventions.md`, `security_floor.md`, `tdd_harness.md`) — initially stubs to be filled per concrete deltas. YAGNI prevents over-writing. ~30 files added (12 stacks × ~3 files); maintainable. |

## References

- pr: arcasilesgroup/ai-engineering#509
- doc: .ai-engineering/specs/drafts/cli-ux-cross-ide-rearch-brief.md
- doc: .ai-engineering/specs/archive/spec-128-context-overrides.md
- doc: .ai-engineering/specs/spec-129-skills-agents-excellence-pragmatic.md
- doc: .ai-engineering/specs/spec-132-cli-ux-overhaul.md
- doc: CLAUDE.md (§10 first-class principles; §14 Strict Content Contracts)
- doc: CONSTITUTION.md (§13.3 hard-rule no-shim)
- research: .ai-engineering/research/ide-hook-engines-2026-05-12.md
- research: .ai-engineering/research/stack-classification-2026-05-12.md
- research: .ai-engineering/research/git-branch-cleanup-modes-2026-05-12.md

## Open Questions

None. All 11 brief questions resolved during interrogation; 3 additional discoveries (ai-review stack-routed handlers, mirror-sync targets missing, hook bridges missing) folded into Decisions D-133-10, D-133-13, D-133-15.
