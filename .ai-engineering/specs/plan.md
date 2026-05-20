---
spec: spec-146
title: Framework Simplification — Less is More
status: approved
pipeline: autopilot
phases: 6
total: 38
completed: 38
execution_route:
  version: 1
  spec: spec-146
  executor: autopilot
  automation: hitl
  concern_count: 6
  estimated_files: 45
  reason: "Plan status 'approved'; 6 independent concerns meets the /ai-autopilot threshold of 3."
  safe_next_command: "/ai-autopilot"
---

# Plan — spec-146 Framework Simplification — Less is More

## Design Routing

design-routing: skipped (no UI/frontend semantics; substring hits were false positives from `autoformat` and generic prose: `form`, `ui`). No design-intent artifact is required.

## Architecture

**Pattern:** Hexagonal Architecture / Ports and Adapters.

**Why:** The spec separates domain policy decisions from adapters: ownership matching remains the domain contract, `state_db` is the SQLite lifecycle adapter, updater/service is a CLI/file-system adapter, hook sidecars are runtime adapters, and JSON/Markdown persistence surfaces retain explicit ownership. This pattern lets the plan fix the concrete ownership bug first without spreading SQLite reads into hot-path hooks or turning every cleanup into a new abstraction.

**Pipeline classification:** autopilot route. The work spans six independent concerns and at least forty-five files across Python source, tests, hook scripts, templates, generated mirrors, `.ai-engineering/` state/reference files, and CHANGELOG. The approved plan was executed through `/ai-autopilot` on the existing branch and PR.

## Gate Strategy

- Section preflight passed for `.ai-engineering/specs/spec.md` after approval.
- Plan status is `approved`; `/ai-autopilot` executed the approved task DAG and all 38 tasks are complete.
- RED/GREEN pairs precede each implementation wave per §10.5 TDD.
- Hook and state changes must run the targeted unit/integration tests before broader verification.
- Mirror or template edits must be followed by `ai-eng dev sync` and `ai-eng dev sync --check` when the edited surface participates in generated mirrors.
- Historical audit files and archived specs remain read-only except for new append-only `framework_operation` telemetry emitted by tools.

## Phase 1: Ownership Read Path and Update Bug Fix

- [x] T-1.1 — RED: add state-db ownership reader contract tests
  - Agent: build
  - Files: tests/unit/state/test_ownership_state_db_read.py:new; src/ai_engineering/state/state_db.py:257
  - Principles applied: §10.5 TDD, §10.8 Hexagonal Architecture
  - Patch (deterministic): create tests that upsert raw and model ownership rows, then assert `list_ownership_rows(project_root)` returns ordered dict rows with `path_pattern`, decoded owners/reviewers, `severity`, and timestamps without requiring `ownership-map.json`.
  - Gate: `rtk .venv/bin/pytest tests/unit/state/test_ownership_state_db_read.py -q` fails before readers exist.

- [x] T-1.2 — GREEN: implement raw ownership row reader
  - Agent: build
  - Files: src/ai_engineering/state/state_db.py:638; src/ai_engineering/state/state_db.py:709
  - Principles applied: §10.1 KISS, §10.8 Hexagonal Architecture
  - Patch (deterministic): add `list_ownership_rows(project_root: Path) -> list[dict[str, object]]`, decode `owners_json` and `reviewers_json`, return `[]` on missing table, and export it in `__all__`.
  - Gate: `rtk .venv/bin/pytest tests/unit/state/test_ownership_state_db_read.py -q` reaches mapper-specific failures only.

- [x] T-1.3 — RED: add OwnershipMap reconstruction tests
  - Agent: build
  - Files: tests/unit/state/test_ownership_state_db_read.py:1; tools/skill_domain/state_models.py:115
  - Principles applied: §10.5 TDD, §10.3 SOLID
  - Patch (deterministic): extend the reader tests to assert `load_ownership_map(project_root)` reconstructs `OwnershipMap.paths` with `OwnershipLevel` and `FrameworkUpdatePolicy` values for allow, deny, team-managed, and append-only rows; assert first-match order is stable.
  - Gate: `rtk .venv/bin/pytest tests/unit/state/test_ownership_state_db_read.py -q` fails until the high-level mapper exists.

- [x] T-1.4 — GREEN: implement updater-ready ownership mapper
  - Agent: build
  - Files: src/ai_engineering/state/state_db.py:638; src/ai_engineering/state/defaults.py:70
  - Principles applied: §10.1 KISS, §10.8 Hexagonal Architecture
  - Patch (deterministic): add `load_ownership_map(project_root: Path) -> OwnershipMap` or equivalent mapper next to the raw reader, mapping the first owner to `OwnershipEntry.owner`, mapping `severity` to `frameworkUpdate`, preserving table order, and returning an empty `OwnershipMap()` when no rows exist.
  - Gate: `rtk .venv/bin/pytest tests/unit/state/test_ownership_state_db_read.py -q` passes.

- [x] T-1.5 — RED: prove updater ignores absent JSON and honors SQLite deny rules
  - Agent: build
  - Files: tests/unit/test_updater.py:147; src/ai_engineering/updater/service.py:395
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): add a test project with `.ai-engineering/state/state.db` ownership rows, no `ownership-map.json`, and a deny/team rule for a missing template path; assert `_initialize_update_context(..., dry_run=True)` loads the rule and `_evaluate_file_change(...)` returns `skip-denied` for the missing path.
  - Gate: `rtk .venv/bin/pytest tests/unit/test_updater.py::TestInitializeUpdateContext -q` fails before updater reads SQLite.

- [x] T-1.6 — GREEN: load SQLite ownership before updater evaluation
  - Agent: build
  - Files: src/ai_engineering/updater/service.py:395; src/ai_engineering/state/state_db.py:638
  - Principles applied: §10.1 KISS, §10.8 Hexagonal Architecture
  - Patch (deterministic): replace the normal `ownership-map.json` read in `_initialize_update_context` with the new SQLite mapper; keep a one-time JSON fallback only when SQLite returns zero rows and the sidecar exists, then upsert those fallback rows and remove the sidecar on non-dry-run.
  - Gate: `rtk .venv/bin/pytest tests/unit/test_updater.py::TestInitializeUpdateContext tests/unit/state/test_ownership_state_db_read.py -q` passes.

- [x] T-1.7 — RED/GREEN: add operator integration scenario for denied missing file
  - Agent: build
  - Files: tests/integration/test_updater.py:1; src/ai_engineering/updater/service.py:848
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): add an integration test that installs/minimally bootstraps a project, writes a deny/team ownership row for a template-managed path, ensures the destination file is absent, runs `update(..., dry_run=True)`, and asserts the result reports `skip-denied` and the file remains absent.
  - Gate: `rtk .venv/bin/pytest tests/integration/test_updater.py tests/unit/test_updater.py tests/unit/state/test_ownership_state_db_read.py -q` passes.

## Phase 2: Persistence Doctrine and Gate-Findings Canonicality

- [x] T-2.1 — RED: add persistence classification tests
  - Agent: build
  - Files: tests/unit/specs/test_persistence_doctrine_contract.py:new; docs/persistence-doctrine.md:50; src/ai_engineering/state/state_db.py:1
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): create tests asserting `state_db.py` no longer calls the entire DB a replayable derived projection, `docs/persistence-doctrine.md` classifies lifecycle tables table-by-table, and `gate-findings.json` remains the named JSON artifact for gate/risk/verify in this spec.
  - Gate: `rtk .venv/bin/pytest tests/unit/specs/test_persistence_doctrine_contract.py -q` fails on current docstring/doctrine drift.

- [x] T-2.2 — GREEN: correct `state_db.py` module contract
  - Agent: build
  - Files: src/ai_engineering/state/state_db.py:1
  - Principles applied: §10.7 Clean Code, §10.8 Hexagonal Architecture
  - Patch (deterministic): rewrite the module docstring so `state.db` is described as a mixed lifecycle database with named derived projections; keep `state.db.events` as NDJSON-derived and `gate_findings` as non-primary placeholder/transitional state.
  - Gate: `rtk .venv/bin/pytest tests/unit/specs/test_persistence_doctrine_contract.py -q` advances to docs failures only.

- [x] T-2.3 — GREEN: reconcile persistence doctrine table entries
  - Agent: build
  - Files: docs/persistence-doctrine.md:50; docs/persistence-doctrine.md:132; tests/unit/specs/test_state_canonical.py:1
  - Principles applied: §10.4 DRY, §10.6 SDD
  - Patch (deterministic): update Tier 2 and Derived Caches sections to distinguish canonical lifecycle tables, derived caches, and transitional placeholders; ensure `state.db.ownership_map` is not described as rebuildable only from a deleted sidecar and gate findings are documented as JSON-primary for this spec.
  - Gate: `rtk .venv/bin/pytest tests/unit/specs/test_persistence_doctrine_contract.py tests/unit/specs/test_state_canonical.py -q` passes.

- [x] T-2.4 — RED/GREEN: pin gate-findings JSON consumers
  - Agent: build
  - Files: tests/unit/test_gate_findings_schema.py:1; tests/integration/test_gate_findings_persisted.py:1; src/ai_engineering/verify/service.py:45; src/ai_engineering/cli_commands/risk_cmd.py:351
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): add or extend tests that fail if `verify`, `risk`, `gate`, or orchestrator paths switch to `state.db.gate_findings` without an explicit later migration spec.
  - Gate: `rtk .venv/bin/pytest tests/unit/test_gate_findings_schema.py tests/integration/test_gate_findings_persisted.py tests/integration/test_risk_accept_all_e2e.py -q` passes.

- [x] T-2.5 — VERIFY: persistence hot-path guard remains green
  - Agent: verify
  - Files: tests/architecture/test_no_sql_on_hot_path.py:1; src/ai_engineering/state/state_db.py:1
  - Principles applied: §10.5 TDD, §10.8 Hexagonal Architecture
  - Patch (deterministic): read-only verification; do not edit production files in this task.
  - Gate: `rtk .venv/bin/pytest tests/architecture/test_no_sql_on_hot_path.py tests/unit/specs/test_persistence_doctrine_contract.py -q` passes.

## Phase 3: `.ai-engineering/` Data-Tree Cleanup

- [x] T-3.1 — RED: add IOC attribution single-home contract
  - Agent: build
  - Files: tests/integration/test_sentinel_runtime_iocs.py:36; tests/unit/skills/test_ioc_attribution_references.py:new; .claude/skills/ai-mcp-audit/SKILL.md:118
  - Principles applied: §10.4 DRY, §10.5 TDD
  - Patch (deterministic): add a test asserting active skills and templates reference `.ai-engineering/security/iocs/IOCS_ATTRIBUTION.md`, not `.ai-engineering/references/IOCS_ATTRIBUTION.md`, and that the duplicate references copy is absent after migration.
  - Gate: `rtk .venv/bin/pytest tests/integration/test_sentinel_runtime_iocs.py tests/unit/skills/test_ioc_attribution_references.py -q` fails before references are updated.

- [x] T-3.2 — GREEN: move IOC attribution references to the security/iocs home
  - Agent: build
  - Files: .claude/skills/ai-mcp-audit/SKILL.md:118; .codex/skills/ai-mcp-audit/SKILL.md:123; .gemini/skills/ai-mcp-audit/SKILL.md:123; .github/skills/ai-mcp-audit/SKILL.md:124; src/ai_engineering/templates/.ai-engineering/references/IOCS_ATTRIBUTION.md:1; .ai-engineering/references/IOCS_ATTRIBUTION.md:1
  - Principles applied: §10.4 DRY, §10.7 Clean Code
  - Patch (deterministic): update canonical skill source to the security path, run mirror sync, remove the byte-identical `.ai-engineering/references/IOCS_ATTRIBUTION.md` and template duplicate, and add the security/iocs attribution file to any installer template path that still needs it.
  - Gate: `rtk .venv/bin/pytest tests/integration/test_sentinel_runtime_iocs.py tests/unit/skills/test_ioc_attribution_references.py -q` passes and `cmp` no longer has duplicate inputs.

- [x] T-3.3 — RED: add strategic compact runtime-path test
  - Agent: build
  - Files: tests/integration/test_strategic_compact_integration.py:1; .ai-engineering/scripts/hooks/strategic-compact.py:64; tests/unit/specs/test_state_canonical.py:70
  - Principles applied: §10.5 TDD, §10.8 Hexagonal Architecture
  - Patch (deterministic): add a test proving `strategic-compact.py` writes `.ai-engineering/runtime/strategic-compact.json` and no longer writes `.ai-engineering/state/strategic-compact.json`.
  - Gate: `rtk .venv/bin/pytest tests/integration/test_strategic_compact_integration.py tests/unit/specs/test_state_canonical.py -q` fails before the hook path moves.

- [x] T-3.4 — GREEN: move strategic compact sidecar out of state
  - Agent: build
  - Files: .ai-engineering/scripts/hooks/strategic-compact.py:64; .ai-engineering/state/hooks-manifest.json:77; tests/unit/specs/test_state_canonical.py:70
  - Principles applied: §10.1 KISS, §10.8 Hexagonal Architecture
  - Patch (deterministic): change the hook sidecar path to `.ai-engineering/runtime/strategic-compact.json`, remove `strategic-compact.json` from documented state transients, delete the old state file, and regenerate hook manifest hashes.
  - Gate: `rtk .venv/bin/pytest tests/integration/test_strategic_compact_integration.py tests/unit/specs/test_state_canonical.py -q` passes.

- [x] T-3.5 — RED/GREEN: remove dead `instinct-observations.ndjson` state artifact
  - Agent: build
  - Files: tests/unit/specs/test_state_canonical.py:67; src/ai_engineering/state/instincts.py:25; .ai-engineering/state/instinct-observations.ndjson:1
  - Principles applied: §10.2 YAGNI, §10.7 Clean Code
  - Patch (deterministic): add a state-canonical assertion that `instinct-observations.ndjson` is forbidden, confirm active code writes `observation-events.ndjson`, then delete the zero-byte legacy file and remove the documented-transient exception.
  - Gate: `rtk .venv/bin/pytest tests/unit/specs/test_state_canonical.py tests/integration/test_framework_hook_emitters.py -q` passes.

- [x] T-3.6 — RED/GREEN: merge team lessons into canonical LESSONS.md
  - Agent: build
  - Files: .ai-engineering/team/lessons.md:1; .ai-engineering/LESSONS.md:1; tests/unit/specs/test_lessons_single_home.py:new; src/ai_engineering/installer/phases/governance.py:36
  - Principles applied: §10.4 DRY, §10.6 SDD
  - Patch (deterministic): add a preservation test for the two unique headings in `.ai-engineering/team/lessons.md`, append missing content to `.ai-engineering/LESSONS.md` without duplicating existing lessons, remove the team copy, and update installer/governance mappings if they still create the duplicate file.
  - Gate: `rtk .venv/bin/pytest tests/unit/specs/test_lessons_single_home.py tests/e2e/test_install_clean.py -q` passes.

- [x] T-3.7 — GREEN: document gate cache as bounded cache, not deletion target
  - Agent: build
  - Files: docs/persistence-doctrine.md:125; src/ai_engineering/cli_commands/gate.py:799; tests/perf/test_ai_pr_coldcache.py:109
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Patch (deterministic): update docs to cite the existing cache status/clear commands and the 24h/256-entry implementation rather than inventing a new lifecycle or removing `.ai-engineering/cache/gate/`.
  - Gate: `rtk .venv/bin/pytest tests/unit/specs/test_persistence_doctrine_contract.py tests/unit/specs/test_state_canonical.py -q` passes.

- [x] T-3.8 — VERIFY: state/data-tree cleanup sweep
  - Agent: verify
  - Files: .ai-engineering/state/:1; .ai-engineering/runtime/:1; .ai-engineering/security/iocs/:1
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): read-only verification; use `rg`/`find` to confirm no active references to removed paths except archived specs/history.
  - Gate: `rtk .venv/bin/pytest tests/unit/specs/test_state_canonical.py tests/integration/test_sentinel_runtime_iocs.py tests/integration/test_strategic_compact_integration.py -q` passes.

## Phase 4: Tunables Documentation and Mirror Reconciliation

- [x] T-4.1 — RED: extend tunables test to promoted M5/M6 variables
  - Agent: build
  - Files: tests/architecture/test_tunables_docs_match_code.py:95; .ai-engineering/scripts/hooks/prompt-injection-guard.py:81; .ai-engineering/scripts/hooks/auto-format.py:50; .ai-engineering/scripts/hooks/runtime-session-end.py:69
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): add code-default resolution for `AIENG_HOOK_CACHE_TTL_SEC=300`, `AIENG_AUTOFORMAT_DEBOUNCE_SEC=1.0`, `AIENG_NDJSON_MAX_LINES=100000`, and `AIENG_NDJSON_MAX_BYTES=52428800`; assert they are documented with defaults, not pending markers.
  - Gate: `rtk .venv/bin/pytest tests/architecture/test_tunables_docs_match_code.py -q` fails on current pending rows.

- [x] T-4.2 — GREEN: update root and template tunables docs
  - Agent: build
  - Files: CLAUDE.md:175; src/ai_engineering/templates/project/CLAUDE.md:175; tests/architecture/test_tunables_docs_match_code.py:58
  - Principles applied: §10.4 DRY, §10.7 Clean Code
  - Patch (deterministic): move implemented M5/M6 variables from the pending block into default-bearing sections, leave or remove only true reserved variables (`AIENG_HOST_PREFLIGHT_*`, `AIENG_HOOK_BUDGET_PROFILE`) per D-146-07, and update `_PENDING_MILESTONES` so only genuinely pending buckets remain.
  - Gate: `rtk .venv/bin/pytest tests/architecture/test_tunables_docs_match_code.py -q` passes.

- [x] T-4.3 — GREEN: regenerate rulebook mirrors after CLAUDE/template edit
  - Agent: build
  - Files: AGENTS.md:175; GEMINI.md:175; .github/copilot-instructions.md:175; src/ai_engineering/templates/project/AGENTS.md:175; src/ai_engineering/templates/project/GEMINI.md:175; src/ai_engineering/templates/project/copilot-instructions.md:175
  - Principles applied: §10.4 DRY, §10.6 SDD
  - Patch (deterministic): run the project mirror-sync command so generated root and template rulebooks carry the same tunables block; do not hand-edit generated mirrors.
  - Gate: `rtk .venv/bin/ai-eng dev sync --check` passes.

- [x] T-4.4 — VERIFY: docs/code tunables reconciliation
  - Agent: verify
  - Files: tests/architecture/test_tunables_docs_match_code.py:1; CLAUDE.md:175; src/ai_engineering/templates/project/CLAUDE.md:175
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): read-only verification.
  - Gate: `rtk .venv/bin/pytest tests/architecture/test_tunables_docs_match_code.py -q && rtk .venv/bin/ai-eng dev sync --check` passes.

## Phase 5: Caller Inventory and Module Simplification

- [x] T-5.1 — RED: add caller-inventory artifact contract
  - Agent: build
  - Files: tests/unit/specs/test_spec_146_caller_inventory.py:new; .ai-engineering/specs/spec-146-caller-inventory.md:new
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): add a test requiring a spec-146 inventory artifact with rows for `agentsview.py`, `outbox.py`, `governance/policy_engine.py`, `cli_ui_skill_ref.py`, `trace_context.py`, `capabilities.py`, `context_packs.py`, `relevance.py`, `StateService`, `DurableStateRepository`, and `installer/mechanisms/__init__.py`.
  - Gate: `rtk .venv/bin/pytest tests/unit/specs/test_spec_146_caller_inventory.py -q` fails before the artifact exists.

- [x] T-5.2 — GREEN: generate and commit caller inventory
  - Agent: build
  - Files: .ai-engineering/specs/spec-146-caller-inventory.md:new; tools/caller_inventory.py:new
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Patch (deterministic): create a small script or documented command output that classifies each candidate as production, test, hook, template, doc, archive, or unused; write the resulting Markdown artifact with exact command and timestamp-free evidence.
  - Gate: `rtk .venv/bin/pytest tests/unit/specs/test_spec_146_caller_inventory.py -q` passes.

- [x] T-5.3 — RED: pin production-used module preservation
  - Agent: build
  - Files: tests/unit/specs/test_spec_146_module_boundaries.py:new; src/ai_engineering/state/observability.py:357; src/ai_engineering/validator/categories/manifest_coherence.py:13
  - Principles applied: §10.5 TDD, §10.3 SOLID
  - Patch (deterministic): add tests asserting `trace_context.py`, `capabilities.py`, and `context_packs.py` are either present or explicitly represented by replacement modules named in the caller inventory.
  - Gate: `rtk .venv/bin/pytest tests/unit/specs/test_spec_146_module_boundaries.py -q` passes before deletion tasks begin.

- [x] T-5.4 — RED: add dead-module import guards
  - Agent: build
  - Files: tests/architecture/test_no_dead_module_imports.py:new; src/ai_engineering/state/agentsview.py:1; src/ai_engineering/state/outbox.py:1; src/ai_engineering/cli_ui_skill_ref.py:1
  - Principles applied: §10.5 TDD, §10.2 YAGNI
  - Patch (deterministic): add an architecture test that fails when production code imports candidates classified as unused/test-only and asserts replacements are documented for any public import removed.
  - Gate: `rtk .venv/bin/pytest tests/architecture/test_no_dead_module_imports.py -q` fails until deletion/update is complete.

- [x] T-5.5 — GREEN: hard-delete low-risk dead/test-only modules
  - Agent: build
  - Files: src/ai_engineering/state/agentsview.py:1; src/ai_engineering/state/outbox.py:1; src/ai_engineering/cli_ui_skill_ref.py:1; tests/unit/test_agentsview_contract.py:1; tests/integration/state/test_outbox_atomic.py:1
  - Principles applied: §10.2 YAGNI, §10.7 Clean Code
  - Patch (deterministic): delete only candidates classified as no-production-callers; update or remove tests that exist solely to preserve deleted modules; do not touch production-used modules in this task.
  - Gate: `rtk .venv/bin/pytest tests/architecture/test_no_dead_module_imports.py tests/unit/specs/test_spec_146_module_boundaries.py -q` passes.

- [x] T-5.6 — RED/GREEN: remove or replace governance policy-engine shim
  - Agent: build
  - Files: src/ai_engineering/governance/policy_engine.py:1; src/ai_engineering/governance/__init__.py:1; src/ai_engineering/governance/opa_runner.py:1; src/ai_engineering/installer/tool_registry.py:207
  - Principles applied: §10.2 YAGNI, §10.4 DRY
  - Patch (deterministic): if the inventory confirms zero production callers beyond re-export/documentation, delete `policy_engine.py`, update `governance/__init__.py` to expose the real OPA path or nothing, and update references that called it downstream-fork insurance.
  - Gate: `rtk .venv/bin/pytest tests/architecture/test_no_dead_module_imports.py tests/unit/test_aieng_test_simulate_fail.py -q` passes.

- [x] T-5.7 — RED/GREEN: split installer mechanisms by mechanism class
  - Agent: build
  - Files: src/ai_engineering/installer/mechanisms/__init__.py:1; src/ai_engineering/installer/tool_registry.py:26; tests/integration/test_install_idempotence.py:41
  - Principles applied: §10.3 SOLID, §10.7 Clean Code
  - Patch (deterministic): add import-contract tests, move mechanism classes into focused modules, keep `mechanisms/__init__.py` as a thin re-export surface during internal migration, and ensure RUF022-sorted `__all__` remains stable.
  - Gate: `rtk .venv/bin/pytest tests/integration/test_install_idempotence.py tests/integration/test_doctor_fix_node_stack.py tests/unit/test_aieng_test_simulate_fail.py -q` passes.

- [x] T-5.8 — RED/GREEN: migrate one facade callsite group away from behavior-free forwarding
  - Agent: build
  - Files: src/ai_engineering/state/service.py:29; src/ai_engineering/state/repository.py:66; src/ai_engineering/cli_commands/gate.py:47; src/ai_engineering/cli_commands/risk_cmd.py:52
  - Principles applied: §10.1 KISS, §10.3 SOLID
  - Patch (deterministic): select the smallest callsite group identified by the inventory where direct `state_db` helpers remove a pass-through layer; add tests first, migrate those callsites, and leave facades in place for remaining production users.
  - Gate: `rtk .venv/bin/pytest tests/integration/test_orchestrator_lookup.py tests/integration/test_risk_accept_all_e2e.py tests/unit/specs/test_spec_146_module_boundaries.py -q` passes.

- [x] T-5.9 — VERIFY: import graph and module simplification sweep
  - Agent: verify
  - Files: src/ai_engineering/:1; tests/:1; tools/:1
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): read-only verification using `pytest` plus `rg` to ensure deleted module names appear only in CHANGELOG/spec artifacts or allowed archives.
  - Gate: `rtk .venv/bin/pytest tests/architecture/test_no_dead_module_imports.py tests/unit/specs/test_spec_146_caller_inventory.py tests/unit/specs/test_spec_146_module_boundaries.py -q` passes.

## Phase 6: Changelog, Sync, and Final Quality Gates

- [x] T-6.1 — RED: add changelog removal coverage test
  - Agent: build
  - Files: tests/docs/test_changelog_spec_146.py:new; CHANGELOG.md:1
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): add a test requiring `[Unreleased]` entries for spec-146 ownership fix, persistence clarification, removed artifacts/modules, and any non-shim breaking import removals.
  - Gate: `rtk .venv/bin/pytest tests/docs/test_changelog_spec_146.py -q` fails before CHANGELOG is updated.

- [x] T-6.2 — GREEN: update CHANGELOG for spec-146
  - Agent: build
  - Files: CHANGELOG.md:1
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): add concise `[Unreleased]` sections for `Fixed`, `Changed`, and `Removed`; list every deleted file/module and exact replacement or rationale; do not mention machine paths.
  - Gate: `rtk .venv/bin/pytest tests/docs/test_changelog_spec_146.py -q` passes.

- [x] T-6.3 — GREEN: write spec-146 handoff evidence
  - Agent: build
  - Files: .ai-engineering/specs/spec-146-pr-handoff.md:new; .ai-engineering/specs/spec-146-caller-inventory.md:1
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): create a handoff note summarizing decisions, files removed, files preserved, gate results, and residual follow-ups; keep it timestamp-free and path-anonymized.
  - Gate: `test -s .ai-engineering/specs/spec-146-pr-handoff.md` passes, and the project anonymous-content grep reports no machine-absolute paths in the handoff note.

- [x] T-6.4 — VERIFY: targeted quality gate suite
  - Agent: verify
  - Files: tests/:1; src/:1; .ai-engineering/:1
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): read-only verification; do not patch failures in this task unless the operator starts a bounded remediation pass.
  - Gate: `rtk .venv/bin/pytest tests/unit/state/test_ownership_state_db_read.py tests/unit/test_updater.py tests/integration/test_updater.py tests/unit/specs/test_persistence_doctrine_contract.py tests/unit/specs/test_state_canonical.py tests/architecture/test_tunables_docs_match_code.py tests/architecture/test_no_dead_module_imports.py tests/docs/test_changelog_spec_146.py -q` passes.

- [x] T-6.5 — VERIFY: sync, lint, spec lint, and full test pass
  - Agent: verify
  - Files: .ai-engineering/specs/spec.md:1; .ai-engineering/specs/plan.md:1; scripts/sync_mirrors/core.py:1
  - Principles applied: §10.5 TDD, §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): read-only verification; if failures remain, record blockers in `spec-146-pr-handoff.md` rather than silently loosening gates.
  - Gate: `rtk .venv/bin/python tools/spec_lint/cli.py --check .ai-engineering/specs/spec.md && rtk .venv/bin/ai-eng dev sync --check && rtk .venv/bin/ruff check && rtk .venv/bin/ruff format --check && rtk .venv/bin/pytest -q` passes.
