---
spec: spec-083
title: Hook Reliability -- Self-Contained Hooks + Doctor Health Check
status: approved
approval: approved
effort: medium
refs:
  - .ai-engineering/scripts/hooks/
  - src/ai_engineering/installer/phases/hooks.py
  - src/ai_engineering/doctor/phases/hooks.py
---

# Spec 083 - Hook Reliability: Self-Contained Hooks + Doctor Health Check

## Problem

Framework hooks fail in 3 independent ways, affecting both the development repo and consumer projects:

1. **Python import failures** (Claude Code): 5 of 9 Python hooks import from `ai_engineering.*`, which requires the package in `sys.path` of the Python that executes the hook. When `python3` in the hook command resolves to a different interpreter than where `ai-engineering` was installed, hooks fail with `ModuleNotFoundError: No module named 'ai_engineering'`.

2. **Shell permission failures** (Copilot on GitHub): The installer copies hooks via `shutil.copy2()` which does not preserve the executable bit reliably across platforms. Multiple `.sh` and `.py` files in templates lack `+x` (inconsistent across source and template directories). Result: `Permission denied` on Copilot hook invocations.

3. **Silent failures with no diagnostics**: `ai-eng doctor` only checks hook hash integrity and directory existence. It does not verify executable permissions, `_lib/` completeness, script existence for registered hooks, or `python3` availability. Hook failures are invisible to users.

### Affected hooks (Python import)

| Hook | Event | Imports from `ai_engineering.*` |
|------|-------|---------------------------------|
| telemetry-skill.py | UserPromptSubmit | observability (6 functions), instincts (2 functions) |
| instinct-observe.py | Pre/PostToolUse | instincts.append_instinct_observation |
| instinct-extract.py | Stop | instincts.extract_instincts, observability.emit_framework_operation |
| observe.py | PostToolUse | observability (3 functions) |
| mcp-health.py | Pre/PostToolUseFailure | observability.emit_control_outcome |
| prompt-injection-guard.py | PreToolUse | observability.emit_control_outcome |

### Working hooks (no package imports)

| Hook | Event | Uses only `_lib/` |
|------|-------|--------------------|
| auto-format.py | PostToolUse | _lib.audit |
| strategic-compact.py | PreToolUse | _lib.audit |
| copilot-adapter.py | (adapter) | no imports |

### Affected hooks (shell permissions)

All 12 `copilot-*.sh` files in `.ai-engineering/scripts/hooks/` and their template copies in `src/ai_engineering/templates/project/`.

## Goals

- Make all 9 Python hooks self-contained: zero imports from `ai_engineering.*`, only `_lib/` and stdlib
- Fix executable permissions on all `.sh` and `.py` hook scripts in templates and source
- Add comprehensive hook health check to `ai-eng doctor` with `--fix` capability
- Maintain identical NDJSON event schema -- downstream consumers (agentsview, instinct skill) must not break

## Non-Goals

- Changing the hook registration model (settings.json, copilot shell scripts)
- Migrating hooks from Python to bash/powershell
- Changing the NDJSON event schema or instincts.yml format
- Modifying the installer's copy mechanism (shutil.copy2) -- fix permissions post-copy instead
- Adding new hooks or changing hook behavior

## Chosen Direction

Inline the required functions into `_lib/` using only Python stdlib. The functions being inlined are mechanically simple (build dict, serialize JSON, append to file). The `_lib/` versions use plain dicts instead of Pydantic models and `json` stdlib instead of `yaml` for instinct persistence (with graceful YAML fallback via try/import).

## Decisions

### D-083-01: Inline observability functions to `_lib/observability.py`

Create `_lib/observability.py` (~120 lines, stdlib only) implementing:
- `build_framework_event()` -- returns a plain dict matching FrameworkEvent schema
- `append_framework_event()` -- JSON-serializes dict with `sort_keys=True` and appends line to NDJSON file
- `emit_skill_invoked()`, `emit_agent_dispatched()`, `emit_context_load()`, `emit_ide_hook_outcome()`, `emit_framework_error()`, `emit_control_outcome()`, `emit_framework_operation()`
- All emit functions return plain dicts (not Pydantic models) -- callers access fields via `entry["correlationId"]` not `entry.correlation_id`

**`emit_declared_context_loads` simplification**: The package version calls `load_manifest_config()` to iterate `config.providers.stacks` for language/framework context discovery. The `_lib/` version emits only the fixed contexts (project-identity, spec, plan, decision-store, team directory). Language/framework context_load events are omitted in the hook version. This is acceptable because: (a) hooks are telemetry, not functional gates; (b) the package version still emits the full set when called from skills; (c) the missing events are discoverable by scanning the contexts directory at analysis time.

Key differences from package version:
- Plain dicts instead of `FrameworkEvent` Pydantic model
- `json.dumps(sort_keys=True)` to match package serialization order
- `project_root.name` instead of `load_manifest_config().name` for project name
- No Pydantic validation -- hooks are producers, not consumers; schema correctness is maintained by code structure
- Identical NDJSON output format for all emitted events

### D-083-02: Inline instinct functions to `_lib/instincts.py`

Create `_lib/instincts.py` (~350 lines, stdlib + optional yaml) implementing:
- `append_instinct_observation()` -- build observation dict, prune old entries (30 days), append to NDJSON. Includes all helpers: `_derive_outcome`, `_build_observation_detail`, `_coerce_mapping`, `_coerce_text`, `_sanitize_text`, `_summarize_mapping`, `_extract_session_id`
- `extract_instincts()` -- read observations, compute tool sequence n-grams, detect error recoveries, write results. Includes: `_filter_new_observations`, `_group_by_session`, `_detect_tool_sequences`, `_detect_error_recoveries`, `_merge_counter`, load/save document helpers
- `maybe_refresh_instinct_context()` -- regenerate `instincts/context.md` from top observations

**`_detect_skill_agent_preferences` dropped**: The package version reads `framework-events.ndjson` via Pydantic `FrameworkEvent` deserialization to correlate skill invocations with agent dispatches. The `_lib/` version drops this detection entirely. Rationale: (a) it's the only function that reads back from the event stream, creating a circular dependency; (b) the package-side `extract_instincts()` via `/ai-instinct` still captures these preferences on demand; (c) tool sequences and error recoveries are the highest-value instinct patterns.

YAML handling: `try: import yaml` at module level. If unavailable:
- `extract_instincts()` writes `instincts.yml` as JSON (valid YAML superset)
- `load_instincts_document()` attempts JSON parse first, then YAML if available
- Downstream consumers (`/ai-instinct` skill) already read via the package which has PyYAML -- no breakage

Key differences from package version:
- Plain dicts instead of `InstinctObservation`/`InstinctMeta` Pydantic models
- File I/O via stdlib `json`/`open` instead of `ai_engineering.state.io`
- Secret redaction regex duplicated (5 lines) -- identical pattern
- Observation pruning uses `datetime.fromisoformat()` instead of Pydantic timestamp parsing
- No `_detect_skill_agent_preferences` -- dropped from hook-side extraction

### D-083-03: Update all 6 affected hooks to import from `_lib/`

Replace `from ai_engineering.state.*` with `from _lib.*` in all 6 hooks. Most hooks need only import line changes. Exception: `telemetry-skill.py` also needs to change `entry.correlation_id` (Pydantic attribute) to `entry["correlationId"]` (dict key) since `_lib/` emit functions return plain dicts.

### D-083-04: Fix executable permissions in templates and source

1. `git update-index --chmod=+x` on all `.sh` and `.py` files in:
   - `.ai-engineering/scripts/hooks/`
   - `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/`

2. In `src/ai_engineering/installer/phases/hooks.py`, after `copy_tree_for_mode()`, add a permission restoration step that applies `+x` to all `.sh` and `.py` files in the copied hooks directory.

### D-083-05: Add comprehensive hook health check to `ai-eng doctor`

Add 4 new checks to `src/ai_engineering/doctor/phases/hooks.py`:

| Check | Validates | Fixable | Fix action |
|-------|-----------|---------|------------|
| `hooks-executable` | All `.sh`/`.py` in scripts/hooks/ have `+x` | Yes | `chmod +x` on each |
| `hooks-lib-complete` | `_lib/` contains `audit.py`, `observability.py`, `instincts.py`, `injection_patterns.py` | No | Requires `ai-eng install` |
| `hooks-registered` | Every hook in `.claude/settings.json` points to existing script | No | Requires `ai-eng install` |
| `hooks-python` | `python3` is invocable and can import from `_lib/` | No | User must fix PATH |

Existing checks (`hooks-integrity`, `hooks-scripts`) remain unchanged.

### D-083-06: Update template `_lib/` to include new files

Template at `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/_lib/` must include `observability.py` and `instincts.py` so `ai-eng install` copies them to consumer projects.

## Functional Requirements

### Phase 1: Create `_lib/` inline modules

1. Create `_lib/observability.py` with all emit functions, stdlib only
2. Create `_lib/instincts.py` with observation/extraction functions, stdlib + optional yaml
3. Unit test both modules independently (no package imports in test)

### Phase 2: Migrate hook imports

1. Update 6 hook files to import from `_lib/` instead of `ai_engineering.*`
2. Fix `telemetry-skill.py` attribute access: `entry.correlation_id` -> `entry["correlationId"]`
3. Verify each hook runs successfully in isolation: `python3 hook.py < test_payload.json`
4. NDJSON equivalence test: run package `emit_skill_invoked()` and `_lib/` version with identical inputs, assert JSON output has same keys, types, and `sort_keys` ordering. This is the highest-risk invariant -- test as a dedicated unit test, not just manual verification

### Phase 3: Fix permissions

1. `git update-index --chmod=+x` on all hook scripts in both locations
2. Add post-copy `chmod` in installer hooks phase
3. Verify Copilot shell hooks execute after fresh `ai-eng install`

### Phase 4: Doctor health check

1. Implement 4 new checks in `doctor/phases/hooks.py`
2. Implement fix for `hooks-executable` (chmod)
3. Integration test: break each condition, verify doctor detects it

### Phase 5: Template sync

1. Copy new `_lib/` files to template directory
2. Verify `ai-eng install` on a clean project produces working hooks
3. Mirror sync for `.github/` and `.agents/` hook templates if applicable

## Data Artifacts

### New files
- `.ai-engineering/scripts/hooks/_lib/observability.py` (~120 lines)
- `.ai-engineering/scripts/hooks/_lib/instincts.py` (~350 lines)
- Same files in `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/_lib/`

### Modified files
- 6 hook `.py` files (import changes + `telemetry-skill.py` dict access fix)
- `src/ai_engineering/installer/phases/hooks.py` (post-copy chmod)
- `src/ai_engineering/doctor/phases/hooks.py` (4 new checks + fix)
- Same hook files in template directory

### Unchanged
- `src/ai_engineering/state/observability.py` -- package version stays as-is
- `src/ai_engineering/state/instincts.py` -- package version stays as-is
- NDJSON event schema -- identical output format
- `instincts.yml` format -- compatible read/write

## Success Criteria

- Zero `from ai_engineering.*` imports in any file under `.ai-engineering/scripts/hooks/`
- All `.sh` and `.py` files in hooks directories have executable bit set in git
- `ai-eng doctor` reports OK for all 6 hook checks (2 existing + 4 new)
- `ai-eng doctor --fix` restores executable permissions when broken
- Hooks produce identical NDJSON events as before (field names, types, schema version)
- Fresh `ai-eng install` on a clean project results in all hooks functional
- Copilot shell hooks execute without `Permission denied` after install
- No third-party imports in `_lib/` (stdlib only, yaml as optional graceful degradation)
