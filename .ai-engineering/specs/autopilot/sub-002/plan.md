---
total: 8
completed: 8
---

# Plan: sub-002 Instincts v2 Schema + Extraction

## Plan

exports: ["instincts.yml v2 schema", "_lib/instincts.py v2 API (extract_instincts, _detect_skill_workflows, confidence_for_count)", "updated models.py InstinctMeta (no pendingContextRefresh)"]
imports: []

- [x] T-2.1: Define v2 schema constants and default document
  - **Files**: `.ai-engineering/scripts/hooks/_lib/instincts.py`
  - **Done**: `INSTINCTS_SCHEMA_VERSION = "2.0"`. `_default_instincts_document()` returns `{corrections: [], recoveries: [], workflows: []}`. Old keys (toolSequences, errorRecoveries, skillAgentPreferences) no longer in default.

- [x] T-2.2: Add confidence scoring functions
  - **Files**: `.ai-engineering/scripts/hooks/_lib/instincts.py`
  - **Done**: `confidence_for_count(n)` returns 0.3/0.5/0.7/0.85 per D-090-05. `apply_confidence_decay(entry, active_dates)` applies -0.02/week. `prune_low_confidence(entries, threshold=0.2)` removes dead entries. All pure functions, no I/O.

- [x] T-2.3: Implement _detect_skill_workflows() extractor
  - **Files**: `.ai-engineering/scripts/hooks/_lib/instincts.py`
  - **Done**: Reads `framework-events.ndjson`, filters `kind: skill_invoked`, groups by session, counts skill→skill sequence pairs. Returns `Counter[str]` like existing detectors. Handles missing/empty ndjson gracefully.

- [x] T-2.4: Update extract_instincts() for v2 families
  - **Files**: `.ai-engineering/scripts/hooks/_lib/instincts.py`
  - **Done**: Calls `_detect_error_recoveries()` → v2 `recoveries` (with input_summary context). Calls `_detect_skill_workflows()` → v2 `workflows`. Does NOT write `corrections` (LLM-only via --review). Applies confidence scoring on merge. Handles v1→v2 migration on first run.

- [x] T-2.5: Schema migration v1→v2
  - **Files**: `.ai-engineering/scripts/hooks/_lib/instincts.py`
  - **Done**: `_migrate_v1_to_v2(document)`: converts `toolSequences` entries with evidenceCount >= 5 into `workflows` entries (with mechanical trigger/action). Discards remaining toolSequences. Removes `errorRecoveries` (empty). Removes `skillAgentPreferences`. Sets schemaVersion to "2.0".

- [x] T-2.6: Delete context.md and simplify meta.json
  - **Files**: `.ai-engineering/instincts/context.md`, `.ai-engineering/instincts/meta.json`, `.ai-engineering/scripts/hooks/_lib/instincts.py`, `src/ai_engineering/state/instincts.py`
  - **Done**: context.md deleted from repo. `_default_meta()` no longer includes `pendingContextRefresh` or `lastContextGeneratedAt`. `ensure_instinct_artifacts()` no longer creates context.md. `maybe_refresh_instinct_context()` and `_refresh_instinct_context()` removed. `_select_context_items()` removed. `instinct_context_path()` removed.

- [x] T-2.7: Align Pydantic version with _lib
  - **Files**: `src/ai_engineering/state/instincts.py`, `src/ai_engineering/state/models.py`
  - **Done**: `default_instincts_document()` matches _lib (v2 families). `extract_instincts()` drops `_detect_skill_agent_preferences()` call. `InstinctMeta` model drops `pending_context_refresh` and `last_context_generated_at` fields. Context refresh functions removed.

- [x] T-2.8: Update instinct tests for v2
  - **Files**: `tests/unit/test_lib_instincts.py`, `tests/unit/test_instinct_state.py`
  - **Done**: `test_instinct_state.py` line 135 assertion updated (no skillAgentPreferences in output). YAML seed data in test fixtures updated to v2 schema. New tests: `test_confidence_for_count`, `test_apply_confidence_decay`, `test_detect_skill_workflows`, `test_migrate_v1_to_v2`. All existing tests pass with v2 schema.

### Confidence
- **Level**: high
- **Assumptions**: framework-events.ndjson has `skill_invoked` events with `component` field containing skill name. _lib is the canonical implementation (Pydantic version aligns, not the other way around).
- **Unknowns**: Exact format of `skill_invoked` events in framework-events.ndjson (need to validate during T-2.3).

## Self-Report

**Status**: 8/8 tasks complete.

**Changes summary**:
- `_lib/instincts.py`: Migrated to v2 schema (corrections/recoveries/workflows). Added confidence scoring functions (`confidence_for_count`, `apply_confidence_decay`, `prune_low_confidence`). Added `_detect_skill_workflows()` reading framework-events.ndjson. Added `_migrate_v1_to_v2()`. Removed all context.md generation code (`_context_path`, `_default_context_text`, `_select_context_items`, `maybe_refresh_instinct_context`, `_needs_context_refresh`, `_refresh_instinct_context`, `INSTINCT_CONTEXT_HEADER`, `INSTINCT_CONTEXT_REL`). Simplified `_default_meta()` (removed `pendingContextRefresh`, `lastContextGeneratedAt`, `contextMaxAgeHours`).
- `src/ai_engineering/state/instincts.py`: Aligned with _lib v2 API. Removed `instinct_context_path`, `default_instinct_context`, `needs_context_refresh`, `refresh_instinct_context`, `maybe_refresh_instinct_context`, `_detect_skill_agent_preferences`, `_build_skill_agent_preference_entry`, `_select_context_items`. Added `_detect_skill_workflows`, `confidence_for_count`, `_migrate_v1_to_v2`, `_build_recovery_entry`, `_build_workflow_entry`.
- `src/ai_engineering/state/models.py`: `InstinctMeta` dropped `pending_context_refresh`, `last_context_generated_at`, `context_max_age_hours` fields.
- `.ai-engineering/instincts/context.md`: Deleted from repo.
- Hook callers (`telemetry-skill.py`, `copilot-skill.sh`, `copilot-skill.ps1`): Removed `maybe_refresh_instinct_context` imports and calls.
- Tests: 49 tests pass (44 in `test_lib_instincts.py`, 5 in `test_instinct_state.py`). New tests cover confidence scoring, decay, pruning, skill workflow detection, and v1-to-v2 migration.

**Validation**: `ruff check` + `ruff format --check` pass on all 5 changed Python files. 49/49 tests pass. No regressions in the broader test suite (7 pre-existing failures unrelated to sub-002).

**Risks**: Template files under `src/ai_engineering/templates/` still contain v1 instinct code. These are generated-project templates and will need a separate template sync pass (not in sub-002 scope).
