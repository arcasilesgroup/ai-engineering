---
id: spec-068
title: "State Unification: Eliminate tools.json, Redesign install-manifest.json, Model manifest.yml"
status: draft
created: 2026-03-25
refs: []
---

# spec-068: State Unification

## Problem

Three state/config files store overlapping information with no clear contract:

1. **`manifest.yml`** (YAML, human + framework-managed) — project config: vcs, stacks, ides, quality gates, skills registry. No Pydantic model. Read via raw `yaml.safe_load()` or regex. 2 direct consumers.

2. **`install-manifest.json`** (JSON, machine-managed) — duplicates config from manifest.yml (stacks, ides, providers, vcs) AND stores runtime state (tooling_readiness, branch_policy, operational_readiness). 43 refs in 24 files.

3. **`tools.json`** (JSON, machine-managed) — credential metadata for GitHub, SonarCloud, Azure DevOps. 15 refs in 4 files. Only created when user runs `ai-eng setup platforms`. Orphaned otherwise.

### Specific issues

- **Config duplication**: `manifest.yml:providers.stacks` = `["python"]` AND `install-manifest.json:installedStacks` = `["python"]`. Same data, two sources of truth, can diverge.
- **No typed access to manifest.yml**: Consumers use `yaml.safe_load()` -> raw dict, regex extraction, or custom dotted-path evaluation. No validation, no autocomplete, no schema enforcement.
- **tools.json is orphaned**: Never created during install. Only appears after `ai-eng setup platforms`. Doctor checks read it but it may not exist.
- **`_offer_platform_onboarding` re-detects instead of reading manifest**: After install gathers stacks/ides/vcs/providers and saves to manifest, the platform onboarding block ignores all of it and re-scans the filesystem.
- **Sonar prompt embedded in install flow**: `_offer_platform_onboarding` prompts "Configure SonarCloud?" during install. This is a setup concern, not an install concern.

## Solution

Three changes:

### A) Create `ManifestConfig` Pydantic model for `manifest.yml`

Typed read access to the user-editable config file. All consumers that need project config (stacks, ides, vcs, quality gates, work items) read from this model instead of raw YAML.

### B) Redesign `install-manifest.json` -> `install-state.json`

Strip all config duplication. The state file stores ONLY runtime state that changes during install/setup/doctor lifecycle. Absorb `tools.json` as the `platforms` section.

### C) Remove `_offer_platform_onboarding` from install flow

Platform credential setup is a post-install concern. Users run `ai-eng setup platforms` explicitly. The install flow ends after the pipeline summary.

## Scope

### In Scope

**A) ManifestConfig model**

1. Create `src/ai_engineering/config/manifest.py` with Pydantic model:
   ```python
   class ProvidersConfig(BaseModel):
       vcs: str = "github"
       ides: list[str] = Field(default_factory=lambda: ["claude_code"])
       stacks: list[str] = Field(default_factory=lambda: ["python"])

   class QualityConfig(BaseModel):
       coverage: int = 80
       duplication: int = 3
       cyclomatic: int = 10
       cognitive: int = 15

   class ManifestConfig(BaseModel):
       schema_version: str = "2.0"
       framework_version: str
       name: str
       providers: ProvidersConfig
       quality: QualityConfig
       tooling: list[str]
       # ... remaining sections
   ```

2. Create `src/ai_engineering/config/loader.py` with `load_manifest_config(root: Path) -> ManifestConfig` -- YAML parse + Pydantic validation.

3. Migrate consumers that read config from `install-manifest.json` to `ManifestConfig`:
   - `policy/gates.py` -- `installed_stacks` -> `manifest.providers.stacks`
   - `vcs/factory.py` -- `providers.primary` -> `manifest.providers.vcs` AND `tooling_readiness.gh.mode` -> `InstallState.tooling.gh.mode` (needs BOTH models)
   - `installer/operations.py` -- stack/ide/provider add/remove -> mutate manifest.yml
   - `skills/service.py` -- already reads manifest.yml, switch to typed model
   - `work_items/service.py` -- already reads manifest.yml, switch to typed model
   - `validator/categories/counter_accuracy.py` -- regex -> typed model
   - `validator/categories/instruction_consistency.py` -- raw dict -> typed model

**B) Redesign state file**

4. Rename `install-manifest.json` -> `install-state.json`. New schema:
   ```json
   {
     "schema_version": "2.0",
     "installed_at": "2026-03-25T10:00:00Z",
     "tooling": {
       "gh": { "installed": true, "authenticated": true, "mode": "cli", "scopes": ["repo"] },
       "az": { "installed": false, "authenticated": false, "mode": "api" },
       "gitleaks": { "installed": true },
       "ruff": { "installed": true },
       "semgrep": { "installed": false }
     },
     "platforms": {
       "sonar": {
         "configured": true,
         "url": "https://sonarcloud.io",
         "project_key": "my-project",
         "organization": "my-org",
         "credential_ref": { "service": "ai-engineering/sonar", "username": "token" }
       }
     },
     "branch_policy": { "applied": true, "mode": "cli" },
     "operational_readiness": { "status": "READY", "pending_steps": [] },
     "release": { "last_version": "0.4.0", "last_released_at": "2026-03-20T00:00:00Z" }
   }
   ```

5. Create `InstallState` Pydantic model in `src/ai_engineering/state/models.py` (replaces `InstallManifest`).

6. Delete `ToolsState`, `GitHubConfig`, `SonarConfig`, `AzureDevOpsConfig` from `credentials/models.py`.

7. Migrate `CredentialService.load_tools_state()` / `save_tools_state()` -> `load_install_state()` / `save_install_state()` reading from `install-state.json`.

8. Migrate all 24 files that import `InstallManifest`:
   - Files that read **config** (stacks, ides, providers) -> `ManifestConfig`
   - Files that read **state** (tooling, platforms, branch_policy) -> `InstallState`
   - Files that read both -> import both models

9. Add migration in `updater/service.py`:
   - If `install-manifest.json` exists: read it, extract state-only fields, write `install-state.json`, delete `install-manifest.json`
   - If `tools.json` exists: read it, merge platform data into `install-state.json`, delete `tools.json`

**C) Remove platform onboarding from install**

10. Delete `_offer_platform_onboarding()` from `core.py`.
11. Remove the call at `core.py:307`.
12. `ai-eng setup platforms` remains unchanged as the explicit entry point.
13. Add "Run `ai-eng setup platforms` to configure credentials" to the install summary's `suggest_next` list.

**D) Tests**

14. Unit tests for `ManifestConfig` model (parse valid manifest.yml, handle missing sections, validate defaults).
15. Unit tests for `InstallState` model (roundtrip serialize/deserialize, migration from old format).
16. Update existing tests that import `InstallManifest` -> `InstallState` or `ManifestConfig`.
17. Update setup.py tests to use `install-state.json` instead of `tools.json`.

### Out of Scope

- Changes to `manifest.yml` structure or content (it stays as-is, we just model it)
- Changes to the 6-phase install pipeline logic
- Changes to `ai-eng setup platforms` command behavior
- Changes to the credential service keyring operations
- Moving manifest.yml to a different location
- Modifying the skills/agents registry sections of manifest.yml

## Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | `ManifestConfig` is read-only for most consumers | manifest.yml is human-editable. Only `installer/operations.py` (stack/ide/provider add/remove) writes to it. All others read. |
| D2 | State file stays JSON, not YAML | Pydantic serializes cleanly to JSON. YAML write is fragile (comment preservation, ordering). JSON is the right format for machine-managed state. |
| D3 | Rename to `install-state.json` | Signals the change: this is runtime state, not a manifest. Old name was confusing -- "install manifest" sounds like config. |
| D4 | `tooling` section is flat, not nested by category | Current `ToolingReadiness` has `gh`, `az`, `python.ruff`, `python.uv` etc. Flatten to tool-level. Stack-specific tooling grouping adds complexity without value -- `ruff` is `ruff` whether it's under `python` or not. `gh.mode` and `az.mode` are preserved (consumers like `vcs/factory.py` depend on them). |
| D5 | `platforms` absorbs `tools.json` | Credential metadata (URL, project_key, credential_ref) is runtime state, not config. Lives alongside tooling state, not in manifest.yml. |
| D6 | Migration is mandatory in `ai-eng update` | Projects with existing `install-manifest.json` and/or `tools.json` must be migrated automatically. No manual intervention. |
| D7 | Remove `_offer_platform_onboarding` entirely | It re-detects what install already knows, duplicates the SonarCloud prompt, and the detected list doesn't even pass through to `setup_platforms_cmd`. Clean cut. |

## Acceptance Criteria

### ManifestConfig Model
- [ ] AC1: `ManifestConfig` parses the current `manifest.yml` without errors
- [ ] AC2: `load_manifest_config()` returns typed model with all sections accessible
- [ ] AC3: Missing optional sections use sensible defaults (same as current behavior)
- [ ] AC4: `policy/gates.py` reads stacks from `ManifestConfig` instead of `InstallManifest`
- [ ] AC5: `vcs/factory.py` reads VCS provider from `ManifestConfig` instead of `InstallManifest`

### State File Redesign
- [ ] AC6: `install-state.json` has no config duplication (no stacks, ides, providers, framework_version)
- [ ] AC7: `install-state.json` includes `platforms` section (absorbed from tools.json)
- [ ] AC8: `InstallState` Pydantic model validates the new schema
- [ ] AC9: `CredentialService` reads/writes platform state from `install-state.json`
- [ ] AC10: `tools.json` is no longer created or read by any code path

### Migration
- [ ] AC11: `ai-eng update` migrates `install-manifest.json` -> `install-state.json`
- [ ] AC11a: If neither `install-manifest.json` nor `tools.json` exists, migration is a no-op with no error
- [ ] AC12: `ai-eng update` merges `tools.json` data into `install-state.json`
- [ ] AC13: Migration deletes old files after successful conversion
- [ ] AC14: Migration is idempotent — if `install-state.json` exists and old files are absent, migration is a no-op. If both old and new exist (partial migration), old file takes precedence and overwrites

### Platform Onboarding Removal
- [ ] AC15: `ai-eng install` does NOT prompt "Configure SonarCloud/SonarQube?"
- [ ] AC16: `ai-eng install` does NOT prompt "Configure platform credentials now?"
- [ ] AC17: Install summary suggests `ai-eng setup platforms` as a next step
- [ ] AC18: `ai-eng setup platforms` continues to work unchanged

### YAML Write (operations.py)
- [ ] AC19: `stack add` / `stack remove` persists changes to `manifest.yml`
- [ ] AC20: YAML roundtrip preserves existing comments and structure in manifest.yml
- [ ] AC21: `provider add` / `provider remove` persists to `manifest.yml` and verifies read-back

### Tests
- [ ] AC22: Unit tests for ManifestConfig parsing (valid, partial, empty)
- [ ] AC23: Unit tests for InstallState (serialize, deserialize, migration)
- [ ] AC24: All existing tests pass after migration (zero regressions)
- [ ] AC25: No imports of `InstallManifest` remain in production code (verified by grep)
- [ ] AC26: No imports of `ToolsState` remain in production code (verified by grep)
- [ ] AC27: No production code references the string `tools.json` (verified by grep)

## Files Changed

| Action | Path | Notes |
|--------|------|-------|
| create | `src/ai_engineering/config/manifest.py` | ManifestConfig Pydantic model |
| create | `src/ai_engineering/config/loader.py` | YAML loader with validation |
| create | `src/ai_engineering/config/__init__.py` | Package init |
| modify | `src/ai_engineering/state/models.py` | Replace InstallManifest with InstallState |
| modify | `src/ai_engineering/credentials/models.py` | Remove ToolsState, GitHubConfig, SonarConfig, AzureDevOpsConfig |
| modify | `src/ai_engineering/credentials/service.py` | Migrate load/save to install-state.json |
| modify | `src/ai_engineering/cli_commands/core.py` | Remove _offer_platform_onboarding |
| modify | `src/ai_engineering/cli_commands/setup.py` | Use InstallState instead of ToolsState |
| modify | `src/ai_engineering/installer/service.py` | Use ManifestConfig + InstallState |
| modify | `src/ai_engineering/installer/operations.py` | Read/write manifest.yml for config mutations |
| modify | `src/ai_engineering/vcs/factory.py` | Read VCS from ManifestConfig |
| modify | `src/ai_engineering/policy/gates.py` | Read stacks from ManifestConfig |
| modify | `src/ai_engineering/doctor/service.py` | Use InstallState for platform checks |
| modify | `src/ai_engineering/doctor/checks/readiness.py` | Use InstallState |
| modify | `src/ai_engineering/doctor/checks/state_files.py` | Check install-state.json |
| modify | `src/ai_engineering/updater/service.py` | Migration logic + new paths |
| modify | `src/ai_engineering/state/defaults.py` | Default InstallState factory |
| modify | `src/ai_engineering/state/service.py` | Load/save InstallState |
| modify | `src/ai_engineering/release/orchestrator.py` | Use InstallState for release tracking |
| modify | `src/ai_engineering/skills/service.py` | Use ManifestConfig |
| modify | `src/ai_engineering/work_items/service.py` | Use ManifestConfig |
| modify | `src/ai_engineering/validator/categories/counter_accuracy.py` | Use ManifestConfig |
| modify | `src/ai_engineering/validator/categories/instruction_consistency.py` | Use ManifestConfig |
| modify | `src/ai_engineering/maintenance/report.py` | Use ManifestConfig for version |
| modify | `src/ai_engineering/installer/phases/__init__.py` | Remove InstallManifest import, use InstallState |
| modify | `src/ai_engineering/installer/phases/detect.py` | Rename path string to install-state.json |
| modify | `src/ai_engineering/installer/phases/state.py` | Rename path string to install-state.json |
| modify | `src/ai_engineering/installer/phases/governance.py` | Rename path string to install-state.json |
| modify | `src/ai_engineering/state/audit.py` | Update _STATE_REGENERATED set to install-state.json |
| modify | `src/ai_engineering/lib/signals.py` | Rename path string to install-state.json |
| modify | `src/ai_engineering/cli_commands/guide.py` | Rename path string to install-state.json |
| modify | `src/ai_engineering/detector/readiness.py` | Use InstallState (reads tooling + branch_policy) |
| modify | `src/ai_engineering/credentials/__init__.py` | Remove ToolsState re-exports if present |
| delete | (runtime) `tools.json` | Migrated into install-state.json |
| rename | (runtime) `install-manifest.json` -> `install-state.json` | State file redesign |
| create | `tests/unit/config/test_manifest.py` | ManifestConfig tests |
| create | `tests/unit/state/test_install_state.py` | InstallState tests |
| modify | `tests/` (multiple) | Update InstallManifest -> InstallState imports |

## Risks

| Risk | Mitigation |
|------|-----------|
| 24-file migration is error-prone | Mechanical: search/replace InstallManifest imports, verify each caller reads config vs state. Type checker catches mismatches. |
| manifest.yml format changes break ManifestConfig | Model uses optional fields with defaults. `yaml.safe_load()` handles missing sections. Versioned via `schema_version`. |
| Existing installations have install-manifest.json | Migration in `ai-eng update` handles conversion automatically. |
| tools.json may not exist (never ran setup) | Migration handles absence gracefully -- `platforms` section starts empty. |
| `installer/operations.py` now writes YAML | Use `ruamel.yaml` (required dependency) for comment-preserving writes. AC20 validates roundtrip correctness. |

## Dependencies

- `pyyaml` (already a dependency, used for read-only loading)
- `ruamel.yaml` (new dependency, required for comment-preserving YAML writes in `operations.py`)
