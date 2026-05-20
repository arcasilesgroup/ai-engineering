---
title: Framework Simplification — Less is More
status: draft
audience: framework-dev
branch: spec/framework-simplification-less-is-more
length_estimate: 443 lines
authoring_style: terse-cited
principles_required:
  - "§10.1 KISS"
  - "§10.2 YAGNI"
  - "§10.3 SOLID"
  - "§10.4 DRY"
  - "§10.7 Clean Code"
  - "§10.8 Hexagonal Architecture"
delivery_mode: multi-wave
mantra: "less is more"
related_briefs:
  - dx-excellence-refactor-brief.md
  - harness-persistence-strategy-brief.md
  - less-is-more-quality-engine-brief.md
  - prune-contexts-docs-research-evals-brief.md
review_notes:
  - "Corrected overclaims about gate cache, tunables, state.db rebuildability, and production-used modules before /ai-brainstorm consumption."
---

# Framework Simplification — Less is More

## 1. Vision

`ai-engineering` has accumulated structural fat across three layers: the `.ai-engineering/` data tree, the `src/ai_engineering/` Python package, and the persistence surface where SQLite, NDJSON and JSON artifacts overlap. The highest-value simplification is not a broad deletion spree; it is a narrower discipline: **fix the ownership-store bug first, align documentation with the real persistence contracts, then delete only the surfaces proven unused by production callers**. The endpoint is a framework that an operator can understand in a weekend, customize without fear, and update without losing local ownership decisions.

The simplification follows the Unix philosophy — small programs with clear boundaries [1] — and the Rails Doctrine preference for strong defaults over endless configuration [2]. Anthropic's skill-creator guidance likewise pushes lean instructions and removal of non-load-bearing material [3]. Applied here, "less is more" means every delete is evidence-backed, every datum has exactly one canonical writable store, and every migration has a test that proves the operator-visible behaviour is safer than the current one.

## 2. Scope Boundary

### In scope

- `ai-eng update` ownership respect: fix the bypass at `src/ai_engineering/updater/service.py:404-408` so operator-set deny rules stored in `state.db.ownership_map` are honoured during update.
- Ownership store read path: add a canonical SQLite reader that reconstructs the updater's `OwnershipMap` view from `state.db.ownership_map`; the writer functions exist, but no matching reader is exported today.
- `.ai-engineering/` data tree cleanup: remove byte-identical duplicates, delete genuinely dead state files, move session ephemera out of `state/`, and merge duplicate learning surfaces only after content-preserving migration.
- Persistence doctrine alignment: reconcile `docs/persistence-doctrine.md`, `state_db.py` docstrings, and live JSON consumers without asserting that all `state.db` tables are rebuildable from NDJSON.
- Gate-findings decision package: inventory JSON and SQLite consumers, then let `/ai-brainstorm` decide whether `gate-findings.json` stays canonical or migrates to `state.db.gate_findings`.
- Tunables documentation hygiene: distinguish implemented tunables from truly pending ones and reconcile `CLAUDE.md` / template docs accordingly.
- Caller-inventory-driven module simplification: delete or inline only after `src/`, `tests/`, `tools/`, `.ai-engineering/scripts/hooks/`, and template consumers are surveyed.
- Facade flattening where evidence shows behaviour-free indirection; broad removal of `StateService` / `DurableStateRepository` is gated behind public-callsite migration.

### Not in scope

- New skills, new agents, or new CLI verbs beyond helper APIs needed by the updater fix.
- Re-litigating the canonical chain `/ai-brainstorm → /ai-plan → /ai-build → /ai-pr`.
- Hard rule changes in `CONSTITUTION.md`.
- Deleting production-used trace/capability/context modules without an equivalent replacement plan.
- Removing `.ai-engineering/cache/gate/`; the cache already has age and entry-count bounds in code and only needs documentation/retention clarity.
- Retiring `gate-findings.json` without updating `risk`, `verify`, `gate`, tests, docs, and fixtures that read the JSON artifact today.
- IDE mirror format changes; mirror parity remains owned by `scripts/sync_mirrors/core.py`.

### Anti-scope

- No backwards-compat shims for files or modules that the approved spec proves safe to delete.
- No "delete because it looks unused" without caller inventory evidence.
- No new abstraction layers in service of future flexibility.

## 3. Diagnostic Snapshot

The framework carries structural debt across five dimensions. Claims below cite local `path:line` evidence where the source tree can prove them.

### 3.1 Directory duplication and unclear local state

- `.ai-engineering/references/IOCS_ATTRIBUTION.md` is byte-identical to `.ai-engineering/security/iocs/IOCS_ATTRIBUTION.md`; integration tests already treat the `security/iocs/` copy as the runtime attribution source at `tests/integration/test_sentinel_runtime_iocs.py:36` and `tests/integration/test_sentinel_runtime_iocs.py:84-92`.
- `.ai-engineering/team/lessons.md` and `.ai-engineering/LESSONS.md` both store learning rules. The control plane gives `.ai-engineering/team/**` a deny policy at `src/ai_engineering/state/control_plane.py:82` and gives `.ai-engineering/LESSONS.md` an append-only policy at `src/ai_engineering/state/control_plane.py:83`, so the two files have different update semantics despite overlapping content.
- `.ai-engineering/cache/gate/` is real session-local cache state, but it is not unbounded: `MAX_AGE_HOURS = 24` and `MAX_ENTRIES = 256` are declared at `src/ai_engineering/policy/gate_cache.py:57-58`, stale/future entries are deleted on lookup at `src/ai_engineering/policy/gate_cache.py:393-405`, and `_prune_if_oversize` evicts to the entry cap at `src/ai_engineering/policy/gate_cache.py:522-555`. The simplification target is documentation and optional manual cleanup, not cache removal.

### 3.2 State directory contracts are partially inconsistent

The `.ai-engineering/state/` surface mixes canonical stores, derived caches, and transitional JSON artifacts:

| Artifact | Current role | Evidence | Simplification stance |
|----------|--------------|----------|-----------------------|
| `framework-events.ndjson` | Canonical audit witness | `docs/persistence-doctrine.md:28-48` | Keep append-only. |
| `state.db` | Canonical for lifecycle data; derived for selected projections | `docs/persistence-doctrine.md:50-72`, `docs/persistence-doctrine.md:132-138` | Clarify table-by-table ownership. |
| `ownership_map` table | Written by installer/import flows | `src/ai_engineering/state/state_db.py:257-304`, `src/ai_engineering/state/state_db.py:638-706` | Add reader for updater. |
| `gate-findings.json` | Live gate/risk/verify JSON artifact | `src/ai_engineering/policy/orchestrator.py:759-801`, `src/ai_engineering/cli_commands/gate.py:349-359`, `src/ai_engineering/verify/service.py:45-89`, `src/ai_engineering/cli_commands/risk_cmd.py:351-387` | Open decision; do not retire blindly. |
| `state.db.gate_findings` | Schema table with seeded/migration support but not the primary read path | `src/ai_engineering/state/migrations/0001_initial_schema.py:144-165`, `src/ai_engineering/state/state_db.py:58-63` | Either make it real or document it as non-canonical. |
| `instinct-observations.ndjson` | Dead local file in current checkout; live code writes `observation-events.ndjson` | `src/ai_engineering/state/instincts.py:25` | Delete after grep proves no writer. |
| `strategic-compact.json` | Session-local hook sidecar in `state/` | `.ai-engineering/scripts/hooks/strategic-compact.py` | Move to `runtime/` if hook ownership agrees. |

The important correction: `docs/persistence-doctrine.md` does **not** say every `state.db` table is derived from NDJSON. It says `state.db` is canonical for lifecycle data at `docs/persistence-doctrine.md:50-69`, while only named caches such as `state.db.events`, `state.db.decisions`, and `state.db.ownership_map` carry rebuild contracts at `docs/persistence-doctrine.md:132-138`. The drift is that `state_db.py` still describes the whole DB as a derived projection at `src/ai_engineering/state/state_db.py:1-10` while direct writes happen for ownership and decisions at `src/ai_engineering/state/state_db.py:279-304` and `src/ai_engineering/state/state_db.py:341-360`.

### 3.3 The `ai-eng update` ownership bypass

The operator scenario is concrete: install into a test project, mark a path such as `runbooks/*` as deny/team in `state.db.ownership_map`, delete the local files, then run `ai-eng update`. The updater currently reloads ownership from a JSON sidecar at `src/ai_engineering/updater/service.py:404-408`:

```
ownership_path = state_dir / "ownership-map.json"
if ownership_path.exists():
    ownership = read_json_model(ownership_path, OwnershipMap)
else:
    ownership = OwnershipMap()
```

The installer writes default ownership rows into SQLite at `src/ai_engineering/installer/phases/state.py:115-120` and removes the legacy JSON sidecar at `src/ai_engineering/installer/phases/state.py:127-132`. The updater never imports `state_db`, so the missing JSON path yields an empty `OwnershipMap()`; `has_deny_rule()` then returns false at `src/ai_engineering/updater/service.py:865-876`, and missing files are recreated as ordinary framework files at `src/ai_engineering/updater/service.py:877-885`.

A direct call to `state_db.list_ownership_rows(project_root)` is not possible yet. `state_db.__all__` exports ownership writers but no ownership reader at `src/ai_engineering/state/state_db.py:709-720`. The spec must therefore add either `list_ownership_rows(project_root)` plus a mapper, or a higher-level `load_ownership_map(project_root) -> OwnershipMap`, before changing the updater.

### 3.4 Module inventory: confirmed candidates vs replacement-plan candidates

The caller survey separates candidates into three buckets.

**Low-risk deletion candidates after test updates:**

- `src/ai_engineering/state/agentsview.py` exposes fixture builders but is only imported by `tests/unit/test_agentsview_contract.py`; source docs mention agentsview, but no production Python caller imports it.
- `src/ai_engineering/state/outbox.py` implements a future transactional outbox; the docstring frames it as deferred scale work at `src/ai_engineering/state/outbox.py:18` and no production caller imports it.
- `src/ai_engineering/governance/policy_engine.py` self-identifies as having zero production callers and existing for downstream-fork insurance at `src/ai_engineering/governance/policy_engine.py:10-13`; `governance/__init__.py` still re-exports it at `src/ai_engineering/governance/__init__.py:18`.
- `src/ai_engineering/cli_ui_skill_ref.py` has no production import path in `src/` and is test-only in the current tree.

**Simplification candidates that require replacement plans, not direct delete:**

- `src/ai_engineering/state/trace_context.py` is production-used by `src/ai_engineering/state/observability.py`: the event builder lazy-imports `current_trace_context` and `new_span_id` at `src/ai_engineering/state/observability.py:354-363`.
- `src/ai_engineering/state/capabilities.py` is used by `observability` at `src/ai_engineering/state/observability.py:12` and `src/ai_engineering/state/observability.py:990-1008`, and by the manifest-coherence validator at `src/ai_engineering/validator/categories/manifest_coherence.py:13-16`.
- `src/ai_engineering/state/context_packs.py` is used by the manifest-coherence validator at `src/ai_engineering/validator/categories/manifest_coherence.py:17-21`; it may still be inlineable, but not dead.
- `src/ai_engineering/state/relevance.py` has no production package-side caller today; the hook-side copy exists at `.ai-engineering/scripts/hooks/_lib/relevance.py:29`, but tests still assert package behaviour. Deletion must decide whether hook-only relevance remains acceptable.

**Facade and registry candidates:**

- `StateService` and `DurableStateRepository` are not dead. They are imported by multiple production flows, including gate/risk/update/install/doctor code paths (`src/ai_engineering/cli_commands/gate.py:47`, `src/ai_engineering/cli_commands/risk_cmd.py:52`, `src/ai_engineering/updater/service.py:51`, `src/ai_engineering/installer/service.py:71-72`, `src/ai_engineering/doctor/phases/state.py:44`). They may be over-broad, but removal requires staged callsite migration.
- `src/ai_engineering/installer/tool_registry.py` is a large registry used by installer and doctor phases at `src/ai_engineering/installer/phases/tools.py:48` and `src/ai_engineering/doctor/phases/tools.py:42`; replacing it with constants is an open design choice, not an automatic delete.
- `src/ai_engineering/installer/mechanisms/__init__.py` is 844 lines and explicitly centralizes mechanism classes for the registry at `src/ai_engineering/installer/mechanisms/__init__.py:9-32`; splitting by mechanism is low-risk if imports remain stable.

### 3.5 Tunables drift, not blanket absence

The `CLAUDE.md` runtime tunables block marks M2/M5/M6 variables as pending at `CLAUDE.md:189-197`, and the template source mirrors those lines at `src/ai_engineering/templates/project/CLAUDE.md:189-197`. Several of those variables are implemented despite the pending label:

- `AIENG_HOOK_CACHE_TTL_SEC` is read by the prompt-injection guard cache at `.ai-engineering/scripts/hooks/prompt-injection-guard.py:81-95` and used for catalog cache freshness at `.ai-engineering/scripts/hooks/prompt-injection-guard.py:499-505`.
- `AIENG_AUTOFORMAT_DEBOUNCE_SEC` is read by the auto-format hook at `.ai-engineering/scripts/hooks/auto-format.py:50-65`.
- `AIENG_NDJSON_MAX_LINES` and `AIENG_NDJSON_MAX_BYTES` are read by SessionEnd rotation logic at `.ai-engineering/scripts/hooks/runtime-session-end.py:74-90`.
- `AIENG_HOST_PREFLIGHT_*` appears to remain documentation-only for the host-preflight controls; `emit_host_capacity` exists at `src/ai_engineering/state/observability.py:839-877`, but grep does not find those exact env names in implementation code.

The simplification target is therefore **documentation/code reconciliation**: remove pending labels for implemented variables, delete or clearly reserve genuinely unimplemented variables, and keep the docs test honest.

## 4. Architecture

### 4.1 Target shape — four clear buckets, one writer per datum

```
.ai-engineering/
  reference/                      # canonical reference docs
  manifest.yml                    # operator config
  specs/                          # markdown spec/plan/decision narrative
  state/
    framework-events.ndjson       # canonical audit witness
    state.db                      # canonical lifecycle DB + named derived caches
    hooks-manifest.json           # hook integrity config artifact
    gate-findings.json            # keep unless spec explicitly migrates all consumers
  cache/gate/                     # bounded ephemeral gate cache
  runtime/                        # session ephemera, gitignored
  team/                           # operator/team local content
```

Deleted or moved only after evidence: `.ai-engineering/references/` if the security/iocs copy is canonical, `.ai-engineering/state/instinct-observations.ndjson` if no writer exists, `.ai-engineering/state/strategic-compact.json` if the hook can use `runtime/`, and `.ai-engineering/team/lessons.md` after content merges into `.ai-engineering/LESSONS.md`.

### 4.2 SSOT rule — table-by-table, not slogan-by-slogan

The persistence doctrine remains the anchor:

- **Audit events** live in `framework-events.ndjson`; the `state.db.events` table is a query projection rebuilt by `ai-eng audit index --rebuild` per `docs/persistence-doctrine.md:132-134`.
- **Lifecycle data** that needs update/delete/query semantics lives in `state.db` per `docs/persistence-doctrine.md:50-69`.
- **Markdown decisions/specs** remain human-authored truth; `state.db.decisions` is a derived cache from spec markdown per `docs/persistence-doctrine.md:135-138`.
- **Gate findings** need an explicit decision because current code and docs still route many consumers through `gate-findings.json`.

The spec should replace broad claims like "state.db is rebuilt from NDJSON" with a table inventory: source of truth, writer, reader, rebuild command if derived, and migration owner.

### 4.3 Ownership respect rule

`ai-eng update` must consult canonical ownership before planning file creates or updates. The target flow:

1. Add `state_db.list_ownership_rows(project_root)` returning raw `ownership_map` rows, plus `state_db.load_ownership_map(project_root)` or an updater-local mapper that reconstructs `OwnershipMap` entries.
2. `_initialize_update_context` at `src/ai_engineering/updater/service.py:395-430` loads ownership from SQLite first, not from `ownership-map.json`.
3. A one-time legacy fallback may read `ownership-map.json` only if SQLite has no rows and the JSON file exists, then upsert rows and delete the sidecar.
4. `_evaluate_file_change` continues to enforce deny rules at `src/ai_engineering/updater/service.py:865-876` and `is_update_allowed()` for existing files at `src/ai_engineering/updater/service.py:887-895`, but now against the canonical map.
5. A dry-run report lists skipped files with their matched ownership rule.

This deliberately differs from Copier `_skip_if_exists`: Copier skips files that already exist and recreates them if missing during update [5]. The ai-engineering rule is stricter: an operator deny rule means "do not recreate this path even if it is missing".

### 4.4 Updater philosophy — preserve operator intent, not accidental files

The current `ai-eng update` behaves like a partial reinstall when the JSON ownership sidecar is absent. The target model is closer to a template-update merge workflow with explicit local ownership: framework-owned files may update, operator/team-owned files are skipped, and denied paths stay absent if the operator removed them. Conflicts should surface in a pre-update report rather than being silently overwritten.

External template tools are prior art for merge workflows, not binding semantics. Copier supports update workflows and skip patterns [5], Homebrew documents local override workflows [7], and mise separates tool updates from project version changes [8]. The ai-engineering-specific invariant is stronger: **the ownership map is the policy authority, not file existence**.

### 4.5 Package layer rationalisation

For `src/ai_engineering/`, simplification proceeds in descending confidence:

- **Delete after inventory**: `agentsview.py`, `outbox.py`, `governance/policy_engine.py`, and `cli_ui_skill_ref.py` if grep + tests confirm no production dependency.
- **Inline only with replacement tests**: `context_packs.py`, `relevance.py`, and selected forwarding shims.
- **Preserve or migrate carefully**: `trace_context.py` and `capabilities.py` because they have production consumers.
- **Flatten facades after public API exists**: migrate `StateService` / `DurableStateRepository` callers to explicit `state_db` helpers in waves; do not remove both classes until risk/gate/install/doctor/update callsites are gone.
- **Split oversized modules**: move mechanism classes out of `installer/mechanisms/__init__.py` into one file per mechanism with a thin re-export surface.

### 4.6 Hexagonal boundary

The simplification reinforces the §10.8 hexagonal boundary visible in `.ai-engineering/reference/architecture-patterns.md`:

```
        ┌─────────────────────────────────────────┐
        │  CLI commands (cli_commands/*.py)       │  primary adapter
        ├─────────────────────────────────────────┤
        │  Domain functions:                      │
        │   - updater.compute_file_changes()      │  pure where possible
        │   - ownership.match_rule()              │  pure
        │   - gate cache freshness policy         │  pure
        ├─────────────────────────────────────────┤
        │  Secondary adapters:                    │
        │   - state_db (SQLite lifecycle state)   │  IO
        │   - filesystem (template/file copy)     │  IO
        │   - framework-events.ndjson (audit)     │  IO
        │   - gate-findings.json if retained      │  IO
        └─────────────────────────────────────────┘
```

The target is not "no service classes" as a dogma. The target is clear adapters, pure domain decisions where feasible, and no facade layer that exists solely to bounce a call to another facade.

## 5. Evidence Catalog

| # | Claim | Source |
|---|-------|--------|
| 1 | `IOCS_ATTRIBUTION.md` runtime test reads the `security/iocs` copy | `tests/integration/test_sentinel_runtime_iocs.py:36`, `tests/integration/test_sentinel_runtime_iocs.py:84-92` |
| 2 | `team/**` and `LESSONS.md` have different update policies | `src/ai_engineering/state/control_plane.py:82-83` |
| 3 | Gate cache already has age and count bounds | `src/ai_engineering/policy/gate_cache.py:57-58`, `src/ai_engineering/policy/gate_cache.py:393-405`, `src/ai_engineering/policy/gate_cache.py:522-555` |
| 4 | Persistence doctrine says `state.db` is canonical for lifecycle data | `docs/persistence-doctrine.md:50-69` |
| 5 | Persistence doctrine names derived cache rows explicitly | `docs/persistence-doctrine.md:132-138` |
| 6 | `state_db.py` docstring still describes the DB as a derived projection | `src/ai_engineering/state/state_db.py:1-10` |
| 7 | Ownership is written to SQLite | `src/ai_engineering/state/state_db.py:257-304`, `src/ai_engineering/state/state_db.py:638-706` |
| 8 | No ownership reader is exported from `state_db` today | `src/ai_engineering/state/state_db.py:709-720` |
| 9 | Updater reads ownership from legacy JSON | `src/ai_engineering/updater/service.py:404-408` |
| 10 | Installer writes ownership rows and deletes sidecar JSON | `src/ai_engineering/installer/phases/state.py:115-132` |
| 11 | Updater create path consults `has_deny_rule()` only after loading its ownership map | `src/ai_engineering/updater/service.py:865-885` |
| 12 | `gate-findings.json` is written/read by multiple live surfaces | `src/ai_engineering/policy/orchestrator.py:759-801`, `src/ai_engineering/cli_commands/gate.py:349-359`, `src/ai_engineering/verify/service.py:45-89`, `src/ai_engineering/cli_commands/risk_cmd.py:351-387` |
| 13 | `state.db.gate_findings` exists but `state_db.py` calls it a placeholder | `src/ai_engineering/state/migrations/0001_initial_schema.py:144-165`, `src/ai_engineering/state/state_db.py:58-63` |
| 14 | `trace_context.py` is production-used by observability | `src/ai_engineering/state/observability.py:354-363` |
| 15 | `capabilities.py` is production-used by observability and validator code | `src/ai_engineering/state/observability.py:12`, `src/ai_engineering/state/observability.py:990-1008`, `src/ai_engineering/validator/categories/manifest_coherence.py:13-16` |
| 16 | `context_packs.py` is used by manifest coherence | `src/ai_engineering/validator/categories/manifest_coherence.py:17-21` |
| 17 | `policy_engine.py` is a downstream-fork insurance shim | `src/ai_engineering/governance/policy_engine.py:10-13`, `src/ai_engineering/governance/__init__.py:18` |
| 18 | `outbox.py` is deferred future-scale code | `src/ai_engineering/state/outbox.py:18` |
| 19 | `StateService` and `DurableStateRepository` have multiple production callers | `src/ai_engineering/cli_commands/gate.py:47`, `src/ai_engineering/cli_commands/risk_cmd.py:52`, `src/ai_engineering/updater/service.py:51`, `src/ai_engineering/installer/service.py:71-72` |
| 20 | `installer/mechanisms/__init__.py` centralizes registry mechanism classes | `src/ai_engineering/installer/mechanisms/__init__.py:9-32` |
| 21 | `tool_registry.py` is used by installer and doctor phases | `src/ai_engineering/installer/phases/tools.py:48`, `src/ai_engineering/doctor/phases/tools.py:42` |
| 22 | `CLAUDE.md` marks M2/M5/M6 tunables pending | `CLAUDE.md:189-197`, `src/ai_engineering/templates/project/CLAUDE.md:189-197` |
| 23 | Hook cache TTL env var is implemented | `.ai-engineering/scripts/hooks/prompt-injection-guard.py:81-95`, `.ai-engineering/scripts/hooks/prompt-injection-guard.py:499-505` |
| 24 | Auto-format debounce env var is implemented | `.ai-engineering/scripts/hooks/auto-format.py:50-65` |
| 25 | NDJSON max lines/bytes env vars are implemented | `.ai-engineering/scripts/hooks/runtime-session-end.py:74-90` |
| 26 | Host capacity event exists, but host-preflight env names are not implemented in source grep | `src/ai_engineering/state/observability.py:839-877`, `scripts/sync_mirrors/core.py:1118-1120` |

## 6. Roadmap

The work decomposes into five waves. Wave 1 is the operator-visible bug fix; later waves simplify only after the evidence gates pass.

### Wave 1 — Ownership respect bug fix

- Add `state_db.list_ownership_rows(project_root)` and a tested mapper to `OwnershipMap`.
- Update `_initialize_update_context` to load ownership from SQLite first.
- Keep a one-time legacy JSON migration path only for projects with no SQLite ownership rows.
- Add integration test: install in tmp project, add deny/team ownership row for a path, delete the file, run `ai-eng update`, assert the file stays absent and report says skip-denied.
- Gate: unit tests for SQLite roundtrip and integration test for the operator scenario pass.

### Wave 2 — Persistence doctrine reconciliation

- Update `state_db.py` docstring and `docs/persistence-doctrine.md` so each `state.db` table is classified as canonical, derived cache, or transitional.
- Inventory `gate-findings.json` consumers and choose either JSON-retained or SQLite-promoted path in `/ai-brainstorm`.
- If SQLite is chosen, add read/write helpers and migrate `risk`, `verify`, `gate`, docs, fixtures, and orchestrator in one scoped wave.
- Gate: no doc line claims that all `state.db` tables rebuild from NDJSON unless the listed rebuild command actually does so.

### Wave 3 — Data tree cleanup

- Delete `.ai-engineering/references/` only after all links point to `.ai-engineering/security/iocs/`.
- Delete `.ai-engineering/state/instinct-observations.ndjson` if grep confirms no writer and no reader.
- Move `strategic-compact.json` to `.ai-engineering/runtime/` if hook code and tests agree.
- Merge `.ai-engineering/team/lessons.md` into `.ai-engineering/LESSONS.md` with duplicate detection; then delete the team copy.
- Document `.ai-engineering/cache/gate/` as bounded ephemeral cache; add a manual cleanup command only if existing `ai-eng gate cache clear` is insufficient.
- Gate: file-existence tests, docs links, and state-plane contract tests pass.

### Wave 4 — Tunables docs/code reconciliation

- Convert implemented variables (`AIENG_HOOK_CACHE_TTL_SEC`, `AIENG_AUTOFORMAT_DEBOUNCE_SEC`, `AIENG_NDJSON_MAX_LINES`, `AIENG_NDJSON_MAX_BYTES`) from "pending" docs rows to default-bearing docs rows.
- Remove or clearly reserve genuinely unimplemented `AIENG_HOST_PREFLIGHT_*` and `AIENG_HOOK_BUDGET_PROFILE` entries.
- Update `tests/architecture/test_tunables_docs_match_code.py` so pending markers only cover actually pending variables.
- Regenerate mirrors from `scripts/sync_mirrors/core.py`.
- Gate: tunables architecture test passes and root mirrors remain byte-equivalent.

### Wave 5 — Caller-inventory simplification

- Add or run a caller inventory script that distinguishes production callers from tests/docs/spec archives.
- Delete low-risk candidates (`agentsview.py`, `outbox.py`, `governance/policy_engine.py`, `cli_ui_skill_ref.py`) only after test updates prove no production break.
- Split `installer/mechanisms/__init__.py` into one mechanism module per class with stable imports.
- Migrate `StateService` / `DurableStateRepository` callsites to explicit helpers where it reduces layers; keep compatibility only until all internal callers move.
- Treat `trace_context.py`, `capabilities.py`, and `context_packs.py` as replacement-plan work, not dead-code work.
- Gate: full test suite green; no production import is left dangling; no `__init__.py` exceeds the agreed line budget.

### Wave sequencing

Wave 1 can land independently and should be prioritized because it fixes data loss by respecting operator-set ownership. Waves 2 and 3 can proceed in parallel after Wave 1. Wave 4 is mostly docs/tests and can land separately. Wave 5 depends on the inventories from Waves 2/3 and should be split if it exceeds 1500 net line changes.

## 7. Definition of Done

The framework is "less is more" when all of these are simultaneously true:

1. `ai-eng update` honours `state.db.ownership_map` deny rules, including the operator scenario where a denied missing file stays missing.
2. `state_db` exposes tested ownership read helpers and updater code no longer depends on `ownership-map.json` for normal operation.
3. `docs/persistence-doctrine.md` and `state_db.py` classify every `state.db` table accurately as canonical, derived cache, or transitional.
4. Gate findings have one approved canonical path; if JSON remains, `state.db.gate_findings` is documented as non-primary or removed; if SQLite wins, every JSON consumer is migrated.
5. `.ai-engineering/` has no byte-identical duplicate directory for IOC attribution and no dead zero-byte state artifact.
6. `.ai-engineering/cache/gate/` is documented as bounded ephemeral cache; no spec claims it lacks TTL/count bounds.
7. `CLAUDE.md` lists only implemented tunables with defaults plus explicitly reserved pending variables that tests recognize.
8. No production-used module is deleted without an equivalent replacement path and regression tests.
9. Low-risk dead modules are removed only after caller inventory passes across `src/`, `tests/`, `tools/`, hooks, templates, and docs.
10. `installer/mechanisms/__init__.py` shrinks to a thin import surface or receives an explicit exemption.
11. `StateService` / `DurableStateRepository` are either reduced to useful adapter boundaries or removed after internal callsites migrate.
12. CHANGELOG documents every hard delete under "Removed" with rationale.
13. Existing CI gates remain green; no test is deleted solely to make a simplification pass.
14. Pre-commit and pre-push hot-path budgets do not regress.

## 8. Quality Stamps

| Standard | Application |
|----------|-------------|
| **§10.1 KISS** | Fix the ownership read path directly before designing a broader persistence platform. Keep gate cache as cache, not as a new DB table. |
| **§10.2 YAGNI** | Delete downstream-fork insurance and future-scale modules only when caller inventory proves they are not load-bearing. Do not invent new migration layers. |
| **§10.3 SOLID — SRP** | `_initialize_update_context` should load context, not run unrelated migrations. Ownership mapping gets one reader/mapping boundary. |
| **§10.4 DRY** | Consolidate ownership defaults and SQLite/JSON ownership logic. Avoid parallel docs that describe tunables differently from implementation. |
| **§10.7 Clean Code** | Split oversized `__init__.py` files and remove forwarding shims where no public import contract exists. |
| **§10.8 Hexagonal Architecture** | SQLite, filesystem, NDJSON, and JSON artifacts stay explicit adapters; domain decisions such as ownership matching are pure and testable. |

The cross-cutting harness standard is honoured only if every simplification is backed by deterministic tests and by file-evidence in this brief. The brief intentionally rejects "looks unused" as sufficient evidence.

## 9. Open Decisions

The brief leaves six choices for `/ai-brainstorm` to resolve with the operator:

1. **Ownership reader shape.** Should the new API be raw (`list_ownership_rows`) plus mapper, or high-level (`load_ownership_map`) returning the updater model? Default: expose both; use high-level in updater and raw in diagnostics.
2. **`gate-findings.json` vs `state.db.gate_findings`.** Keep JSON as canonical because many current consumers depend on it, or promote SQLite and migrate every consumer in one wave? Default: keep JSON unless `/ai-brainstorm` accepts the larger migration.
3. **Gate cache lifecycle.** Is current 24h/256-entry policy enough, or should there be explicit directory-level cleanup docs/CLI? Default: document existing bounds and reuse `ai-eng gate cache clear`.
4. **Trace/capability/context module treatment.** Inline production-used modules or keep them as adapter boundaries? Default: do not delete `trace_context.py` or `capabilities.py` in this spec; inventory first.
5. **Tunables policy.** Remove truly unimplemented host-preflight/budget-profile entries, or keep them as explicit reservations? Default: default-bearing docs for implemented variables; one clearly labelled reserved block for true roadmap vars.
6. **Brief consolidation.** Should overlapping drafts be superseded by this spec, or should this brief consume only the ownership + simplification slice? Default: mark overlaps only after the approved spec has a final scope.

## 10. Migration

### 10.1 Hard delete only after proof

- No backwards-compat shims for approved deletions.
- Deletions require caller inventory, tests, and CHANGELOG rationale.
- Renames use `git mv`; no parallel deprecated path.
- Test-only APIs may be removed with tests updated in the same PR; production APIs need callsite migration first.

### 10.2 Operator-facing ownership migration

`ai-eng update` after Wave 1 will:

1. Open `state.db` and load ownership rows.
2. If the table is empty and legacy `ownership-map.json` exists, read it once, upsert rows into SQLite, and delete the JSON sidecar.
3. Produce a dry-run report showing files skipped because of deny/team/operator rules.
4. Leave denied missing files absent.

The migration is idempotent. A second invocation sees SQLite rows and ignores the removed JSON sidecar.

### 10.3 Downstream forks

This is a breaking-change program only for waves that delete public import paths. The release notes must separately flag:

- Any removal of `governance.policy_engine` and the direct replacement (`governance.opa_runner` or a new helper).
- Any removal of forwarding shims and their canonical import targets.
- Any `StateService` / `DurableStateRepository` API removal after internal callsites migrate.
- Any gate-findings canonical-path change, if `/ai-brainstorm` chooses SQLite.

Forks that depended on deleted shims break. The remedy is documented in CHANGELOG; no shim is preserved.

## 11. Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| 1 | Ownership reader maps SQLite rows incorrectly into `OwnershipMap` semantics | Medium | High | Add unit roundtrip tests for allow/deny/append-only and integration test for deleted denied path. |
| 2 | `gate-findings.json` migration breaks risk/verify/gate workflows | Medium | High | Treat as open decision; inventory consumers before changing canonical path. |
| 3 | A module labelled low-risk has a hook/template consumer outside `src/` | Medium | Medium | Inventory `src`, `tests`, `tools`, `.ai-engineering/scripts/hooks`, templates, docs, and archived specs before deletion. |
| 4 | Docs/code tunables reconciliation removes a variable that is implemented but poorly documented | Medium | Medium | Grep exact env names and update docs tests before removing docs rows. |
| 5 | Moving `strategic-compact.json` to `runtime/` breaks hook assumptions | Low | Medium | Patch hook + tests in same wave; keep state file untouched until tests prove runtime path. |
| 6 | Facade flattening creates a huge PR | Medium | Medium | Split Wave 5 into facade-callsite migration, mechanisms split, and dead-module delete PRs. |
| 7 | Hard delete breaks downstream forks | Medium | Medium | CHANGELOG and release notes list each import removal and replacement. No shim, but clear remedy. |
| 8 | Hot-path budget regresses | Low | High | Ownership reader runs in `ai-eng update`, not commit hooks; run existing hot-path budget tests anyway. |
| 9 | Overlapping drafts conflict on persistence doctrine | Medium | Medium | During `/ai-brainstorm`, decide whether this brief supersedes or narrows the older persistence/simplification drafts. |

## 12. References

External evidence — all sources accessed 2026-05-19.

1. Unix philosophy — Doug McIlroy's "do one thing well" summary. [The Unix Design Philosophy](https://inkgray.com/posts/unix-design-philosophy/); [Unix philosophy — Wikipedia](https://en.wikipedia.org/wiki/Unix_philosophy).
2. The Ruby on Rails Doctrine — omakase and convention over configuration. [The Ruby on Rails Doctrine](https://rubyonrails.org/doctrine); [What is Convention over Configuration in Rails — Avo](https://avohq.io/glossary/convention-over-configuration).
3. Anthropic skill-creator canonical structure — lean SKILL.md guidance and removing non-load-bearing material. [skill-creator SKILL.md — anthropics/skills](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md); [The Complete Guide to Building Skills for Claude](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf).
4. Event sourcing + snapshot derivation prior art. [Event Sourcing — Martin Fowler](https://martinfowler.com/eaaDev/EventSourcing.html); [Snapshots in Event Sourcing — Kurrent](https://www.kurrent.io/blog/snapshots-in-event-sourcing); [Event Sourcing Pattern — Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing).
5. Copier docs: `copier update` preserves local changes, and `_skip_if_exists` skips existing files but recreates them if missing during update. [Copier docs — Updating](https://copier.readthedocs.io/en/stable/updating/); [Copier docs — Configuring a template](https://copier.readthedocs.io/en/stable/configuring/).
6. (Internal) The three-layer facade pattern in `src/ai_engineering/state/service.py` and `src/ai_engineering/state/repository.py`; see Evidence Catalog #19 before deletion.
7. Homebrew local override pattern. [Homebrew FAQ](https://docs.brew.sh/FAQ); [Homebrew Manpage](https://docs.brew.sh/Manpage).
8. mise/asdf update separation — updating the tool does not automatically change project tool versions. [mise docs — Settings](https://mise.jdx.dev/configuration/settings.html); [Mise vs asdf — Better Stack](https://betterstack.com/community/guides/scaling-nodejs/mise-vs-asdf/); [asdf — Configuration](https://asdf-vm.com/manage/configuration.html).

## 13. Glossary

- **SSOT (Single Source of Truth)** — for a given datum, exactly one canonical writable store; other copies are named derived caches with rebuild commands.
- **Derived cache** — a projection rebuildable from a canonical source. Example: `state.db.events` from `framework-events.ndjson`.
- **Lifecycle data** — mutable framework state that needs update/delete/query semantics, such as ownership, install state, risk acceptances, and selected decision/cache tables.
- **Ownership rule** — path-pattern policy used by `ai-eng update` to decide whether a framework update may create or modify a file.
- **Deny rule** — an ownership rule that blocks create/update even when a template file is missing locally.
- **Operator-owned file** — a file protected from framework overwrite by ownership policy.
- **Gate findings artifact** — the current JSON document `.ai-engineering/state/gate-findings.json` consumed by gate/risk/verify flows unless the spec migrates every consumer to SQLite.
- **Caller inventory** — grep/import/test evidence across source, hooks, templates, docs, and tests that classifies a module as production-used, test-only, doc-only, or unused.
- **Facade flatten** — replacing behaviour-free service/repository forwarding with explicit helpers while preserving useful adapter boundaries.
- **Hard delete** — Constitution §13.3 rule: approved deletion happens directly with CHANGELOG documentation and no compatibility shim.

## 14. Acceptance

The following checklist is the contract `/ai-brainstorm` consumes to produce `spec.md`.

- [ ] `state_db.list_ownership_rows(project_root)` and/or `state_db.load_ownership_map(project_root)` implemented with unit tests.
- [ ] `src/ai_engineering/updater/service.py:_initialize_update_context` reads canonical ownership from SQLite before evaluating file changes.
- [ ] Legacy `ownership-map.json` is used only as one-time migration fallback when SQLite ownership rows are absent.
- [ ] Operator integration test proves: install → add deny/team rule → delete matching file → `ai-eng update` leaves file absent and reports skip-denied.
- [ ] `docs/persistence-doctrine.md` and `src/ai_engineering/state/state_db.py` agree on which tables are canonical and which are derived caches.
- [ ] `gate-findings.json` canonical-path decision recorded; if SQLite wins, all JSON consumers listed in Evidence Catalog #12 are migrated.
- [ ] `.ai-engineering/references/` removed only after links/tests point to `.ai-engineering/security/iocs/IOCS_ATTRIBUTION.md`.
- [ ] `.ai-engineering/state/instinct-observations.ndjson` removed after grep confirms no writer/reader.
- [ ] `strategic-compact.json` either remains documented in `state/` or moves to `runtime/` with hook tests updated.
- [ ] `.ai-engineering/team/lessons.md` content merged into `.ai-engineering/LESSONS.md` without duplicate loss, then removed if operator approves.
- [ ] `.ai-engineering/cache/gate/` documented as bounded cache; no acceptance item claims missing TTL/count bounds.
- [ ] Implemented tunables (`AIENG_HOOK_CACHE_TTL_SEC`, `AIENG_AUTOFORMAT_DEBOUNCE_SEC`, `AIENG_NDJSON_MAX_LINES`, `AIENG_NDJSON_MAX_BYTES`) documented with defaults instead of pending labels.
- [ ] Truly pending tunables (`AIENG_HOST_PREFLIGHT_*`, `AIENG_HOOK_BUDGET_PROFILE`, if still unimplemented) are either removed from docs or explicitly reserved with tests updated.
- [ ] Caller inventory artifact classifies each deletion/inlining candidate as production, test, doc, template, or unused.
- [ ] `src/ai_engineering/state/trace_context.py` and `src/ai_engineering/state/capabilities.py` are not deleted unless replacement tests prove observability and manifest-coherence behaviour still work.
- [ ] Low-risk candidates (`agentsview.py`, `outbox.py`, `governance/policy_engine.py`, `cli_ui_skill_ref.py`) removed only after test updates and import inventory pass.
- [ ] `installer/mechanisms/__init__.py` split or explicitly exempted with rationale.
- [ ] `StateService` / `DurableStateRepository` migration plan lists every production callsite before removal.
- [ ] `scripts/sync_mirrors/core.py` regenerated root/template mirrors after `CLAUDE.md` tunables changes.
- [ ] CHANGELOG entries document each removal under "Removed" with rationale.
- [ ] No CI test deleted solely to make simplification pass.
- [ ] Hot-path budget tests remain green.
- [ ] Overlapping drafts are marked superseded only after `/ai-brainstorm` approves the final scope.
