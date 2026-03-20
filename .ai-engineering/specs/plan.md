# Plan: spec-059 CI/CD Standards-Driven Pipeline Generation

## Pipeline: standard
## Phases: 6
## Tasks: 18 (build: 14, verify: 4)

---

### Phase 1: Delete leaf modules
**Gate**: All deleted files gone. No remaining imports reference them (verify with grep).

- T-1.1: Delete `src/ai_engineering/pipeline/` directory (compliance.py, injector.py, __init__.py) (agent: build)
- T-1.2: Delete `src/ai_engineering/installer/cicd.py` (agent: build)
- T-1.3: Delete `src/ai_engineering/templates/pipeline/` directory (all 12 files) (agent: build)
- T-1.4: Delete `tests/unit/test_pipeline_compliance.py` and `tests/unit/test_cicd_sonar.py` (agent: build)

### Phase 2: Remove CLI consumers of deleted modules
**Gate**: `ai-eng --help` runs without import errors. `cicd` subcommand no longer listed.

- T-2.1: Delete `src/ai_engineering/cli_commands/cicd.py`. Remove cicd import + `cicd_app` registration block + command list entry from `cli_factory.py` (lines 23, 129, 304-310) (agent: build)
- T-2.2: Clean `cli_commands/maintenance.py` — remove pipeline imports (lines 36-37), delete `maintenance_pipeline_compliance()` function (lines 244-275), remove compliance step from `maintenance_all()` (lines 359, 365, 379, 399-400), adjust step count 5→4 (agent: build)
- T-2.3: Clean `cli_commands/vcs.py` — remove `no_cicd` parameter (lines 83-86), delete `if not no_cicd:` block (lines 128-137), remove `cicd_regenerated` from JSON output (line 145) and human output (lines 150-151) (agent: build)

### Phase 3: Clean installer and state layer
**Gate**: `from ai_engineering.installer.service import install` succeeds. `InstallManifest` no longer has `.cicd` field.

- T-3.1: Clean `installer/service.py` — remove `generate_pipelines` import (line 37), `SonarCicdConfig` import (line 31), delete `_resolve_sonar_cicd_config()` (lines 317-336), delete `_create_sonar_properties_if_needed()` (lines 339-374), delete `_configure_sonarlint_if_possible()` (lines 377-394), delete Phase 4 block (lines 267-285), simplify readiness condition that reads `manifest.cicd.generated` (line 306) (agent: build)
- T-3.2: Clean `state/models.py` — delete `SonarCicdConfig` class (lines 199-214), delete `CicdStatus` class (lines 217-223), remove `cicd: CicdStatus` field from `InstallManifest` (line 286) (agent: build)
- T-3.3: Clean `detector/readiness.py` — remove or replace `manifest.cicd.generated` tool check (line 314) (agent: build)
- T-3.4: Clean `policy/test_scope.py` — delete `ScopeRule(name="pipeline", ...)` block (lines 257-264) (agent: build)

### Phase 4: Add cicd section to manifest + install flow
**Gate**: `manifest.yml` has `cicd:` section. `ai-eng install` writes `standards_url` to manifest.yml.

- T-4.1: Add `cicd:` section to `.ai-engineering/manifest.yml` (live) and `src/ai_engineering/templates/.ai-engineering/manifest.yml` (template). Schema: `cicd:\n  standards_url: null` (agent: build)
- T-4.2: Modify `cli_commands/core.py` — change `_prompt_external_cicd_docs()` flow (line 77 area) to write `standards_url` into `manifest.yml` `cicd:` section instead of `ext_refs` dict for `install-manifest.json` (agent: build)

### Phase 5: Update skill mirrors and tests
**Gate**: All `/ai-pipeline` skill files reference `cicd.standards_url` from `manifest.yml`. All tests pass.

- T-5.1: Update `/ai-pipeline` handlers — `generate.md` reads `cicd.standards_url` from `manifest.yml`; `validate.md` removes `generate_pipelines` reference. Apply to all 4 handler paths: `.claude/skills/`, `.agents/skills/`, and both template mirrors (agent: build)
- T-5.2: Update `/ai-pipeline` SKILL.md files — update config source references. Apply to all 3 main mirrors + 3 template mirrors + `ai-pipeline.prompt.md` (2 files) (agent: build)
- T-5.3: Update test files — clean `test_installer.py` (remove pipeline generation assertions), `test_state.py` (remove SonarCicdConfig/CicdStatus tests), `test_readiness.py` (remove `manifest.cicd.generated` mock), `test_readiness_integration.py` (remove `manifest.cicd.generated` setup), `test_install_operational_flows.py` (remove pipeline assertions), `test_cli_command_modules.py` (remove cicd command tests + generate_pipelines mocks) (agent: build)
- T-5.4: Update docs — cli-reference.md (remove `cicd regenerate`, `maintenance pipeline-compliance`), product-contract.md template (remove pipeline generation references) (agent: build)

### Phase 6: Verification
**Gate**: All tests green. No dead imports. Linter clean.

- T-6.1: Run `ruff check` — verify no dead imports referencing deleted modules (agent: verify)
- T-6.2: Run `pytest` — all tests pass (agent: verify)
- T-6.3: Grep for orphaned references — search for `generate_pipelines`, `CicdStatus`, `SonarCicdConfig`, `pipeline.compliance`, `pipeline.injector`, `cicd_regenerate`, `action-pins`, `manifest.cicd` across entire codebase (agent: verify)
- T-6.4: Run `ai-eng --help` and `ai-eng install --help` — verify no cicd subcommand, install still works (agent: verify)

---

## Key Implementation Notes

- **Dependency order is critical**: Phase 1-2 delete consumers before Phase 3 deletes the models they consume. Reversing this order causes import failures.
- **`defaults.py` needs zero changes**: `default_install_manifest()` doesn't reference `CicdStatus` directly; the field used `default_factory`. Removing the field from `InstallManifest` is sufficient.
- **Pydantic forward-compat confirmed**: `InstallManifest` uses default `extra = "ignore"`. Existing `install-manifest.json` files with `cicd` key will deserialize cleanly after field removal.
- **`_build_manual_steps_for_cicd` does not exist**: The explore agent confirmed no such function. Manual steps are built inline in `_run_operational_phases`.
- **`_configure_sonarlint_if_possible` is only called from Phase 4**: Safe to delete. No other callsite exists.
