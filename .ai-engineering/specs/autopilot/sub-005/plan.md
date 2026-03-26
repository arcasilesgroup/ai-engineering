---
total: 7
completed: 7
---

# Plan: sub-005 Install Fixes — team/ and specs/

## Plan

exports: [GovernancePhase._classify (modified behavior for team-owned files), generic team seed templates, specs placeholder templates]
imports: [sub-003 may add project-identity.md handling to governance.py -- this sub-spec modifies a different branch of _classify and does not conflict]

- [x] T-5.1: Delete ai-engineering-specific template files from contexts/team/
  - **Files**: `src/ai_engineering/templates/.ai-engineering/contexts/team/cli.md`, `src/ai_engineering/templates/.ai-engineering/contexts/team/mcp-integrations.md`
  - **Done**: Both files deleted. Only `README.md` and `lessons.md` remain in `src/ai_engineering/templates/.ai-engineering/contexts/team/`.

- [x] T-5.2: Make lessons.md template generic (remove ai-engineering specific patterns)
  - **Files**: `src/ai_engineering/templates/.ai-engineering/contexts/team/lessons.md`
  - **Done**: File contains only the header ("## Rules & Patterns"), the purpose description paragraph, the "How to Add Lessons" section, and an empty "## Patterns" section. No ai-engineering specific lesson entries remain. File is a generic placeholder suitable for any project adopting the framework.

- [x] T-5.3: Create specs/ placeholder templates
  - **Files**: `src/ai_engineering/templates/.ai-engineering/specs/spec.md` (NEW), `src/ai_engineering/templates/.ai-engineering/specs/plan.md` (NEW)
  - **Done**: Directory `src/ai_engineering/templates/.ai-engineering/specs/` exists with two files. `spec.md` contains "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n". `plan.md` contains "# No active plan\n\nRun /ai-plan after spec approval.\n". Both are valid markdown.

- [x] T-5.4: Fix GovernancePhase._classify to deploy team seed files on INSTALL and FRESH modes
  - **Files**: `src/ai_engineering/installer/phases/governance.py`
  - **Done**: The `_classify` method handles `contexts/team/` files with mode-aware logic: (1) INSTALL mode -- if dest does not exist, return "create" with rationale "team seed file"; if dest exists, return "skip". (2) FRESH mode -- return "overwrite" with rationale "FRESH mode: overwrite framework-owned" (consistent with other framework files). (3) REPAIR/RECONFIGURE modes -- return "skip" with rationale "team-owned file" (preserve user content). The old unconditional "skip" for all team files is replaced. No changes to `_TEAM_OWNED` constant value, `_EXCLUDE_PREFIXES`, `_STATE_PREFIX`, or `_STATE_REGENERATED`.

- [x] T-5.5: Write unit tests for team seed deployment and specs directory creation
  - **Files**: `tests/unit/installer/test_phases.py`
  - **Done**: New tests in `TestGovernancePhase` class: (1) `test_plan_install_creates_team_seed_actions` -- verifies INSTALL mode produces "create" actions for `contexts/team/README.md` and `contexts/team/lessons.md`. (2) `test_plan_install_skips_team_if_exists` -- verifies INSTALL mode with existing team files produces "skip" actions. (3) `test_plan_fresh_overwrites_team_seeds` -- verifies FRESH mode produces "overwrite" actions for team files. (4) `test_plan_repair_skips_team` -- verifies REPAIR mode skips team files. (5) `test_plan_includes_specs_directory_files` -- verifies plan includes specs/spec.md and specs/plan.md as "create" actions. (6) `test_execute_creates_team_and_specs` -- verifies execute in INSTALL mode creates both team seed files and specs placeholder files on disk. All tests pass.

- [x] T-5.6: Update e2e test for team seed content and specs directory
  - **Files**: `tests/e2e/test_install_clean.py`
  - **Done**: (1) `test_install_creates_required_dirs` -- add `"specs"` to the required dirs list. (2) New test `test_install_creates_team_seed_files` -- asserts exactly 2 files exist in `contexts/team/` (README.md and lessons.md), and their content is the generic template (not ai-engineering specific). (3) New test `test_install_creates_specs_placeholders` -- asserts `specs/spec.md` and `specs/plan.md` exist with placeholder content. All tests pass.

- [x] T-5.7: Verify all tests pass (unit + e2e + integration)
  - **Files**: `tests/unit/installer/test_phases.py`, `tests/e2e/test_install_clean.py`, `tests/integration/test_phase_failure.py`
  - **Done**: `pytest tests/unit/installer/test_phases.py tests/e2e/test_install_clean.py tests/integration/test_phase_failure.py -v` passes with 0 failures. No regressions in existing tests. `ruff check` and `ty check` pass on all modified files.

### Confidence
- **Level**: high
- **Assumptions**: (1) Sub-003 modifies governance.py only to add project-identity.md handling, not to restructure `_classify` -- confirmed by reading sub-003 scope which targets template file changes and ownership in defaults.py, not `_classify` branching. (2) INSTALL mode is the correct mode for fresh directories -- confirmed by service.py auto-detection logic (line 211-216). (3) The legacy `install()` function does not need code changes because it uses `copy_template_tree()` which inherently copies all non-excluded files -- confirmed by reading service.py line 139-141 and templates.py line 215-246.
- **Unknowns**: None. All files were read, all patterns are clear, all mode behaviors are verified from source.

## Self-Report

**Status**: COMPLETE -- 7/7 tasks done
**Tests**: 35 unit+e2e passed, 3 integration passed, 0 failures, 0 regressions
**Linting**: ruff check + ruff format clean on all modified files

### Changes Made

1. **Deleted** `cli.md` and `mcp-integrations.md` from team templates (ai-engineering specific content)
2. **Rewrote** `lessons.md` template to be generic (header + instructions + empty Patterns section, no project-specific lessons)
3. **Created** `specs/spec.md` and `specs/plan.md` placeholder templates in the template tree
4. **Fixed** `GovernancePhase._classify` to handle team-owned files with mode-aware logic:
   - INSTALL: create if missing, skip if exists (seeds bootstrap the directory)
   - FRESH: overwrite (consistent with all other framework files)
   - REPAIR/RECONFIGURE: skip (preserve user content)
5. **Added 6 unit tests** covering all mode behaviors for team seeds and specs directory creation
6. **Added 2 e2e tests** for team seed content validation and specs placeholder creation
7. **Updated** existing e2e test to include `specs` in required directories list

### Design Decisions

- Used "team seed file" / "team seed already exists" as rationales (distinct from generic "new file" / "file already exists") for clear auditability in plan output
- INSTALL mode checks `dest_path.exists()` to avoid overwriting user content on re-install without FRESH flag
- FRESH mode reuses the same rationale string as other framework files ("FRESH mode: overwrite framework-owned") for consistency
- The `_TEAM_OWNED` constant, `_EXCLUDE_PREFIXES`, and `_STATE_REGENERATED` were not modified -- only the branching logic within `_classify` changed
