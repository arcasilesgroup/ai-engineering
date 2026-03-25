# Plan: spec-068 State Unification

## Pipeline: full
## Phases: 7
## Tasks: 22 (build: 17, verify: 5)

---

### Phase 1: New models (additive, zero breakage)
**Gate**: ManifestConfig parses manifest.yml; InstallState serializes/deserializes correctly. No existing code modified.

- [x] T-1.1: Create `config/` package with ManifestConfig model (agent: build) -- DONE
  - Create `src/ai_engineering/config/__init__.py`, `manifest.py`, `loader.py`
  - ManifestConfig models all sections of manifest.yml (providers, quality, tooling, work_items, documentation, cicd, skills, agents, ownership)
  - `load_manifest_config(root) -> ManifestConfig` -- yaml.safe_load + Pydantic validate
  - All fields optional with sensible defaults (graceful degradation for partial manifests)
  - **Done when**: `ManifestConfig.model_validate(yaml.safe_load(manifest.yml))` succeeds on this repo's manifest

- [x] T-1.2: Write tests for ManifestConfig (agent: build) -- DONE (46 tests)
  - Create `tests/unit/config/test_manifest.py`
  - Test: parse real manifest.yml, parse partial manifest, parse empty file, missing file
  - Test: all config fields accessible via typed attributes
  - **Done when**: Tests pass GREEN

- [x] T-1.3: Create InstallState model in state/models.py (agent: build) -- DONE
  - Add `InstallState` as NEW class alongside existing `InstallManifest` (don't delete yet)
  - Flat tooling section: `ToolEntry` with installed/authenticated/mode/scopes
  - Platforms section: absorb SonarConfig, AzureDevOpsConfig, GitHubConfig structures
  - Keep branch_policy, operational_readiness, release sections
  - No stacks, ides, providers, ai_providers, framework_version (config lives in manifest.yml)
  - **Done when**: `InstallState` model defined, coexists with `InstallManifest`

- [x] T-1.4: Write tests for InstallState (agent: build) -- DONE (21 tests)
  - Create `tests/unit/state/test_install_state.py`
  - Test: serialize/deserialize roundtrip, default values, platform credential refs
  - Test: migration helper (convert old InstallManifest dict -> InstallState)
  - **Done when**: Tests pass GREEN

- [x] T-1.5: Verify new models (agent: verify) -- DONE (67/67 pass, 1945/1946 unit suite)
  - Verify ManifestConfig parses this repo's manifest.yml
  - Verify InstallState roundtrip matches expected JSON schema from spec
  - Verify no existing tests broke (new code is purely additive)
  - **Done when**: `pytest tests/unit/config/ tests/unit/state/test_install_state.py` passes, full suite green

---

### Phase 2: State file I/O + migration infrastructure
**Gate**: install-state.json can be read/written. Migration converts old files to new format. No consumers switched yet.

- [ ] T-2.1: Add InstallState load/save to state service (agent: build)
  - Add `load_install_state()` / `save_install_state()` to `state/service.py` (or `credentials/service.py`)
  - File: `.ai-engineering/state/install-state.json`
  - Coexist with old `load_tools_state()` -- don't delete yet
  - **Done when**: Can write and read InstallState to install-state.json

- [ ] T-2.2: Add migration functions to updater/service.py (agent: build)
  - `_migrate_install_manifest()`: read install-manifest.json -> extract state fields -> write install-state.json -> delete old
  - `_migrate_tools_json()`: read tools.json -> merge into install-state.json platforms section -> delete old
  - Both idempotent: no-op if source absent, overwrite if both exist (old wins)
  - Wire into `update()` flow before existing migrations
  - **Done when**: Migration converts fixture files correctly

- [ ] T-2.3: Write tests for migration (agent: build)
  - Test: migrate install-manifest.json -> install-state.json (config fields stripped, state preserved)
  - Test: migrate tools.json -> platforms section merged
  - Test: both files absent -> no-op
  - Test: both old and new exist -> old overwrites new
  - Test: idempotent (run twice, same result)
  - **Done when**: All migration tests pass

- [ ] T-2.4: Verify migration (agent: verify)
  - Run migration tests
  - Verify old models still work (no breakage to existing consumers)
  - **Done when**: Full test suite green

---

### Phase 3: Remove platform onboarding from install
**Gate**: `ai-eng install` no longer prompts for SonarCloud or platform credentials. `ai-eng setup platforms` unchanged.

- [ ] T-3.1: Remove _offer_platform_onboarding from core.py (agent: build)
  - Delete `_offer_platform_onboarding()` function
  - Remove the call at end of `install_cmd()`
  - Add `("ai-eng setup platforms", "Configure platform credentials")` to `suggest_next` list
  - **Done when**: Install flow ends after summary panel without interactive prompts

- [ ] T-3.2: Update install tests (agent: build)
  - Remove/update tests that expect SonarCloud/platform prompts during install
  - Verify test_install_clean, test_install_existing still pass
  - **Done when**: All install tests pass without prompt expectations

---

### Phase 4: Migrate config consumers to ManifestConfig
**Gate**: All files that read config (stacks, ides, providers, vcs) use ManifestConfig. InstallManifest still exists but config fields are no longer read from it.

- [ ] T-4.1: Migrate config-only consumers (agent: build)
  - `policy/gates.py`: `installed_stacks` -> `load_manifest_config(root).providers.stacks`
  - `skills/service.py`: raw yaml.safe_load -> `load_manifest_config(root)`
  - `work_items/service.py`: raw yaml.safe_load -> `load_manifest_config(root)`
  - `validator/categories/counter_accuracy.py`: regex -> `load_manifest_config(root).skills.total`
  - `validator/categories/instruction_consistency.py`: raw dict -> `load_manifest_config(root)`
  - `maintenance/report.py`: `framework_version` -> `load_manifest_config(root).framework_version`
  - **Done when**: No config-field reads from InstallManifest in these files

- [ ] T-4.2: Migrate dual consumers (config+state) (agent: build)
  - `vcs/factory.py`: split -- VCS from ManifestConfig, mode from InstallState
  - `installer/service.py`: split -- config from ManifestConfig, state writes to InstallState
  - `detector/readiness.py`: split -- stacks from ManifestConfig, tooling/branch from InstallState
  - `installer/operations.py`: config mutations write to manifest.yml via ruamel.yaml
  - **Done when**: These files import ManifestConfig + InstallState, not InstallManifest

- [ ] T-4.3: Add ruamel.yaml dependency + YAML write for operations.py (agent: build)
  - Add `ruamel.yaml` to pyproject.toml
  - Implement comment-preserving YAML write in operations.py for stack/ide/provider mutations
  - Test roundtrip: load manifest.yml -> add stack -> save -> reload -> verify comments preserved
  - **Done when**: `stack add python` roundtrip preserves manifest.yml structure

---

### Phase 5: Migrate state consumers to InstallState
**Gate**: All files that read/write state use InstallState. InstallManifest still exists but unused.

- [ ] T-5.1: Migrate state-only consumers (agent: build)
  - `doctor/checks/readiness.py`: InstallManifest -> InstallState
  - `doctor/checks/state_files.py`: path string -> install-state.json
  - `doctor/service.py`: ToolsState -> InstallState.platforms
  - `release/orchestrator.py`: InstallManifest -> InstallState (release section)
  - `hooks/manager.py`: InstallManifest -> InstallState (git_hooks section)
  - `cli_commands/setup.py`: ToolsState -> InstallState.platforms
  - `credentials/service.py`: load/save_tools_state -> load/save via InstallState
  - **Done when**: No imports of ToolsState or state-field reads from InstallManifest

- [ ] T-5.2: Migrate path-string references (agent: build)
  - `installer/phases/detect.py`: string `install-manifest.json` -> `install-state.json`
  - `installer/phases/state.py`: string -> `install-state.json`
  - `installer/phases/governance.py`: string -> `install-state.json`
  - `installer/phases/__init__.py`: remove InstallManifest import
  - `state/audit.py`: _STATE_REGENERATED set -> `install-state.json`
  - `state/defaults.py`: default factory -> `default_install_state()`
  - `lib/signals.py`: path string -> `install-state.json`
  - `cli_commands/guide.py`: path string -> `install-state.json`
  - `cli_commands/core.py`: path string -> `install-state.json`
  - `cli_commands/vcs.py`: path string -> `install-state.json`
  - **Done when**: grep for `install-manifest.json` in src/ returns zero results

- [ ] T-5.3: Verify zero InstallManifest/ToolsState usage (agent: verify)
  - grep `InstallManifest` in src/ -- only models.py (definition) should remain
  - grep `ToolsState` in src/ -- zero results
  - grep `tools.json` in src/ -- zero results
  - grep `install-manifest.json` in src/ -- zero results
  - **Done when**: All greps clean

---

### Phase 6: Delete old code
**Gate**: Old models removed. Only InstallState and ManifestConfig exist.

- [ ] T-6.1: Delete InstallManifest and ToolsState (agent: build)
  - Remove `InstallManifest` class from state/models.py (keep other models: OwnershipMap, DecisionStore, AuditEntry)
  - Remove `default_install_manifest()` from state/defaults.py
  - Remove `ToolsState`, `GitHubConfig`, `SonarConfig`, `AzureDevOpsConfig` from credentials/models.py
  - Remove `load_tools_state()` / `save_tools_state()` from credentials/service.py
  - Clean up `credentials/__init__.py` re-exports
  - Remove all supporting sub-models only used by InstallManifest (ToolingReadiness, PythonTooling, etc.)
  - **Done when**: Old models deleted, no import errors

---

### Phase 7: Test migration + final verification
**Gate**: Full test suite green. AC25/AC26/AC27 verified.

- [ ] T-7.1: Migrate test files (agent: build)
  - Update ~17 test files: `InstallManifest` -> `InstallState` or `ManifestConfig`
  - Update fixture helpers (conftest.py `install()` calls)
  - Update `install-manifest.json` path strings -> `install-state.json`
  - Update `tools.json` -> `install-state.json` platform section
  - Key files: test_state.py, test_installer.py, test_install_clean.py, test_install_existing.py, test_installer_integration.py, test_install_operational_flows.py, test_credentials.py, test_sonar_gate.py, conftest.py
  - **Done when**: All test imports updated

- [ ] T-7.2: Run full test suite (agent: verify)
  - `pytest` full run
  - Fix any failures
  - **Done when**: Full suite green

- [ ] T-7.3: Final grep verification (agent: verify)
  - AC25: `grep -r "InstallManifest" src/` -> zero (definition removed)
  - AC26: `grep -r "ToolsState" src/` -> zero
  - AC27: `grep -r "tools\.json" src/` -> zero
  - `grep -r "install-manifest\.json" src/` -> zero
  - **Done when**: All greps return zero matches in production code
