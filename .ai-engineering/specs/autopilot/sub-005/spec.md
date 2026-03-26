---
id: sub-005
parent: spec-079
title: "Install Fixes — team/ and specs/"
status: planning
files: ["src/ai_engineering/installer/phases/governance.py", "src/ai_engineering/templates/.ai-engineering/contexts/team/README.md", "src/ai_engineering/templates/.ai-engineering/contexts/team/lessons.md", "src/ai_engineering/templates/.ai-engineering/contexts/team/cli.md", "src/ai_engineering/templates/.ai-engineering/contexts/team/mcp-integrations.md", "src/ai_engineering/templates/.ai-engineering/specs/spec.md", "src/ai_engineering/templates/.ai-engineering/specs/plan.md", "tests/unit/installer/test_phases.py", "tests/e2e/test_install_clean.py"]
depends_on: ["sub-003"]
---

# Sub-Spec 005: Install Fixes — team/ and specs/

## Scope

Fix governance.py so `ai-eng install` creates `contexts/team/` (with 2 generic seed files: README.md + lessons.md) and `specs/` directory on FRESH mode. Remove cli.md and mcp-integrations.md from templates (ai-engineering specific). Create specs/ placeholder templates. Update install tests.

## Exploration

### Existing Files

**`src/ai_engineering/installer/phases/governance.py`** (144 lines)
GovernancePhase class implementing `plan()` / `execute()` / `verify()`. Copies the `.ai-engineering/` template tree excluding `agents/` and `skills/` (handled by IdeConfigPhase). Key exports: `GovernancePhase` class. Key constants: `_TEAM_OWNED = "contexts/team/"`, `_STATE_PREFIX = "state/"`, `_STATE_REGENERATED` set, `_EXCLUDE_PREFIXES` tuple.

The `_classify` static method (line 124-143) determines action per file. Current behavior: line 127-128 hard-skips ALL files under `contexts/team/` regardless of install mode. This means even INSTALL mode (the default for fresh directories) and FRESH mode never deploy team seed files via the phase pipeline. The bug: team files are always skipped, so the `contexts/team/` directory is never created by GovernancePhase.

Note: the legacy `install()` function in `service.py` does NOT use GovernancePhase -- it calls `copy_template_tree()` directly with `exclude=["agents/", "skills/"]`. That function DOES copy team files (no team-specific exclusion). So the legacy path works but the pipeline path does not.

**`src/ai_engineering/templates/.ai-engineering/contexts/team/README.md`** (1 line)
Current content: "Team-specific customizations. Add your conventions here. ai-engineering will never overwrite these files." -- already generic, suitable as seed.

**`src/ai_engineering/templates/.ai-engineering/contexts/team/lessons.md`** (32 lines)
Current content: Rules & Patterns header + instructions on how to add lessons + 2 specific lessons (plan checkboxes and /ai-pr spec cleanup). The specific lesson content is ai-engineering project-specific. Needs to be replaced with an empty placeholder retaining only the header and instructions section.

**`src/ai_engineering/templates/.ai-engineering/contexts/team/cli.md`** (59 lines)
CLI UX conventions specific to ai-engineering: dual-output routing, JSON envelope contract, color semantics, progress indicators. Entirely ai-engineering specific. DELETE from templates.

**`src/ai_engineering/templates/.ai-engineering/contexts/team/mcp-integrations.md`** (117 lines)
Approved MCP servers (Context7, Exa Search, fal.ai) with security posture and compliance classification. Entirely ai-engineering specific. DELETE from templates.

**`src/ai_engineering/templates/.ai-engineering/specs/`** -- DOES NOT EXIST
No specs directory exists in templates. This is why `ai-eng install` never creates the `specs/` directory. NEW: needs `spec.md` and `plan.md` placeholder files.

**`tests/unit/installer/test_phases.py`** (268 lines)
Unit tests for all installer phases. `TestGovernancePhase` class (lines 43-77) has 3 tests: `test_plan_install_creates_actions`, `test_execute_creates_files`, `test_verify_passes`. Tests run against real templates with a `tmp_path` target. Needs new tests for team seed creation in INSTALL/FRESH mode and specs directory creation.

**`tests/e2e/test_install_clean.py`** (157 lines)
E2E tests for fresh install using the legacy `install()` function. `test_install_creates_required_dirs` (line 34-49) already asserts `contexts/team` directory exists. This test passes because the legacy path copies team files. Needs: additional assertions for team seed file content (2 files only) and specs directory existence. May need a new test class for pipeline install if the fix is pipeline-specific.

**`tests/unit/test_installer.py`** (812 lines)
Unit tests for `installer/service.py`. Covers the legacy `install()` function with heavy mocking. Not directly relevant to GovernancePhase changes since GovernancePhase is used by `install_with_pipeline()`. However, any changes to template files will affect the legacy install path indirectly. The file is correctly excluded from the final files list -- `test_phases.py` is the right test target.

### Patterns to Follow

The exemplar is the state file handling in `_classify` (lines 130-133). State files have a similar ownership pattern: they are managed by a different phase (StatePhase) but need mode-aware behavior. The pattern:

```python
if rel.startswith(_STATE_PREFIX):
    if rel in _STATE_REGENERATED and mode is InstallMode.FRESH:
        return "skip", "regenerated by state phase in FRESH mode"
    return "skip", "state file managed by state phase"
```

For team-owned files, the analogous pattern should be:
- INSTALL mode (fresh directory): "create" -- deploy seed files to bootstrap the directory
- FRESH mode: "overwrite" -- consistent with how FRESH treats all other framework-owned files
- REPAIR/RECONFIGURE modes: "skip" -- never overwrite team content

This is a behavioral change from "always skip" to "mode-aware create/overwrite/skip". The key insight is that INSTALL mode is the default for fresh directories (service.py line 211), not FRESH. So the fix must handle INSTALL mode, not just FRESH.

For specs templates, the pattern to follow is the existing template files at the same level (e.g., `manifest.yml`, `README.md`) which are simple files in the `.ai-engineering/` template root. The specs directory will contain placeholder `.md` files that get deployed alongside them.

### Dependencies Map

**Imports by governance.py**:
- `ai_engineering.installer.templates.copy_file_if_missing` -- used in `execute()` for "create" actions
- `ai_engineering.installer.templates.get_ai_engineering_template_root` -- used in `plan()` to find template source
- `ai_engineering.installer.phases.InstallContext`, `InstallMode`, `PhasePlan`, `PhaseResult`, `PhaseVerdict`, `PlannedAction` -- phase infrastructure

**What imports GovernancePhase**:
- `src/ai_engineering/installer/service.py` -- instantiates it in `install_with_pipeline()`
- `tests/unit/installer/test_phases.py` -- test imports
- `tests/integration/test_phase_failure.py` -- pipeline integration tests

**Sub-003 dependency**: Sub-003 modifies governance.py to add `project-identity.md` seed handling. That change is in a DIFFERENT section from `_classify` -- sub-003 adds a new file to the template tree (`contexts/project-identity.md`) which `_classify` routes as a normal framework file (not under `_TEAM_OWNED` prefix). No conflict with this sub-spec's changes to the `_TEAM_OWNED` branch of `_classify`.

### Risks

1. **INSTALL vs FRESH mode ambiguity**: The parent spec says "FRESH mode" but a fresh directory actually uses INSTALL mode (auto-detection in service.py). The fix must handle both INSTALL and FRESH, otherwise brand new installations still will not get team seeds. This is the most critical design point.

2. **Legacy install() path divergence**: The legacy `install()` function in service.py does NOT use GovernancePhase. It calls `copy_template_tree()` which already copies team files. Deleting cli.md and mcp-integrations.md from templates will automatically stop them from being deployed via the legacy path too. No code change needed in the legacy path, but e2e tests that use `install()` will see the template content changes.

3. **Existing e2e test sensitivity**: `test_install_creates_required_dirs` checks `contexts/team` directory exists. After removing 2 of 4 template files, the directory still gets created (2 remaining files). No test breakage expected, but adding assertions for specific file content is important.

4. **lessons.md content change**: Replacing the current lessons.md template (which has ai-engineering specific patterns) with a generic placeholder changes what gets deployed to new projects. This is the intended behavior per the spec.
