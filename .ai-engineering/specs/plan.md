# Plan: spec-083 Hook Reliability -- Self-Contained Hooks + Doctor Health Check

## Pipeline: standard
## Phases: 4
## Tasks: 16 (build: 11, verify: 3, guard: 2)

### Phase 1: Create `_lib/` inline modules + fix permissions
**Gate**: Both `_lib/` modules pass unit tests, NDJSON equivalence verified, all hook scripts have `+x` in git index

Note: Permissions (T-1.5, T-1.6) are independent of code changes (T-1.1 through T-1.4) and run in parallel.

- [x] T-1.1: Write tests for `_lib/observability.py` (agent: build, mode: test)
  - Test each emit function produces correct dict structure
  - Test `append_framework_event` writes valid JSON line with `sort_keys=True`
  - Test `build_framework_event` includes all required fields (schemaVersion, timestamp, project, engine, kind, outcome, component, correlationId)
  - Test secret redaction in `_bounded_summary`
  - NDJSON equivalence test: compare output of `_lib/` emit vs package emit with identical inputs -- assert same keys, types, sort order
  - Files: `tests/unit/test_lib_observability.py`

- [x] T-1.2: Implement `_lib/observability.py` to pass tests (agent: build, mode: code, blocked-by: T-1.1)
  - ~120 lines, stdlib only (json, os, re, datetime, uuid, pathlib)
  - Plain dicts, no Pydantic
  - `emit_declared_context_loads` simplified: fixed contexts only (project-identity, spec, plan, decision-store, team)
  - All emit functions return plain dict with `correlationId` key
  - Files: `.ai-engineering/scripts/hooks/_lib/observability.py`

- [x] T-1.3: Write tests for `_lib/instincts.py` (agent: build, mode: test)
  - Test `append_instinct_observation` writes valid NDJSON with correct schema
  - Test observation pruning removes entries older than 30 days
  - Test `extract_instincts` detects tool sequence n-grams
  - Test `extract_instincts` detects error recovery patterns
  - Test `maybe_refresh_instinct_context` generates markdown
  - Test YAML fallback: with yaml unavailable, writes JSON (valid YAML superset)
  - Verify `_detect_skill_agent_preferences` is NOT present (dropped per D-083-02)
  - Files: `tests/unit/test_lib_instincts.py`

- [x] T-1.4: Implement `_lib/instincts.py` to pass tests (agent: build, mode: code, blocked-by: T-1.3)
  - ~350 lines, stdlib + optional yaml
  - Plain dicts for observations and meta
  - All helpers inlined: `_derive_outcome`, `_build_observation_detail`, `_coerce_mapping`, `_coerce_text`, `_sanitize_text`, `_summarize_mapping`, `_extract_session_id`, `_filter_new_observations`, `_group_by_session`, `_detect_tool_sequences`, `_detect_error_recoveries`, `_merge_counter`, `_select_context_items`
  - No `_detect_skill_agent_preferences`
  - Files: `.ai-engineering/scripts/hooks/_lib/instincts.py`

- [x] T-1.5: Fix git executable permissions on all hook scripts (agent: build, parallel with T-1.1)
  - `git update-index --chmod=+x` on every `.sh` and `.py` in `.ai-engineering/scripts/hooks/` (excluding `_lib/`)
  - `git update-index --chmod=+x` on every `.sh` and `.py` in `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/` (excluding `_lib/`)
  - `_lib/*.py` files stay 100644 (they are library modules, not entry points)

- [x] T-1.6: Add post-copy chmod in installer hooks phase (agent: build, parallel with T-1.1)
  - In `src/ai_engineering/installer/phases/hooks.py`, after `copy_tree_for_mode()` call, iterate `.sh` and `.py` files and apply `stat.S_IXUSR | stat.S_IXGRP`
  - Write unit test: mock copy, verify chmod called on correct files
  - Files: `src/ai_engineering/installer/phases/hooks.py`, `tests/unit/test_installer_hooks_phase.py` (or extend existing)

- [x] T-1.7: Verify Phase 1 (agent: verify)
  - Run `ruff check` + `ty check` on new `_lib/` modules
  - Run all unit tests from T-1.1, T-1.3
  - Verify git index shows 100755 for all hook scripts
  - Verify no `from ai_engineering` imports in `_lib/observability.py` or `_lib/instincts.py`

### Phase 2: Migrate hook imports
**Gate**: All 6 hooks import from `_lib/` only, zero `ai_engineering.*` imports, hooks pass isolation test

- [x] T-2.1: Update imports in all 6 hooks + 3 copilot .sh + 5 copilot .ps1 + fix telemetry-skill.py (agent: build)
  - `telemetry-skill.py`: replace imports + change `entry.correlation_id` → `entry["correlationId"]` (lines 67, 78)
  - `instinct-observe.py`: replace `from ai_engineering.state.instincts` → `from _lib.instincts`
  - `instinct-extract.py`: replace both imports (instincts + observability)
  - `observe.py`: replace `from ai_engineering.state.observability` → `from _lib.observability`
  - `mcp-health.py`: replace `from ai_engineering.state.observability` → `from _lib.observability`
  - `prompt-injection-guard.py`: replace `from ai_engineering.state.observability` → `from _lib.observability`
  - Files: 6 hook files in `.ai-engineering/scripts/hooks/`

- [x] T-2.2: Verify zero package imports + hooks functional (agent: verify)
  - `grep -r "from ai_engineering" .ai-engineering/scripts/hooks/` returns empty
  - Run `python3 -c "import sys; sys.path.insert(0,'.ai-engineering/scripts/hooks'); from _lib.observability import emit_skill_invoked"` succeeds
  - Run each hook with test stdin payload, verify exit 0

- [x] T-2.3: Guard -- governance check on hook changes (agent: guard)
  - Verify no suppression comments added
  - Verify hook fail-open behavior preserved (all hooks exit 0 on exception)
  - Verify NDJSON schema version unchanged ("1.0")

### Phase 3: Doctor health check
**Gate**: `ai-eng doctor` reports 6 OK checks for hooks phase, `--fix` restores permissions

- [x] T-3.1: Write tests for 4 new doctor checks (agent: build, mode: test)
  - Test `hooks-executable`: detect missing +x, verify fix applies chmod
  - Test `hooks-lib-complete`: detect missing `_lib/` files
  - Test `hooks-registered`: detect broken script references in settings.json
  - Test `hooks-python`: detect missing python3
  - Files: `tests/unit/test_doctor_phases_hooks.py` (extend existing)

- [x] T-3.2: Implement 4 new checks + fix in doctor hooks phase (agent: build, mode: code, blocked-by: T-3.1)
  - `_check_hooks_executable()`: glob `.sh`/`.py`, check `os.access(X_OK)`, fixable via chmod
  - `_check_hooks_lib_complete()`: check 4 required files in `_lib/`
  - `_check_hooks_registered()`: parse `.claude/settings.json` hooks, resolve script paths
  - `_check_hooks_python()`: `subprocess.run(["python3", "-c", "import json"])` with timeout
  - Add new checks to `check()` function, add `hooks-executable` to `fix()` function
  - Files: `src/ai_engineering/doctor/phases/hooks.py`

- [x] T-3.3: Verify doctor integration (agent: verify)
  - Run `ai-eng doctor` -- all 6 hook checks pass
  - Manually break permissions on one file, run `ai-eng doctor --fix`, verify FIXED status

### Phase 4: Template sync + final verification
**Gate**: Fresh `ai-eng install` produces working hooks; all mirrors synced

- [x] T-4.1: Sync all changed files to template directory (agent: build)
  - Copy `_lib/observability.py` and `_lib/instincts.py` to `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/_lib/`
  - Copy updated 6 hook files to template
  - Verify template hook permissions match source (100755 for scripts, 100644 for `_lib/`)
  - Files: template directory under `src/ai_engineering/templates/project/`

- [x] T-4.2: Mirror sync to `.github/` and `.agents/` -- N/A, hooks only live in .ai-engineering/ (agent: build)
  - Sync updated hooks to `.github/skills/ai-*/` and `.agents/skills/*/` if they have hook copies
  - Run `scripts/sync_command_mirrors.py` if applicable
  - Note: Copilot `.sh` hooks and `.ps1` hooks reference Python hooks internally -- verify paths still resolve

- [x] T-4.3: Final governance + integration verification (agent: guard)
  - `grep -r "from ai_engineering" .ai-engineering/scripts/hooks/` returns empty (all locations)
  - `git ls-files -s .ai-engineering/scripts/hooks/*.py .ai-engineering/scripts/hooks/*.sh` shows 100755
  - Run full test suite: `pytest tests/unit/test_lib_observability.py tests/unit/test_lib_instincts.py tests/unit/test_doctor_phases_hooks.py`
  - Run `ai-eng doctor` -- all checks pass
  - Verify NDJSON output from hooks matches expected schema
