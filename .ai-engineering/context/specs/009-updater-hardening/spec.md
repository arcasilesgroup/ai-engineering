---
spec: "009"
title: "Updater Hardening"
status: "IN_PROGRESS"
created: "2026-02-11"
branch: "feat/009-updater-hardening"
base: "334ee92"
---

# Spec 009 — Updater Hardening

## Problem

The updater service (`updater/service.py`, 231 lines) is ownership-safe but has five structural gaps:

1. **No rollback** — if an apply fails mid-operation, already-written files remain modified with no recovery mechanism. The installer is safe (create-only idempotency) but the updater overwrites, making partial failures destructive.
2. **No diff preview** — `ai-eng update` reports file counts and action markers but never shows *what changed* inside each file, forcing users to trust blindly or diff manually.
3. **`_PROJECT_TEMPLATE_TREES` ignored** — the updater only iterates `_PROJECT_TEMPLATE_MAP`. Files deployed via `_PROJECT_TEMPLATE_TREES` (`.claude/` tree: settings.json + 30+ command wrappers added in spec 008) are never updated.
4. **Ownership inconsistency** — `_is_update_allowed()` in the updater reimplements logic that `OwnershipMap.is_writable_by_framework()` already provides, with divergent `APPEND_ONLY` semantics. Additionally, `.claude/settings.json` has no ownership pattern (only `.claude/commands/**` exists), so the updater would deny it even if it were processed.
5. **Weak test assertions** — `test_denied_changes_reported` asserts `denied_count >= 0` (always true). No tests for template trees, rollback, diff generation, or create-blocked-by-deny.

## Solution

1. Consolidate ownership logic into `OwnershipMap.is_update_allowed()`, widen `.claude/commands/**` to `.claude/**`.
2. Wire `_PROJECT_TEMPLATE_TREES` into `_update_project_files()`.
3. Add backup/restore transactional wrapper around file writes in `update()`.
4. Generate unified diffs in `FileChange.diff`; add `--diff` and `--json` flags to CLI.
5. Harden test suite with concrete assertions and new edge-case tests targeting ≥90% coverage.

## Scope

### In Scope

- Ownership model consolidation (`is_update_allowed` on `OwnershipMap`, `.claude/**` pattern).
- `_PROJECT_TEMPLATE_TREES` support in updater.
- Rollback via temp backup on apply failure.
- Diff preview (`--diff` flag) and JSON output (`--json` flag) in CLI.
- Test hardening: 8 new unit tests, 2 new E2E tests.
- Refactor `update()` to separate evaluation from execution.

### Out of Scope

- Schema/version migration framework (separate spec when v0.2.0 introduces breaking changes).
- `framework_version` bump post-update (depends on migration infrastructure).
- Remote skill update flow.
- State file merging/migration.
- Installer changes (already handles `_PROJECT_TEMPLATE_TREES` correctly).

## Acceptance Criteria

1. `ai-eng update . --diff` shows unified diffs for each file with action `update`.
2. `ai-eng update . --json` emits valid JSON with all changes, actions, and diffs.
3. `.claude/settings.json` and `.claude/commands/*` are updated by `ai-eng update --apply`.
4. A simulated write failure during apply restores all previously-written files from backup.
5. `OwnershipMap.is_update_allowed()` exists, and `_is_update_allowed()` private function is removed.
6. File creation respects ownership: a `deny` pattern blocks `create` action.
7. `pytest --cov=ai_engineering.updater` reports ≥90% coverage.
8. All existing tests remain green; no regressions.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D-009-1 | `.claude/**` replaces `.claude/commands/**` in ownership defaults | Entire `.claude/` tree is framework-managed; single broad pattern covers settings.json, commands/, and future additions. |
| D-009-2 | Migrations deferred to future spec | No real migrations exist at v0.1.0; infrastructure without consumers is dead weight. |
| D-009-3 | `copy_template_tree()` not reused by updater | Create-only semantics incompatible with evaluate+overwrite; separate logic avoids contaminating installer. |
| D-009-4 | Diff truncated to 50 lines in CLI, full in `--json` | Governance files are small markdown, but truncation prevents output explosion if files grow. |
