---
total: 5
completed: 5
confidence: 90
---

# Plan: sub-002 Unified Stack Detection

## Plan

### [x] T-2.1 Expand schema stacks enum and update manifest model

Align the `providers.stacks` enum in the JSON schema with autodetect.py vocabulary. Add missing languages detected by autodetect.py (javascript, java, csharp, go, php, ruby, kotlin, swift, dart, elixir). Keep existing framework/platform entries for backward compatibility. No breaking schema change -- single flat array remains.

- Files:
  - `.ai-engineering/schemas/manifest.schema.json` -- expand `providers.stacks.items.enum` to include all autodetect values
- Done: schema enum includes all 13 autodetect languages + existing framework/platform entries, no duplicates, `ai-eng validate` passes

### [x] T-2.2 Replace file-based stack detection in ai-build agent

Replace "Detect Stack" section (section 1) in ai-build with "Read Stacks from Manifest": instruction to read `manifest.yml providers.stacks` instead of scanning project files. Keep "Load Contexts" section (section 2) unchanged since it already maps stacks to context files. Propagate identical change to all 5 IDE mirrors and 3 template mirrors.

- Files:
  - `.claude/agents/ai-build.md` -- rewrite section "1. Detect Stack"
  - `.github/agents/build.agent.md` -- mirror
  - `.agents/agents/ai-build.md` -- mirror
  - `src/ai_engineering/templates/project/.claude/agents/ai-build.md` -- template mirror
  - `src/ai_engineering/templates/project/.github/agents/build.agent.md` -- template mirror (note: different filename convention)
  - `src/ai_engineering/templates/project/.agents/agents/ai-build.md` -- template mirror
- Done: all 6 files have identical "Read Stacks from Manifest" section replacing file-based heuristics; `ai-eng validate` passes

### [x] T-2.3 Replace file-based stack detection in ai-security, ai-pipeline, and ai-review

Replace file-based detection instructions in 4 primary skill files with manifest reads. For ai-review, add a "Step 0: Read manifest stacks" before existing Step 1 (diff-scoped detection stays as a supplementary input). Propagate to all IDE and template mirrors.

- Files:
  - `.claude/skills/ai-security/SKILL.md` -- replace "Detect stacks" in static mode step 1
  - `.claude/skills/ai-pipeline/SKILL.md` -- replace "Stack detection" in Integration section
  - `.claude/skills/ai-pipeline/handlers/generate.md` -- replace step 1 detection
  - `.claude/skills/ai-review/handlers/review.md` -- add Step 0 manifest read before Step 1
  - `.github/skills/ai-security/SKILL.md` -- mirror
  - `.github/skills/ai-pipeline/SKILL.md` -- mirror
  - `.github/skills/ai-pipeline/handlers/generate.md` -- mirror
  - `.agents/skills/security/SKILL.md` -- mirror
  - `.agents/skills/pipeline/SKILL.md` -- mirror
  - `.agents/skills/pipeline/handlers/generate.md` -- mirror
  - `src/ai_engineering/templates/project/.claude/skills/ai-security/SKILL.md` -- template
  - `src/ai_engineering/templates/project/.claude/skills/ai-pipeline/SKILL.md` -- template
  - `src/ai_engineering/templates/project/.claude/skills/ai-pipeline/handlers/generate.md` -- template
  - `src/ai_engineering/templates/project/.claude/skills/ai-review/handlers/review.md` -- template
  - `src/ai_engineering/templates/project/.github/skills/ai-security/SKILL.md` -- template
  - `src/ai_engineering/templates/project/.github/skills/ai-pipeline/SKILL.md` -- template
  - `src/ai_engineering/templates/project/.github/skills/ai-pipeline/handlers/generate.md` -- template
  - `src/ai_engineering/templates/project/.agents/skills/security/SKILL.md` -- template
  - `src/ai_engineering/templates/project/.agents/skills/pipeline/SKILL.md` -- template
  - `src/ai_engineering/templates/project/.agents/skills/pipeline/handlers/generate.md` -- template
- Done: all 20 files reference manifest as source of truth; no file-based heuristics in skill instructions; `ai-eng validate` passes

### [x] T-2.4 Add stack-drift check to doctor detect phase

Add a `_check_stack_drift()` function to `doctor/phases/detect.py` that compares `manifest_config.providers.stacks` against `autodetect.detect_stacks(target)`. Emit WARN when manifest stacks do not match detected stacks (extra or missing). The fix function is non-fixable (warn only -- user must decide whether to update manifest or add marker files). Update test file with new `TestStackDrift` class covering: match (OK), extra in manifest (WARN), missing from manifest (WARN), empty manifest (WARN), no manifest config (graceful skip).

- Files:
  - `src/ai_engineering/doctor/phases/detect.py` -- add `_check_stack_drift()` and wire into `check()`
  - `tests/unit/test_doctor_phases_detect.py` -- add `TestStackDrift` class (min 5 test cases)
- Done: `pytest tests/unit/test_doctor_phases_detect.py` passes; `check()` returns 4 results instead of 3; drift is reported as WARN with descriptive message showing extra/missing stacks

### [x] T-2.5 Update test parity and validate integrity

Update `test_doctor_phase_parity.py` if it asserts a fixed count of detect-phase checks (was 3, now 4). Run full validation suite: `ai-eng validate`, `ruff check`, `ruff format --check`.

- Files:
  - `tests/unit/test_doctor_phase_parity.py` -- update detect phase expected check count if hardcoded
  - `tests/unit/test_doctor_phases_detect.py` -- update `TestCheckReturnsAllResults` class (line 241-250) to expect 4 results and include `stack-drift` in names set
- Done: `pytest tests/unit/` passes; `ai-eng validate` passes; `ruff check` clean; `ruff format --check` clean

## Confidence Assessment

- **90% confidence**: all changes are well-scoped text replacements in markdown files (tasks 2-3) and a straightforward addition of one check function following established patterns (task 4). The only risk is mirror count -- missing a template mirror would cause `ai-eng validate` to flag sync drift, which is self-correcting.
- **Risk**: the `TestCheckReturnsAllResults` class hardcodes `len(results) == 3` and the names set -- must be updated in T-2.5 or tests will fail.
- **Schema risk (low)**: expanding the enum is additive and backward-compatible. Existing manifests with `[python]` remain valid.

## Self-Report

**Status**: PASS -- all 5 tasks complete, all tests green, linters clean.

### T-2.1 Results
- Expanded `providers.stacks` enum in `manifest.schema.json` from 19 to 29 values
- Added 10 autodetect languages: javascript, java, csharp, go, php, ruby, kotlin, swift, dart, elixir
- Backward compatible -- existing manifests remain valid

### T-2.2 Results
- Replaced "1. Detect Stack" with "1. Read Stacks from Manifest" in 5 ai-build files
- Files: `.claude/agents/ai-build.md`, `.github/agents/build.agent.md`, `.agents/agents/ai-build.md`, 2 template mirrors
- Note: `src/.../templates/project/.github/agents/build.agent.md` does not exist (5 files, not 6)

### T-2.3 Results
- ai-security: replaced "Detect stacks" with "Read stacks" in static mode step 1 across 6 files (3 IDE + 3 template)
- ai-security: replaced "Detect lock files" with "Identify lock files" in deps mode step 1 across 6 files
- ai-pipeline SKILL.md: replaced file-based stack detection in Integration section across 6 files
- ai-pipeline handlers/generate.md: replaced file-based detection in step 1 across 6 files
- ai-review handlers/review.md: added Step 0 manifest read before Step 1 in 2 files (primary + template)
- Total: 26 file modifications across all mirrors

### T-2.4 Results
- Added `_check_stack_drift()` to `doctor/phases/detect.py`
- Imports `detect_stacks` from `autodetect.py` for file-system comparison
- Compares manifest stacks vs detected stacks, reports extra/missing as WARN
- Added `TestStackDrift` class with 5 test cases: match(OK), extra(WARN), missing(WARN), empty(WARN), no-config(WARN)

### T-2.5 Results
- Updated `TestCheckReturnsAllResults`: 3->4 results, added "stack-drift" to expected names set
- `test_doctor_phase_parity.py` uses structural checks (not fixed counts) -- no changes needed
- All 24 detect tests pass, all 6 parity tests pass
- `ruff check` clean, `ruff format --check` clean

### Verification
- `pytest tests/unit/test_doctor_phases_detect.py`: 24/24 passed
- `pytest tests/unit/test_doctor_phase_parity.py`: 6/6 passed
- `ruff check`: all checks passed
- `ruff format --check`: 2 files already formatted
- Mirror verification script: 25/25 files correct, 0 failures
