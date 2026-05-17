---
spec: spec-138
slug: harness-persistence-strategy
title: Plan — Harness Persistence Strategy
pipeline: build
phases: 5
status: approved
branch: claude/review-spec-drafts-DX2pD
date_approved: 2026-05-16
auto_approved: true
single_concern: false
---

# Plan — spec-138 Harness Persistence Strategy

Five phases mapped to the brief's M1–M5 milestones. TDD-first; every change carries a contract or unit test that fails before the implementation lands.

## Branch / PR

- Working branch: `claude/review-spec-drafts-DX2pD`
- Target: `main` via single PR carrying spec-138 + spec-139 + spec-140 + spec-141 (multi-spec autonomous run).

## Quality bar

- §10.5 TDD: every new test RED before code.
- §10.4 DRY applied to STORES (not writers): two stores with the same datum is the violation we close; one store with multiple writers is acceptable.
- No `# noqa`, `# nosec`, `// @ts-ignore`, etc. per CONSTITUTION.md §13.
- No backwards-compatibility shims; CHANGELOG documents every removal.

## Phase M1 — Bug Clearance

**Anchor:** §10.7 Clean Code (truth in data flow); CONSTITUTION.md §13.3 (hard rename / hard delete).

### Tasks

- **M1.T0 — Survey 12 `decision-store.json` callers (D-138-04).** Grep `decision-store.json` across `src/`, `.ai-engineering/`, `tools/`, `tests/`. Catalog every read-site. Produce `runtime/session-orchestration/decision-store-callers.md`. Decide per-caller: migrate to `state.db.decisions` read OR remove the call (when the data is unused).
- **M1.T1 — Delete `_insert_events_row`.** Remove function from `src/ai_engineering/governance/decision_log.py` (lines 115-157). Remove call from `emit_policy_decision`. Update `tests/unit/governance/test_decision_log.py` to assert only the NDJSON emit; drop the fake `events` table fixture.
- **M1.T2 — Remove `audit-index.sqlite` zombie.** Delete the 0-byte file from the repo. Rewrite `src/ai_engineering/state/audit_index.py` so `_LEGACY_INDEX_REL` and the lazy-delete branch are gone; `INDEX_REL` points to `state.db` exclusively.
- **M1.T3 — Fix `runtime-stop.py:474`.** Replace the legacy `audit-index.sqlite` open with a `state.db` connection guarded by a `tables_present` check (skip read when `events` table is empty — first session before any SessionEnd rebuild).
- **M1.T4 — Diagnose Bug 5 (current session hooks not emitting).** Read `.claude/settings.json` event registration, manually invoke `runtime-session-start.py` with the expected env, capture stderr. Document findings in `runtime/session-orchestration/bug-5-diagnostic.md`. If root cause is Claude Desktop CWD/stdin behavior independent of this spec, file upstream and continue.
- **M1.T5 — Remove `repository.save_decisions` JSON dual-write.** Delete the `write_json_model` call to `decision-store.json` at `src/ai_engineering/state/repository.py:154-168`. Update tests.
- **M1.T6 — Add `tests/unit/state/test_sql_writer_schemas.py`.** Test imports every module in `src/ai_engineering/` that contains `INSERT INTO`, parses the column list, compares to the canonical schema declared in `0001_initial_schema.py`. RED before any production fix; GREEN after M1.T1 and M1.T5.

### Acceptance gate

- `pytest tests/unit/governance/test_decision_log.py tests/unit/state/test_repository.py tests/unit/state/test_sql_writer_schemas.py` green.
- `grep -rn "_insert_events_row\|decision-store.json\|_LEGACY_INDEX_REL\|audit-index.sqlite"` returns no production hits (test fixtures and archived specs allowed).
- `ls .ai-engineering/state/audit-index.sqlite` returns `No such file or directory`.

## Phase M2 — Doctrine Landing

**Anchor:** §10.6 SDD; §10.7 Clean Code; CONSTITUTION.md anonymous-content rule.

### Tasks

- **[x] M2.T1 — Author `docs/persistence-doctrine.md`.** Four tiers with one-line summaries; SSOT-PD rule statement; rebuild semantics for derived caches; glossary (Article-III, derived cache, hot path, SSOT-PD, tier).
- **[x] M2.T2 — Amend CONSTITUTION.md.** Add a hard rule under §13 (data layer) referencing the doctrine: "Every datum has exactly one canonical store. Derived caches are explicitly labelled and rebuildable on demand."
- **[x] M2.T3 — Update CLAUDE.md §0 bootstrap.** Replace the broken `state.db.decisions` query instruction with a doctrine pointer; preserve §0 structure (read CONSTITUTION → read manifest → read doctrine → no implementation without an approved spec).
- **[x] M2.T4 — Regenerate mirror surfaces.** Run `python scripts/sync_mirrors/core.py` so `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md` carry the same canonical block (mirrors stay lean per D-138-05).
- **[x] M2.T5 — Add `tests/architecture/test_persistence_doctrine_exists.py`.** Asserts the file exists, has the four-tier section headers, and CLAUDE.md §0 contains the pointer.

### Acceptance gate

- `docs/persistence-doctrine.md` non-empty with §1 SSOT-PD rule, §2 four tiers, §3 rebuild semantics, §4 glossary.
- CONSTITUTION.md amended and CHANGELOG documents the addition.
- All four IDE mirrors byte-equivalent (existing `tests/architecture/test_surface_parity.py` still green).

## Phase M3 — Autopopulation

**Anchor:** §10.4 DRY (one writer per datum); §10.3 SOLID single responsibility.

### Tasks

- **[x] M3.T1 — `/ai-brainstorm` writes decisions to `state.db.decisions`.** At spec-approval handler in `src/ai_engineering/brainstorm/`, call `upsert_decision_rows` for every `D-NNN-NN` in the approved spec. Cold path — fired once per approval. (`src/ai_engineering/brainstorm/spec_approval.py::handle_spec_approval`.)
- **[x] M3.T2 — `/ai-plan` upserts decisions when the plan introduces new ones.** Same writer; idempotent on duplicate D-IDs. (Shared `handle_spec_approval` entry point accepts `plan.md` paths.)
- **[x] M3.T3 — `ai-eng decision backfill`.** New CLI subcommand under `ai-eng decision` group. Parses `.ai-engineering/specs/*.md`, `.ai-engineering/specs/archive/*.md`, and `CHANGELOG.md`, extracts `D-NNN-NN` patterns with rationale strings, populates `state.db.decisions`. Idempotent on re-run. Summary line distinguishes `backfilled` vs `already_current`.
- **[x] M3.T4 — Installer wires `install_steps`.** After each completed installer phase, `PipelineRunner._record_step` calls `upsert_install_step` with the step ID and outcome (`done` / `failed` / `non_critical_failure`). Cold path — fired during install only. Fail-open: an UPSERT error never masks a phase failure.
- **[x] M3.T5 — `ai-eng ownership import`.** Parse `.github/CODEOWNERS` (or `--source <path>`), populate `state.db.ownership_map`. New `ownership_app` Typer group registered in `cli_factory`.
- **[x] M3.T6 — Unit tests for each writer.** `tests/unit/state/test_decision_writer_integration.py`, `tests/unit/cli/test_decision_backfill.py`, `tests/unit/installer/test_install_steps_writer.py`, `tests/unit/cli/test_ownership_import.py` (23 cases total, all green).

### Acceptance gate

- After fresh install + `ai-eng decision backfill`, `SELECT COUNT(*) FROM decisions` > 0.
- After `ai-eng ownership import`, `SELECT COUNT(*) FROM ownership_map` > 0.
- No hot-path hook imports `sqlite3` (covered by M4.T4 contract test).

## Phase M4 — Events as Derived Cache + NDJSON Rotation

**Anchor:** Article-III preservation; spec-135 hot-path budget.

### Tasks

- **M4.T1 — Document `state.db.events` as derived cache.** Update `docs/persistence-doctrine.md` and the migration docstring at `0003_replay_ndjson.py` to declare derived semantics.
- **M4.T2 — `ai-eng audit index --rebuild` is the sole writer.** Audit all callers of `state.db.events` INSERT path; ensure only `audit_index.build_index` reaches it.
- **M4.T3 — Wire SessionEnd rebuild.** Add `audit_index.rebuild_at_session_end()` invocation to `.ai-engineering/scripts/hooks/runtime-session-end.py` with a 5-second budget guard.
- **M4.T4 — Wire NDJSON rotation.** In `runtime-session-end.py`, after rebuild, check `framework-events.ndjson` size/lines; if above thresholds (100k lines OR 50 MB), invoke `ai-eng maintenance reset-events --auto`. (spec-139 M6 adds the throttle wrapper around this.)
- **M4.T5 — Add `tests/architecture/test_no_sql_on_hot_path.py`.** For every script registered under PreToolUse / PostToolUse / UserPromptSubmit / SubagentStop / Notification in `.claude/settings.json`, parse imports and assert `sqlite3` is not imported. Hard CI gate (D-138-06).
- **M4.T6 — Integration test for SessionEnd rebuild.** `tests/integration/test_session_end_rebuild.py`: emit 100 NDJSON events, fire SessionEnd, assert `state.db.events` count == 100 and within 5 s wall-clock.

### Acceptance gate

- After 5 hook firings (NDJSON growth) + SessionEnd, `SELECT COUNT(*) FROM events` matches NDJSON line count minus malformed lines (sampled to 1k).
- NDJSON rotates when test threshold (`AIENG_NDJSON_MAX_LINES=100`) is breached; chain integrity (`ai-eng audit verify-chain`) holds.
- `test_no_sql_on_hot_path.py` green.

## Phase M5 — `hooks_integrity` Removal + Doctor Surface

**Anchor:** §10.2 YAGNI; CONSTITUTION.md §3 hard delete.

### Tasks

- **[x] M5.T1 — Migration `0008_drop_hooks_integrity.py`.** DROP TABLE `hooks_integrity`. Removes the dead schema declared in `0001_initial_schema.py` and the documented-but-never-honored intent in `0002_seed_from_json.py`.
- **[x] M5.T2 — Strip references.** Remove `hooks_integrity` from `audit_index.py` schema docs (if any) and the docstring in `0002_seed_from_json.py:15-17`.
- **[x] M5.T3 — `ai-eng doctor --check state-db`.** New subcommand: connects to `state.db`, lists every table with row count and `last_modified` mtime, flags expected-but-empty tables (decisions if 0 rows post-backfill, install_steps if 0 rows post-install).
- **M5.T4 — CHANGELOG entries.** `## [Unreleased] ### Removed`: `_insert_events_row` dual-write, `decision-store.json` legacy mirror, `audit-index.sqlite` legacy 0-byte file, `state.db.hooks_integrity` table.
- **M5.T5 — Update `_history.md`.** Add row for spec-138 with status `approved`.

### Acceptance gate

- `ai-eng doctor --check state-db` returns a table-status report (one row per `state.db` table).
- `0008_drop_hooks_integrity` applied cleanly on fresh DB; chain re-verification still passes.
- CHANGELOG documents all four removals.

## Cross-spec coordination

- **spec-139 dependency.** M6 of spec-139 (NDJSON throttle wrapper + state.db VACUUM) consumes the rotation wire added in this spec's M4.T4. spec-139 must not duplicate the wiring; only adds the 1-hour throttle and the `incremental_vacuum` call.
- **spec-140 dependency.** Wave 1 of spec-140 deletes dead tests; ensure spec-138's new tests (`test_sql_writer_schemas.py`, `test_no_sql_on_hot_path.py`, `test_persistence_doctrine_exists.py`) are NOT in the deletion list.
- **spec-141 dependency.** None — semgrep coverage work is fully orthogonal.

## Out of single-concern envelope

This plan is multi-phase / multi-file and does NOT satisfy the `/ai-build --no-hitl` single-concern gate. Implementation proceeds via the multi-spec autonomous orchestration captured in `runtime/session-orchestration/run-manifest.md`. The build agent is dispatched per phase; quality loop runs once at the end of the combined run.
