---
total: 7
completed: 7
---

# Plan: sub-002 Eliminate contexts/orgs

## Plan

### Task 1: Delete template directory
- [x] Remove `src/ai_engineering/templates/.ai-engineering/contexts/orgs/` (directory + README.md)
- **Files**: `src/ai_engineering/templates/.ai-engineering/contexts/orgs/README.md`
- **Done**: Directory no longer exists. `git status` shows deletion.

### Task 2: Delete dogfood directory
- [x] Remove `.ai-engineering/contexts/orgs/` (directory + README.md)
- **Files**: `.ai-engineering/contexts/orgs/README.md`
- **Done**: Directory no longer exists. `git status` shows deletion.

### Task 3: Remove ownership rule from defaults.py
- [x] Delete line 70 from `src/ai_engineering/state/defaults.py`: the `(".ai-engineering/contexts/orgs/**", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY)` tuple
- **Files**: `src/ai_engineering/state/defaults.py`
- **Done**: `_DEFAULT_OWNERSHIP_PATHS` list no longer contains any entry with `contexts/orgs`. Count of entries decreases by 1.

### Task 4: Remove orgs test from test_state.py
- [x] Delete the `test_contexts_orgs_denied` method (lines 151-154) from `tests/unit/test_state.py`
- **Files**: `tests/unit/test_state.py`
- **Done**: No test references `contexts/orgs`. All remaining tests pass (`pytest tests/unit/test_state.py`).

### Task 5: Update README.md directory trees
- [x] Remove `orgs/` line from the directory tree in `.ai-engineering/README.md` (line 97) and update the `contexts/` description from "Language, framework, org, team conventions" to "Language, framework, team conventions" (line 94)
- [x] Remove `orgs/` line from the directory tree in `src/ai_engineering/templates/.ai-engineering/README.md` (line 97) and update the same description
- **Files**: `.ai-engineering/README.md`, `src/ai_engineering/templates/.ai-engineering/README.md`
- **Done**: Neither README contains the string `orgs/`. The `contexts/` comment no longer mentions "org".

### Task 6: Remove orgs entry from live ownership-map.json
- [x] Delete the `contexts/orgs/**` entry (lines 38-42) from `.ai-engineering/state/ownership-map.json`
- **Files**: `.ai-engineering/state/ownership-map.json`
- **Done**: File parses as valid JSON. No entry with pattern `contexts/orgs` exists.

### Task 7: Add decision DEC-026 to decision-store.json
- [x] Append a new decision entry to `.ai-engineering/state/decision-store.json` with:
  - `id`: "DEC-026"
  - `title`: "contexts/orgs eliminated -- aspirational stub with no implementation"
  - `category`: "architecture"
  - `status`: "active"
  - `criticality`: "low"
  - `source`: "spec-079"
  - `spec`: "079"
  - `decision`: "contexts/orgs eliminated -- aspirational stub with no implementation. The directory promised 'Auto-detected from git remote' organization conventions but zero skills, agents, or CLI commands ever referenced it. Use contexts/team/ for team-wide conventions."
  - `context`: "architecture"
  - `acknowledged_by`: "plan"
- **Files**: `.ai-engineering/state/decision-store.json`
- **Done**: `jq '.decisions[-1].id' decision-store.json` returns "DEC-026". File parses as valid JSON.

## Verification

After all tasks:
1. `grep -r "contexts/orgs" . --include="*.py" --include="*.json" --include="*.md"` returns only spec-079 references (spec.md, plan.md, manifest.md, decision-store DEC-026).
2. `pytest tests/unit/test_state.py` passes with zero failures.
3. `ruff check src/ai_engineering/state/defaults.py` reports zero errors.

## Exports / Imports

- **Imports**: None (sub-002 has no dependencies)
- **Exports**: None (no other sub-spec depends on sub-002 outputs)

## Confidence

**HIGH** -- This is a pure deletion task with no behavioral dependencies. Every touchpoint is fully enumerated and the change is mechanically verifiable. The only risk is a stale reference somewhere not caught by grep; the codebase-wide search above confirmed there are none outside of spec-079 artifacts.

## Self-Report

**Status**: COMPLETE (7/7 tasks)
**Attempts**: 1 (all tasks succeeded on first pass)

### Changes Made
1. **Deleted** `src/ai_engineering/templates/.ai-engineering/contexts/orgs/` (template directory + README.md)
2. **Deleted** `.ai-engineering/contexts/orgs/` (dogfood directory + README.md)
3. **Removed** `contexts/orgs/**` ownership rule from `src/ai_engineering/state/defaults.py` (line 70)
4. **Removed** `test_contexts_orgs_denied` test method from `tests/unit/test_state.py` (lines 151-154)
5. **Updated** both README.md files: removed `orgs/` from directory tree, changed `contexts/` description from "Language, framework, org, team conventions" to "Language, framework, team conventions"
6. **Removed** `contexts/orgs/**` entry from `.ai-engineering/state/ownership-map.json` (lines 38-42)
7. **Added** DEC-026 to `.ai-engineering/state/decision-store.json`

### Validation Results
- `ruff check`: All checks passed (0 errors on defaults.py and test_state.py)
- `ownership-map.json`: Valid JSON, no `contexts/orgs` entry
- `decision-store.json`: Valid JSON, last ID = DEC-026
- `grep contexts/orgs`: All hits are exclusively in spec-079 artifacts and DEC-026 -- zero hits in production code, tests, or operational config
