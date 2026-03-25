---
id: spec-070
title: "Update Command Parity with Install"
status: draft
created: 2026-03-25
refs: []
---

# spec-070: Update Command Parity with Install

## Problem

`ai-eng update` cannot update 73 out of 273 files it evaluates. The ownership map has only 14 rules, so any file without a matching pattern defaults to `is_update_allowed() → False` → `skip-denied`. Meanwhile, `install` creates all these files without issue because it uses create-only semantics (no ownership check).

This means after install, running update cannot maintain the majority of governance files it deployed.

### Evidence

Running `ai-eng update` on a freshly-installed project (`testingapp`) produces:
- **200 applied** (skip-unchanged + create for files with ownership rules)
- **73 denied** (files without ownership rules or with missing coverage)

### Root Causes

1. **Incomplete ownership map**: 9+ file categories have no ownership rule → default deny
2. **VCS templates never evaluated**: `_evaluate_project_files` calls `resolve_template_maps(None)` without `vcs_provider` → `vcs_tree_list` is always `[]`
3. **VCS provider data lost after migration**: `_migrate_install_manifest()` deletes `install-manifest.json` after migrating to `install-state.json`, but `InstallState` has no `vcs_provider` field — the data is permanently lost
4. **Hooks not updatable**: Hook scripts are deployed via `_COMMON_TREE_MAPS` but have no ownership rule → denied
5. **Misleading UX**: `skip-unchanged` and `skip-denied` both render as `✗ FAIL` (line 520: `"ok" if action in ("create", "update") else "fail"`)

## Solution

Expand the ownership map to cover all framework-managed file categories, preserve VCS provider info through state migration, wire it into update, and fix status reporting.

## Scope

### In Scope

1. Add missing ownership rules to `_DEFAULT_OWNERSHIP_PATHS` in `state/defaults.py`:
   - `.ai-engineering/README.md` → framework-managed, allow
   - `.ai-engineering/manifest.yml` → team-managed, deny (user customizes this)
   - `.ai-engineering/runbooks/**` → framework-managed, allow
   - `.ai-engineering/scripts/hooks/**` → framework-managed, allow
   - `.ai-engineering/contexts/orgs/**` → team-managed, deny
   - `.ai-engineering/contexts/product/**` → team-managed, deny
   - `.gitleaks.toml` → framework-managed, allow
   - `.semgrep.yml` → framework-managed, allow
   - `.github/instructions/**` → framework-managed, allow
   - `.github/CODEOWNERS` → team-managed, deny (teams customize this)
   - `.github/dependabot.yml` → team-managed, deny (teams customize this)
   - `.github/pull_request_template.md` → team-managed, deny (teams customize this)
   - `.github/ISSUE_TEMPLATE/**` → framework-managed, allow
   - `.github/hooks/**` → framework-managed, allow
   - `.claude/settings.json` → team-managed, deny (users add allow rules)

2. Preserve VCS provider through state migration:
   - Add `vcs_provider: str | None` and `ai_providers: list[str] | None` fields to `InstallState` model
   - Update `InstallState.from_legacy_dict()` to extract `providers.primary` and `ai_providers.enabled` from the legacy manifest
   - For projects where migration already ran (no manifest, no fields in state): fallback to `None`

3. Wire VCS provider into update:
   - Read `install-state.json` (or legacy `install-manifest.json`) in `update()` to get the active `vcs_provider`
   - Pass it to `resolve_template_maps()` in `_evaluate_project_files()`
   - Fallback to `None` if neither source has VCS info (no regression)

4. Fix status reporting in `core.py` `update_cmd`:
   - `create` / `update` → `ok` status (✓)
   - `skip-unchanged` → `info` status (neutral, file is current)
   - `skip-denied` → `fail` status (ownership denial)

5. Auto-merge missing default ownership rules:
   - Before evaluation, compare loaded ownership map patterns against defaults
   - Insert missing rules at the START of the list (before user rules) so user-added broad patterns still take precedence via first-match-wins
   - Never remove or modify existing rules
   - If new rules were added and `--apply` is set, persist the updated ownership map

### Out of Scope

- Changing install pipeline phases or install flow
- Adding new files or templates
- Changing the ownership model semantics (allow/deny/append-only)
- Refactoring the updater into a multi-phase pipeline
- Reading manifest to filter providers (update evaluates all providers — this is acceptable)
- Fixing `.claude/settings.json` merge strategy (separate spec if needed — this spec only adds the deny rule to prevent silent overwrites)

## Acceptance Criteria

- [ ] AC1: `ai-eng update` on a freshly-installed project reports 0 skip-denied for framework-managed categories (runbooks, hooks, instructions, security configs, issue templates)
- [ ] AC2: `skip-unchanged` files are displayed with neutral/info status (not `✗ FAIL`)
- [ ] AC3: Team-managed files (contexts/team/**, contexts/orgs/**, contexts/product/**, manifest.yml, CODEOWNERS, dependabot.yml, PR template, settings.json) are correctly denied with explicit deny rules
- [ ] AC4: VCS templates (`.github/ISSUE_TEMPLATE/**`, `.github/hooks/**`) are evaluated and updatable when VCS provider is configured
- [ ] AC5: Running `update` on a project with an old ownership map auto-merges missing default rules (inserted before existing rules)
- [ ] AC6: All existing tests pass (zero regressions)
- [ ] AC7: `InstallState` model has `vcs_provider` field; `from_legacy_dict()` preserves it from legacy manifest
- [ ] AC8: Projects where state migration already ran (no VCS info) gracefully fallback to `None` — no error, no regression

## Assumptions

- ASSUMPTION: `manifest.yml` is user-customized after install and should be team-managed (deny updates)
- ASSUMPTION: `contexts/orgs/` and `contexts/product/` are team-customized and should be denied
- ASSUMPTION: `CODEOWNERS`, `dependabot.yml`, and PR template are team-customized and should be denied
- ASSUMPTION: `.claude/settings.json` is user-customized (deny rules, allow rules) and should be denied to prevent silent overwrites
- ASSUMPTION: `.github/ISSUE_TEMPLATE/**` are framework-managed boilerplate and can be updated
- ASSUMPTION: Inserting new default rules at the START of the ownership list preserves first-match-wins semantics correctly

## Risks

| Risk | Mitigation |
|------|-----------|
| Existing projects have customized `.gitleaks.toml` or `.semgrep.yml` | These become updatable but update is dry-run by default — user reviews before `--apply` |
| Old ownership maps get auto-merged rules they didn't expect | Merge is additive only. Dry-run shows everything. Rules inserted at start so user overrides still win |
| VCS provider not available (legacy install, migration already ran) | Fallback to `None` — current behavior preserved, no regression |
| `.claude/settings.json` deny rule blocks framework updates to deny list | Accepted. Users should not lose their custom allow rules. Framework deny rule changes require manual merge or a future settings-merge spec |
| User-added broad pattern (e.g., `.ai-engineering/**` deny) shadows new specific rules | Rules inserted before user rules. First-match-wins means framework defaults match first. User can re-order if needed |

## Dependencies

- None. Pure enhancement to existing updater and ownership defaults.
