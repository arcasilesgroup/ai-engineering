---
id: spec-066
title: "Relocate scripts/hooks/ into .ai-engineering/"
status: draft
created: 2026-03-24
refs: []
---

# spec-066: Relocate scripts/hooks/ into .ai-engineering/

## Problem

`ai-eng install` deploys `scripts/hooks/` at the project root — 34 hook scripts + `_lib/` support module that pollute the user's project tree with framework internals. Every other framework artifact lives inside `.ai-engineering/`, but hooks are the exception.

```
myproject/
  .ai-engineering/        # framework home
    contexts/
    state/
    manifest.yml
  .claude/                # IDE config
  .github/                # IDE config
  scripts/                # WHY IS THIS HERE?
    hooks/                # 34+ files (telemetry, copilot, guards...)
  src/
  README.md
```

Users see `scripts/hooks/` and don't understand its purpose. It should be inside `.ai-engineering/` where all framework files belong:

```
myproject/
  .ai-engineering/
    contexts/
    scripts/
      hooks/              # moved here
    state/
    manifest.yml
  .claude/
  .github/
  src/
  README.md
```

## Solution

Move `scripts/hooks/` to `.ai-engineering/scripts/hooks/` in three places:

1. **Template source**: `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/` (stays under `project/` template root to preserve existing resolution logic in `copy_project_templates()` and `HooksPhase.execute()`)
2. **Dogfooding**: `.ai-engineering/scripts/hooks/` (live copy in this repo)
3. **Installed projects**: `ai-eng install` deploys hooks to `<target>/.ai-engineering/scripts/hooks/`

Additionally: `ai-eng update` migrates existing installations from old path to new path.

## Scope

### In Scope

**A) Move Template Source**

1. Move `src/ai_engineering/templates/project/scripts/hooks/` → `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/`
2. Remove empty `src/ai_engineering/templates/project/scripts/` directory after move.

**B) Update Installer**

3. In `templates.py`: change `_COMMON_TREE_MAPS` tuple from `("scripts/hooks", "scripts/hooks")` → `(".ai-engineering/scripts/hooks", ".ai-engineering/scripts/hooks")`. Source stays resolved from `get_project_template_root()` — no resolution logic changes needed.
4. In `phases/hooks.py` line ~98: update verification path from `context.target / "scripts/hooks"` → `context.target / ".ai-engineering" / "scripts" / "hooks"`.

**C) Update Claude Code Settings**

5. In `src/ai_engineering/templates/project/.claude/settings.json`: update all 10 hook command paths from `$CLAUDE_PROJECT_DIR/scripts/hooks/` → `$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/`.
6. In dogfooding `.claude/settings.json`: same update.

**D) Update GitHub Copilot Hooks**

7. In `src/ai_engineering/templates/project/github_templates/hooks/hooks.json` (3 entries): update script paths from `scripts/hooks/` → `.ai-engineering/scripts/hooks/`.
8. In dogfooding `.github/hooks/hooks.json` (12 entries, 6 hooks × bash+ps1): update script paths from `./scripts/hooks/` → `./.ai-engineering/scripts/hooks/`.

**E) Fix Shell Script Path Navigation**

9. Telemetry scripts using `$(dirname "$0")/../..` to find root: change to `$(dirname "$0")/../../..` (3 levels up instead of 2).
   - Affected: `telemetry-skill.sh`, `telemetry-session.sh`, `telemetry-agent.sh`
10. Copilot scripts using `PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"`: change to `$SCRIPT_DIR/../../..`.
    - Affected: `copilot-skill.sh`, `copilot-session-start.sh`, `copilot-session-end.sh`, `copilot-error.sh`, `copilot-agent.sh`
    - NOT affected (sibling-relative only, no root navigation): `copilot-observe.sh`, `copilot-auto-format.sh`, `copilot-injection-guard.sh`, `copilot-cost-tracker.sh`, `copilot-mcp-health.sh`, `copilot-instinct-extract.sh`, `copilot-telemetry-skill.sh`

**F) Fix PowerShell Script Path Navigation**

11. PowerShell scripts using `Split-Path -Parent (Split-Path -Parent $PSScriptRoot)`: add one more `Split-Path -Parent` level.
    - Affected: `telemetry-session.ps1`, `telemetry-skill.ps1` (2 scripts)
    - NOT affected: `telemetry-agent.ps1` (uses `Get-Location` fallback, not dirname navigation)

**G) Move Dogfooding Copy**

12. Move `scripts/hooks/` → `.ai-engineering/scripts/hooks/` in this repo.
13. Remove empty `scripts/` directory.

**H) Update Tests**

14. `tests/unit/test_template_parity.py` line ~15: update `_LIVE_HOOKS` path.
15. `tests/unit/test_strategic_compact.py` line ~16: update `HOOK_DIR` path.
16. `tests/integration/test_strategic_compact_integration.py` line ~15: update `HOOK_DIR` path.
17. `tests/integration/test_telemetry_canary.py` lines ~34-48, ~106: update all `scripts/hooks/` references.

**I) Update Policy Scope**

18. `src/ai_engineering/policy/test_scope.py` line ~403: update `"scripts/hooks/**"` → `".ai-engineering/scripts/hooks/**"`.

**J) Update Updater (migration for existing installations)**

19. In `src/ai_engineering/updater/service.py`: add `_migrate_hooks_dir()` function alongside existing `_migrate_legacy_dirs()`.
    - If `<target>/scripts/hooks/` exists: move contents to `<target>/.ai-engineering/scripts/hooks/`.
    - Remove empty `<target>/scripts/hooks/` and `<target>/scripts/` if empty.
    - Log the migration.
20. In `updater/service.py` lines ~203-204: update `_evaluate_project_files()` to use new tree map paths.

**K) Changelog exception**

21. Do NOT update historical `CHANGELOG.md` references to `scripts/hooks/`. These describe past state and are correct as written.

### Out of Scope

- Changes to hook script logic (only paths change, not behavior)
- Changes to what hooks are installed or their functionality
- New hooks or hook removal
- Changes to `ai-eng install` flow beyond the path update

## Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Template source stays under `project/` root at `project/.ai-engineering/scripts/hooks/` | Preserves existing `_COMMON_TREE_MAPS` resolution via `get_project_template_root()`. No changes to `copy_project_templates()`, `HooksPhase.execute()`, or updater `_evaluate_project_files()` resolution logic. The tuple changes from `("scripts/hooks", "scripts/hooks")` to `(".ai-engineering/scripts/hooks", ".ai-engineering/scripts/hooks")` — minimal and safe. |
| D2 | 3-level dirname navigation | Moving from `scripts/hooks/` (2 levels from root) to `.ai-engineering/scripts/hooks/` (3 levels). Shell scripts use `dirname` to find root — must add one level. |
| D3 | Dogfooding mirrors installed structure | This repo uses the same hooks structure as installed projects. Keeps parity for template sync checks. |
| D4 | Migration in `ai-eng update` is in-scope | Shipping without migration creates broken upgrade path: old hooks linger, new settings.json points to empty paths. Not acceptable as follow-up. |

## Acceptance Criteria

### File Relocation
- [ ] AC1: `scripts/hooks/` no longer exists at project root after install
- [ ] AC2: `.ai-engineering/scripts/hooks/` contains all 34 hook scripts + `_lib/` after install
- [ ] AC3: Template source is at `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/`
- [ ] AC4: Dogfooding copy is at `.ai-engineering/scripts/hooks/`
- [ ] AC5: `src/ai_engineering/templates/project/scripts/` directory no longer exists

### Path References
- [ ] AC6: `.claude/settings.json` references `$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/`
- [ ] AC7: `.github/hooks/hooks.json` references `./.ai-engineering/scripts/hooks/`
- [ ] AC8: Shell scripts with root navigation use 3 levels up (8 scripts)
- [ ] AC9: PowerShell scripts with root navigation use 3 levels up (2 scripts)

### Installer
- [ ] AC10: `ai-eng install` deploys hooks to `.ai-engineering/scripts/hooks/`
- [ ] AC11: `phases/hooks.py` verifies hooks at `.ai-engineering/scripts/hooks/`

### Migration
- [ ] AC12: `ai-eng update` moves `scripts/hooks/` → `.ai-engineering/scripts/hooks/` in existing installations
- [ ] AC13: Empty `scripts/` directory removed after migration
- [ ] AC14: Migration is idempotent (running twice doesn't break anything)

### Tests
- [ ] AC15: `test_template_parity.py` passes with new paths
- [ ] AC16: `test_strategic_compact.py` passes with new paths
- [ ] AC17: `test_telemetry_canary.py` passes with new paths
- [ ] AC18: All existing tests pass — zero regressions

### Functional
- [ ] AC19: Claude Code hooks fire correctly after relocation
- [ ] AC20: CHANGELOG.md historical references are NOT modified

## Files Changed

| Action | Path | Notes |
|--------|------|-------|
| move | `src/ai_engineering/templates/project/scripts/hooks/` → `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/` | Template source relocation |
| move | `scripts/hooks/` → `.ai-engineering/scripts/hooks/` | Dogfooding relocation |
| modify | `src/ai_engineering/installer/templates.py` | `_COMMON_TREE_MAPS` tuple update |
| modify | `src/ai_engineering/installer/phases/hooks.py` | Verification path |
| modify | `src/ai_engineering/updater/service.py` | Migration function + `_evaluate_project_files()` path |
| modify | `src/ai_engineering/templates/project/.claude/settings.json` | 10 hook command paths |
| modify | `.claude/settings.json` | 10 hook command paths (dogfooding) |
| modify | `src/ai_engineering/templates/project/github_templates/hooks/hooks.json` | 3 script paths |
| modify | `.github/hooks/hooks.json` | 12 script paths (dogfooding) |
| modify | 8 shell scripts | dirname navigation (2→3 levels) |
| modify | 2 PowerShell scripts | Split-Path navigation (2→3 levels) |
| modify | `tests/unit/test_template_parity.py` | Test paths |
| modify | `tests/unit/test_strategic_compact.py` | Test paths |
| modify | `tests/integration/test_strategic_compact_integration.py` | Test paths |
| modify | `tests/integration/test_telemetry_canary.py` | Test paths |
| modify | `src/ai_engineering/policy/test_scope.py` | Scope glob |

## Risks

| Risk | Mitigation |
|------|-----------|
| Shell scripts break due to wrong level count | AC8: test that `ROOT_DIR` resolves to correct project root. Template parity test catches drift. |
| Old hooks linger after update | AC12-14: migration function moves old hooks and cleans up. Idempotent. |
| Claude Code doesn't pick up new paths | AC19: functional test. `$CLAUDE_PROJECT_DIR` is absolute, path change is transparent. |
| CHANGELOG references confuse implementer | AC20: explicit "do not touch" rule for historical entries. |
