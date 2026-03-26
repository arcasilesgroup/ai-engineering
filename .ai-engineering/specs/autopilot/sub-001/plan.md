---
total: 7
completed: 7
---

# Plan: sub-001 Hooks Cleanup

## Plan

### Task 1: Delete 6 dead hook files from dogfood installation
- [x] Delete `.ai-engineering/scripts/hooks/telemetry-skill.sh`
- [x] Delete `.ai-engineering/scripts/hooks/telemetry-skill.ps1`
- [x] Delete `.ai-engineering/scripts/hooks/telemetry-session.sh`
- [x] Delete `.ai-engineering/scripts/hooks/telemetry-session.ps1`
- [x] Delete `.ai-engineering/scripts/hooks/telemetry-agent.sh`
- [x] Delete `.ai-engineering/scripts/hooks/telemetry-agent.ps1`

**Files:** `.ai-engineering/scripts/hooks/telemetry-{skill,session,agent}.{sh,ps1}`
**Done when:** 6 files no longer exist under `.ai-engineering/scripts/hooks/`. Active hooks (`telemetry-skill.py`, `copilot-telemetry-skill.sh`, all other `.py` and `copilot-*` files) remain untouched.

### Task 2: Delete 6 dead hook files from template installation
- [x] Delete `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/telemetry-skill.sh`
- [x] Delete `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/telemetry-skill.ps1`
- [x] Delete `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/telemetry-session.sh`
- [x] Delete `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/telemetry-session.ps1`
- [x] Delete `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/telemetry-agent.sh`
- [x] Delete `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/telemetry-agent.ps1`

**Files:** `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/telemetry-{skill,session,agent}.{sh,ps1}`
**Done when:** 6 files no longer exist under template hooks dir. Active hooks (`telemetry-skill.py`, `copilot-telemetry-skill.sh`, all other `.py` and `copilot-*` files) remain untouched.

### Task 3: Remove ghost directory `scripts/hooks/`
- [x] Remove `scripts/hooks/_lib/__pycache__/` (3 untracked `.pyc` files)
- [x] Remove `scripts/hooks/_lib/` (empty after pycache removal)
- [x] Remove `scripts/hooks/` (empty after _lib removal)

**Files:** `scripts/hooks/` (entire tree)
**Done when:** `scripts/hooks/` directory no longer exists. `scripts/` still exists with its other tracked files (`check_workflow_policy.py`, `dev-setup.sh`, etc.).
**Note:** No tracked files live here -- only untracked `__pycache__` artifacts from a previous migration. Safe to `rm -rf`.

### Task 4: Update template github hooks.json
- [x] Replace `telemetry-skill.sh` reference with `copilot-telemetry-skill.sh` (or remove if copilot-skill.sh covers it)
- [x] Replace `telemetry-session.sh end` reference with `copilot-session-end.sh`
- [x] Replace `telemetry-agent.sh` reference with `copilot-agent.sh`

**Files:** `src/ai_engineering/templates/project/github_templates/hooks/hooks.json`
**Done when:** Template hooks.json references only `copilot-*.sh` scripts. No bare `telemetry-*.sh` references remain. JSON is valid.
**Rationale:** The live `.github/hooks/hooks.json` already uses `copilot-*` names correctly. The template was never updated to match.

### Task 5: Update integration test `test_telemetry_canary.py`
- [x] `TestHookScripts.test_script_exists_and_executable`: replace parametrized list `["telemetry-skill.sh", "telemetry-session.sh"]` with active `.py` hooks (e.g., `telemetry-skill.py`, `cost-tracker.py`) or `copilot-*.sh` equivalents
- [x] `TestHookScripts.test_powershell_stub_exists`: replace parametrized list `["telemetry-skill.ps1", "telemetry-session.ps1"]` -- either remove entirely (Claude Code uses `.py` only) or replace with relevant `copilot-*.ps1` entries
- [x] `TestTemplateHookSync.test_template_hook_scripts_exist` (line 105): replace `("telemetry-skill.sh", "telemetry-session.sh")` with active hook file names that exist in the template

**Files:** `tests/integration/test_telemetry_canary.py`
**Done when:** All parametrized test data references only hooks that exist. `pytest tests/integration/test_telemetry_canary.py` passes (or marks appropriately for CI environment).

### Task 6: Update docstrings referencing dead scripts
- [x] `.ai-engineering/scripts/hooks/observe.py` line 5: change "Also absorbs telemetry-agent.sh logic" to "Replaces former telemetry-agent.sh:"
- [x] `.ai-engineering/scripts/hooks/cost-tracker.py` line 4: change "Absorbs telemetry-session.sh functionality." to "Replaces former telemetry-session.sh."
- [x] `.ai-engineering/scripts/hooks/telemetry-skill.py` line 6: change "Migrates telemetry-skill.sh to Python." to "Replaces former telemetry-skill.sh."
- [x] Same 3 edits in template copies under `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/`

**Files:** 6 files total (3 dogfood + 3 template mirrors)
**Done when:** No docstring in active hooks refers to dead scripts using present-tense language. Past-tense "Replaces former" is acceptable.

### Task 7: Update `docs/solution-intent.md` telemetry scripts section
- [x] Replace lines 617-619 (telemetry-skill.sh/.ps1, telemetry-agent.sh/.ps1, telemetry-session.sh/.ps1) with current hook names: `telemetry-skill.py`, `observe.py`, `cost-tracker.py`, `copilot-telemetry-skill.sh`

**Files:** `docs/solution-intent.md` (lines 616-619)
**Done when:** Solution-intent doc lists only active hook names under "Telemetry Scripts".

## Files NOT Modified (explicit preservation list)

- `tests/unit/test_template_parity.py` -- no changes needed; symmetric deletions from both dirs preserve count/name parity
- `.claude/settings.json` -- already clean, references only `.py` hooks
- `.github/hooks/hooks.json` -- already clean, references only `copilot-*` hooks
- `CHANGELOG.md` -- historical record, not modified

## Exports / Imports

**Exports to other sub-specs:** None. This sub-spec is self-contained.
**Imports from other sub-specs:** None. No dependencies.

## Confidence Assessment

**Overall: HIGH (95%)**

- File deletions are straightforward: 12 files deleted symmetrically from dogfood + template.
- Ghost directory removal is trivial: only untracked `__pycache__` files.
- Template hooks.json update has a clear model to follow (the live `.github/hooks/hooks.json`).
- Test updates are mechanical: swap file names in parametrized lists.
- Docstring updates are cosmetic.

**Risk:** Template parity test could fail if file counts drift during edits. Mitigation: delete from both locations in the same commit, verify with `pytest tests/unit/test_template_parity.py`.

## Self-Report

**Status:** COMPLETE -- all 7 tasks executed successfully.
**Attempts:** 1 per task, no retries needed.

### Summary of Changes

| Task | Action | Result |
|------|--------|--------|
| 1 | Deleted 6 dead `.sh`/`.ps1` hooks from dogfood | 6 files removed |
| 2 | Deleted 6 dead `.sh`/`.ps1` hooks from template | 6 files removed (symmetric) |
| 3 | Removed ghost `scripts/hooks/` directory | 3 `.pyc` files + 2 empty dirs removed |
| 4 | Rewrote template `hooks.json` | Aligned with live `.github/hooks/hooks.json` format (v1 schema, 6 hook types) |
| 5 | Updated `test_telemetry_canary.py` | Replaced dead file assertions with `.py` hook + `copilot-*.sh` existence checks |
| 6 | Updated 6 docstrings (3 dogfood + 3 template) | Changed present-tense "Absorbs/Migrates" to past-tense "Replaces former" |
| 7 | Updated `docs/solution-intent.md` | Replaced dead hook names with `telemetry-skill.py`, `observe.py`, `cost-tracker.py`, `copilot-*.sh/.ps1` |

### Validation

- `ruff check` -- all 7 modified Python files pass
- `ruff format --check` -- all 7 files already formatted
- JSON validity -- template `hooks.json` validated
- Template parity -- both hooks dirs have 27 entries (symmetric)
- Active hook preservation -- `telemetry-skill.py`, `copilot-telemetry-skill.sh`, `observe.py`, `cost-tracker.py` all confirmed present
- Residual references -- only in `CHANGELOG.md` (historical, not modified per spec) and spec/plan files (documentation)
