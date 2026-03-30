---
id: sub-002
parent: spec-090
title: "Instincts v2 Schema + Extraction"
status: planned
files: [".ai-engineering/instincts/instincts.yml", ".ai-engineering/instincts/context.md", ".ai-engineering/instincts/meta.json", "src/ai_engineering/state/instincts.py", "src/ai_engineering/state/models.py", ".ai-engineering/scripts/hooks/_lib/instincts.py", ".ai-engineering/scripts/hooks/instinct-extract.py", "src/ai_engineering/state/defaults.py"]
depends_on: []
---

# Sub-Spec 002: Instincts v2 Schema + Extraction

## Scope

Implements D-090-04 (new pattern families), D-090-05 (confidence scoring), D-090-06 (v2 schema), D-090-08 (eliminate context.md), D-090-10 (smarter extraction from same observation data).

## Exploration

### Existing Files
- `_lib/instincts.py` (hook stdlib) — 663 lines, PRIMARY implementation. Already drops skillAgentPreferences (line 7 comment: "intentionally excluded"). Key functions: `_default_instincts_document()` (line 165), `extract_instincts()` (line 558), `_detect_tool_sequences()` (line 441), `_detect_error_recoveries()` (line 452).
- `src/ai_engineering/state/instincts.py` (Pydantic) — ~520 lines, wrapper. Includes `_detect_skill_agent_preferences()` (line 458) that _lib intentionally excludes. Must align with _lib.
- `models.py` — `InstinctObservation` (line 341), `InstinctMeta` (line 356). Observation schema stays v1.
- `instincts.yml` — v1 schema: 16 toolSequences entries, empty errorRecoveries. No skillAgentPreferences key.
- `meta.json` — v1: has `pendingContextRefresh`, `lastContextGeneratedAt` (to be removed per D-090-08).
- `context.md` — "No active instincts yet." To be DELETED.
- `instinct-extract.py` — 44 lines, thin wrapper calling `extract_instincts()`. No changes needed.

### Patterns to Follow
- `_lib/instincts.py` IS the v2 design already for hook execution (stdlib-only). The Pydantic version must align.
- Confidence scoring should follow the same pattern as `evidenceCount`: stored per-entry in YAML, updated by merge logic.

### Dependencies Map
- `instinct-extract.py` → imports `extract_instincts` from `_lib.instincts`
- `instinct-observe.py` → imports `append_instinct_observation` from `_lib.instincts`
- `src/state/instincts.py` → imports from `models.py` (InstinctObservation, InstinctMeta)
- Tests: `test_lib_instincts.py` (11 tests), `test_instinct_state.py` (4 tests, 2 need v2 update)

### Risks
- Schema migration must handle existing v1 instincts.yml gracefully (don't lose data).
- Two implementations (_lib and src/state) must stay in sync or one deprecated.
- `_detect_skill_workflows()` is NEW function — needs framework-events.ndjson format validation.
