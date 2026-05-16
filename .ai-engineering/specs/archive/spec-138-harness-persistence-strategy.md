---
spec: spec-138
slug: harness-persistence-strategy
title: Harness Persistence Strategy — SSOT-PD Doctrine and Silent Dual-Write Clearance
status: approved
effort: large
branch: claude/review-spec-drafts-DX2pD
source_brief: .ai-engineering/specs/drafts/harness-persistence-strategy-brief.md
target_dispatch: /ai-build
chains_after: spec-137
mantra: "One canonical store per datum. Caches are rebuildable. No silent dual-writes."
date_approved: 2026-05-16
auto_approved: true
auto_approval_reason: operator invoked --no-hitl autonomous run for batch of 4 spec drafts; spec brief carries explicit recommendations on every open decision
summary: Declare a single-source-of-truth-per-datum doctrine (NDJSON canonical audit, SQLite lifecycle, JSON config, Markdown human truth) and execute the bug clearance + autopopulation + retention wiring needed to make state.db actually carry data while keeping the hot path SQL-free. Closes the five silent dual-write failures in `_insert_events_row`, `runtime-stop.py` zombie read of `audit-index.sqlite`, `repository.save_decisions` phantom JSON write, dead `hooks_integrity` schema, and unwired NDJSON rotation.
---

# spec-138 — Harness Persistence Strategy

> Mantra: **One canonical store per datum. Caches are rebuildable. No silent dual-writes.**

## Summary

The ai-engineering framework accumulates five persistence primitives (SQLite, NDJSON, JSON, Markdown, ephemeral runtime) but no single document declares what belongs where. The result is internal inconsistency: the same datum lives in two stores, the second store either silently drifts or is never populated, and the test suites assert against schemas that don't exist in production. Five confirmed bugs document the failure mode — `_insert_events_row` writes to a phantom schema and swallows the resulting `sqlite3.Error`; `run_hook_safe` never INSERTs into `hooks_integrity` despite the migration documenting that intent; `0003_replay_ndjson` is one-shot and never re-runs; `audit-index.sqlite` persists as a 0-byte zombie that `runtime-stop.py:474` opens, fails on, and silently moves past; `repository.save_decisions` dual-writes to a `decision-store.json` that no operator has on disk. This spec lands a single coherent doctrine — **SSOT-PD: Single Source of Truth Per Datum** — under which each piece of state has exactly one canonical writable home, with derived caches explicitly labelled, rebuildable on demand, and forbidden from masquerading as sources of truth. The doctrine respects Article-III (NDJSON stays canonical audit per CONSTITUTION.md §13.1), respects spec-135 hot-path budgets (no SQL on PreToolUse/PostToolUse), and closes the five silent failures with hard deletions and CHANGELOG entries (per CONSTITUTION.md §3 — no shims).

## Goals

1. **Doctrine declared.** `docs/persistence-doctrine.md` exists, declares the four tiers (NDJSON / SQLite / JSON / Markdown), states the SSOT-PD rule, and documents rebuild semantics for derived caches. CONSTITUTION.md amended; CLAUDE.md §0 points to the doctrine instead of the broken `state.db.decisions` query instruction.
2. **Bug clearance landed.** `_insert_events_row` deleted; `audit-index.sqlite` 0-byte zombie removed; `_LEGACY_INDEX_REL` constant deleted; `runtime-stop.py:474` reads `state.db` (the post-rebuild events cache) directly, not the legacy index; `decision-store.json` dual-write removed from `repository.save_decisions`.
3. **Autopopulation wired.** `state.db.decisions` is populated at `/ai-brainstorm` approval and via `ai-eng decision backfill`; `state.db.install_steps` is populated by the installer; `state.db.ownership_map` is populated by `ai-eng ownership import`.
4. **Events as derived cache.** `state.db.events` is repositioned as a SessionEnd-rebuilt derived cache. `ai-eng audit index --rebuild` is the only writer; the function runs within the 5-second SessionEnd budget via the existing `indexed_lines.last_offset` incremental indexing.
5. **NDJSON rotation wired.** `framework-events.ndjson` rotates automatically at the lesser of 100k lines or 50 MB at SessionEnd; chain integrity (`ai-eng audit verify-chain`) holds across rotation.
6. **`hooks_integrity` resolved (Option A).** The dead-schema `hooks_integrity` table is dropped via migration `0008_drop_hooks_integrity` (no consumer; `hooks-manifest.json` + NDJSON `integrity_violation` events are sufficient evidence).
7. **Contract tests in CI.** A new `tests/unit/state/test_sql_writer_schemas.py` parses every SQL INSERT in production code and asserts the columns match the canonical schema from `0001_initial_schema.py`. A new `tests/architecture/test_no_sql_on_hot_path.py` confirms no hot-path hook imports `sqlite3` directly.
8. **Operator-facing visibility.** `ai-eng doctor --check state-db` reports each table's row count and freshness vs expected.

## Non-Goals

- Removing `framework-events.ndjson` or the hash chain (Article-III hard rule).
- Replacing SQLite with another RDBMS (Postgres, DuckDB) — SQLite operational profile fits.
- Expanding `state.db` to absorb new concerns (session history, tool-call traces).
- Distributing state across machines — single-host single-checkout model preserved.
- Cross-IDE shared state — every IDE checkout owns its own `state.db`.
- Restructuring `.ai-engineering/state/specs/*.json` spec-lifecycle artifacts — owned by `spec_lifecycle.py`.
- Wiring `framework-events.ndjson` rotation to a separate retention surface (e.g., cron); SessionEnd is the only trigger.

## Decisions

- **D-138-01 — `hooks_integrity` disposition.** Drop the table via migration `0008_drop_hooks_integrity`. Rationale: no documented consumer exists; spec-115 G-1 envisioned it but no skill or agent reads from it today. `hooks-manifest.json` carries the sha256 truth; `framework-events.ndjson` carries the runtime violation record. Two stores already cover the surface; the third (dead) one is YAGNI debt. Resolves brief OD-1 (Option A).
- **D-138-02 — `state.db.events` rebuild cadence.** SessionEnd-only automatic rebuild plus `ai-eng audit index --rebuild` for on-demand. Rationale: scheduled mid-session rebuild would race with active emit; the incremental indexing via `indexed_lines.last_offset` makes the rebuild cheap enough to fit in the 5-second SessionEnd budget. Resolves brief OD-2.
- **D-138-03 — `decisions_fts` invalidation.** Preserve the existing FTS5 triggers tied to the `decisions` table; the spec phase confirms the trigger DDL is present and tests round-trip insert→search. Rationale: the FTS5-by-trigger pattern is SQLite-canonical and the cost is paid at write time (cold path). No replacement strategy needed. Resolves brief OD-3.
- **D-138-04 — `repository.save_decisions` legacy JSON write removal.** Hard-remove in M1 alongside the broken dual-write paths; the 12 outstanding view-model callers cited in the inline comment are surveyed during M1 task 0 and either migrated to read from `state.db.decisions` or have their reads converted to the spec markdown. Rationale: per CONSTITUTION.md §3, no shims; the JSON has no readers on any operator checkout today (file absent on disk), so removing the writer cannot regress any extant deployment. Resolves brief OD-4.
- **D-138-05 — Mirror surface payload.** Canonical doctrine prose lives in `docs/persistence-doctrine.md`; CLAUDE.md §0 + the mirror IDE files (AGENTS.md, GEMINI.md, .github/copilot-instructions.md) carry a one-paragraph pointer that names the four tiers and links to the doctrine file. Rationale: per spec-134 sub-005 mirror diet, mirrors stay lean; deep prose lives once. Resolves brief OD-5.
- **D-138-06 — Hot-path contract test severity.** Hard CI gate (not warning). Rationale: the kernel-panic root-cause in spec-135 (= spec-139 in this run) is precisely the class of regression a soft warning would silently let through. The cost of a false positive is one developer-minute of test-suite reading; the cost of a false negative is operator machine collapse. Resolves brief OD-6.
- **D-138-07 — Order alongside spec-139 NDJSON rotation.** This spec ships the rotation wiring; spec-139 M6 reduces to the throttle wrapper (`runtime-rotate-throttled.py`) plus `state.db PRAGMA incremental_vacuum`. Rationale: spec-138 is the foundation; rotation is data-layer concern; the throttle wrapper is the orchestration layer concern. Recorded in `runtime/session-orchestration/run-manifest.md`.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Caller migration for `decision-store.json` is bigger than estimated | Medium | Medium | M1 task 0 surveys before scoping M3; if scope grows, split M3 into M3a/M3b |
| SessionEnd events-rebuild exceeds 5s budget under heavy NDJSON growth | Medium | Low | Incremental indexing via `last_offset` already implemented; full rescan only on schema change; if budget breached, defer to next session |
| Hot-path contract test produces false positives on legitimate cold-path SQL access from a hot-path-named file | Low | Low | Test imports each registered hot-path hook script and statically scans for `import sqlite3`; read-only access on cold paths via different files is allowed |
| Current Claude Code session does not emit hooks (Bug 5 in brief §3.3) | Medium | High | Bug 5 is investigated as M1 task 4 (diagnostic-first); if it is a Claude Desktop CWD bug independent of this spec, file upstream and proceed with the rest |
| Custom operator forks expect `_insert_events_row` for their own dual-write | Very Low | Low | None found on GitHub; CHANGELOG documents the removal |
| `hooks_integrity` removal (D-138-01) blocks a future consumer | Low | Low | Reintroduce via migration 0009 if a real consumer is later specified — YAGNI |
| Doctrine becomes stale as new specs add new stores | Medium | Medium | `ai-eng doctor` warns when a new `.json` or `.db` file appears under `.ai-engineering/state/` with no doctrine entry |
| `state.db PRAGMA incremental_vacuum` interferes with active session | Low | Low | Vacuum runs only at SessionEnd, never mid-session (covered by spec-139 M6) |

## References

- doc: .ai-engineering/specs/drafts/harness-persistence-strategy-brief.md
- doc: CONSTITUTION.md §13.1 (Article-III audit-chain immutability)
- doc: CLAUDE.md §0 (bootstrap) and Hot-Path Discipline section
- doc: .ai-engineering/reference/principles.md §10.1 KISS, §10.2 YAGNI, §10.3 SOLID, §10.4 DRY, §10.6 SDD
- pr: arcasilesgroup/ai-engineering#514 (spec-136 + spec-137 — predecessor work on the same branch lineage)

## Open Questions

None — all six open decisions in the brief are resolved as D-138-01 through D-138-06.
