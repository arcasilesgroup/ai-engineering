---
id: spec-074
title: "Provider/IDE Field Separation, Release Flow Fix, Verify Governance Rewrite"
status: approved
created: 2026-03-25
refs: []
---

# spec-074: Provider/IDE Field Separation, Release Flow Fix, Verify Governance Rewrite

## Problem

Three bugs identified in the CLI audit, all requiring schema or behavioral changes.

### 1. `providers.ides` conflates AI providers with IDEs

`ProvidersConfig` has a single `ides: list[str]` field that stores both AI providers (`claude_code`, `github_copilot`) and IDEs (`vscode`, `jetbrains`). The default value is `["claude_code"]` — an AI provider, not an IDE.

**Impact:**
- `ai-eng provider list` shows IDEs as providers
- `ai-eng ide list` shows AI providers as IDEs
- `ide_config` phase treats all entries as AI providers for template deployment
- `doctor/phases/ide_config` passes IDE names to `resolve_template_maps(providers=...)`

**Double bug in operations.py:** `add_provider()` reads `providers.ides` for duplicate check but never calls `update_manifest_field` — the provider is never persisted. Same for `remove_provider()`.

**Evidence:** `InstallContext` already has separate `providers` and `ides` fields. The separation exists at runtime but not in the manifest schema. `_KNOWN_IDES` and `_VALID_AI_PROVIDERS` sets are already defined and disjoint in `operations.py`.

### 2. `release` without `--wait` creates tag before PR merge

Without `--wait`, the release flow: create PR (phase 4) → skip wait-for-merge → `_create_tag()` which runs `git checkout main && git pull --ff-only`. If the PR hasn't merged, `pull --ff-only` either fails or tags the wrong commit.

**Evidence:** `orchestrator.py` lines 216-219 return `PhaseResult(success=True, skipped=True)` for the wait phase, then line 221 immediately calls `_create_tag()`.

### 3. `verify governance` is a subprocess proxy

`verify_governance()` calls `["uv", "run", "ai-eng", "validate", "--json"]` as subprocess. It depends on `uv` being installed, discards all structured output from validate, and produces only a single `CRITICAL` finding with no detail about which category failed.

**Evidence:** `verify/service.py` lines 116-131.

## Solution

### Group 1: Provider/IDE Field Separation

Add `AiProvidersConfig` sub-model to `ProvidersConfig` with `enabled: list[str]` and `primary: str`. Migrate all consumers.

**Schema change in `config/manifest.py`:**

```python
class AiProvidersConfig(BaseModel):
    enabled: list[str] = Field(default_factory=lambda: ["claude_code"])
    primary: str = "claude_code"

class ProvidersConfig(BaseModel):
    vcs: str = "github"
    ai_providers: AiProvidersConfig = Field(default_factory=AiProvidersConfig)
    ides: list[str] = Field(default_factory=list)  # now truly IDEs only
    stacks: list[str] = Field(default_factory=lambda: ["python"])
```

**manifest.yml migration:** Existing `providers.ides` values are split: entries matching `_VALID_AI_PROVIDERS` move to `providers.ai_providers.enabled`, remainder stays in `providers.ides`. The `load_manifest_config()` loader handles legacy format transparently.

**Consumer updates:**

| Consumer | Current | After |
|----------|---------|-------|
| `provider.py` (CLI) | `manifest.providers.ides` | `manifest.providers.ai_providers.enabled` |
| `operations.py` `add_provider()` | reads `providers.ides`, never writes | reads/writes `providers.ai_providers.enabled` |
| `operations.py` `remove_provider()` | reads `providers.ides`, never writes | reads/writes `providers.ai_providers.enabled` |
| `installer/phases/ide_config.py` | `manifest.providers.ides` as providers | `manifest.providers.ai_providers.enabled` |
| `doctor/phases/ide_config.py` | `manifest.providers.ides` as providers | `manifest.providers.ai_providers.enabled` |
| `stack_ide.py` `ide_*` | `manifest.providers.ides` | unchanged (now correctly only IDEs) |
| `lib/signals.py` | reads `providers.ides` for telemetry | `providers.ai_providers.enabled` |

**Fix `add_provider()`/`remove_provider()`:** After template copy/removal, call `update_manifest_field(target, "providers.ai_providers.enabled", updated_list)` to actually persist the change.

### Group 2: Release Flow Fix

Make `--wait` the default behavior. Without `--wait`, stop after creating the PR — do NOT attempt to create the tag.

**Change in `orchestrator.py`:**

When `config.wait` is False:
- Phases "prepare" and "pr" execute normally
- Phase "wait-for-merge" is skipped (as now)
- Phase "tag" is **also skipped** with message: "Tag creation deferred — run `ai-eng release <version> --wait` to tag after merge"
- Phase "monitor" is skipped

This is a behavioral change but prevents the silent bug. The tag is only created when we can verify the PR is merged.

### Group 3: Verify Governance Direct Import

Replace the subprocess call with a direct Python import of the validation logic.

**Change in `verify/service.py`:**

```python
# Before: subprocess
result = subprocess.run(["uv", "run", "ai-eng", "validate", "--json"], ...)

# After: direct import
from ai_engineering.validator.service import validate_content_integrity
report = validate_content_integrity(project_root)
# Map each failed category to a Finding with proper severity and detail
```

This eliminates the `uv` dependency, provides structured output (which categories failed and why), and removes the opaque single-CRITICAL-finding behavior.

## Scope

### In Scope

1. Add `AiProvidersConfig` model to `config/manifest.py` with `enabled` and `primary` fields
2. Update `ProvidersConfig.ides` default from `["claude_code"]` to `[]`
3. Add migration logic in `load_manifest_config()` for legacy `providers.ides` containing AI provider values
4. Update `provider.py` CLI to read/write `providers.ai_providers.enabled`
5. Fix `add_provider()` to actually write to manifest via `update_manifest_field`
6. Fix `remove_provider()` to actually write to manifest via `update_manifest_field`
7. Update `installer/phases/ide_config.py` to read `providers.ai_providers.enabled`
8. Update `doctor/phases/ide_config.py` to read `providers.ai_providers.enabled`
9. Update `lib/signals.py` telemetry to read `providers.ai_providers.enabled`
10. Fix `test_provider_commands.py` integration tests to pass with new model
11. Update `installer/service.py` to populate `providers.ai_providers` during install
12. Update `orchestrator.py`: skip tag phase when `wait=False`
13. Update release tests for new skip behavior
14. Replace `verify_governance()` subprocess with direct import of `validate_content_integrity()`
15. Update verify tests for new governance implementation
16. Update dogfooding `manifest.yml` to new schema
17. Update manifest template for new projects

### Out of Scope

- Changing `_KNOWN_IDES` or `_VALID_AI_PROVIDERS` sets (already correct)
- Adding new AI providers or IDEs
- Changing the `ide` CLI command behavior (now correctly scoped to IDEs)
- Release `--wait` polling mechanism (already works correctly)
- Verify scoring/thresholds (only the governance mode is changed)

## Acceptance Criteria

- [ ] AC1: `ProvidersConfig` has `ai_providers: AiProvidersConfig` field with `enabled` and `primary`
- [ ] AC2: `ProvidersConfig.ides` defaults to `[]` (empty list, not `["claude_code"]`)
- [ ] AC3: `ai-eng provider add github_copilot` writes to `providers.ai_providers.enabled` in manifest.yml
- [ ] AC4: `ai-eng provider remove github_copilot` writes to `providers.ai_providers.enabled` in manifest.yml
- [ ] AC5: `ai-eng provider list` shows only AI providers, not IDEs
- [ ] AC6: `ai-eng ide list` shows only IDEs, not AI providers
- [ ] AC7: Legacy manifest.yml with `providers.ides: ["claude_code"]` loads correctly (migration)
- [ ] AC8: `test_provider_commands.py` integration tests all pass
- [ ] AC9: `ai-eng release 1.0.0` (without --wait) creates PR but does NOT create tag
- [ ] AC10: `ai-eng release 1.0.0 --wait` creates PR, waits for merge, THEN creates tag
- [ ] AC11: `ai-eng verify governance` produces per-category findings, not a single opaque CRITICAL
- [ ] AC12: `ai-eng verify governance` does NOT spawn a subprocess
- [ ] AC13: All existing tests pass (`pytest tests/ -x`)
- [ ] AC14: `ruff check src/` passes

## Files Modified

| File | Change |
|------|--------|
| `src/ai_engineering/config/manifest.py` | Add `AiProvidersConfig`, update `ProvidersConfig` |
| `src/ai_engineering/config/loader.py` | Migration logic for legacy `providers.ides` |
| `src/ai_engineering/cli_commands/provider.py` | Read/write `ai_providers.enabled` |
| `src/ai_engineering/installer/operations.py` | Fix add/remove to write manifest, use `ai_providers` |
| `src/ai_engineering/installer/phases/ide_config.py` | Read `ai_providers.enabled` |
| `src/ai_engineering/doctor/phases/ide_config.py` | Read `ai_providers.enabled` |
| `src/ai_engineering/installer/service.py` | Populate `ai_providers` during install |
| `src/ai_engineering/lib/signals.py` | Read `ai_providers.enabled` for telemetry |
| `src/ai_engineering/release/orchestrator.py` | Skip tag when `wait=False` |
| `src/ai_engineering/verify/service.py` | Direct import instead of subprocess |
| `tests/integration/test_provider_commands.py` | Fix for new model |
| `tests/unit/test_provider_cli.py` | Update mocks for new field |
| `tests/unit/test_release_orchestrator.py` | Test skip-tag behavior |
| `tests/unit/test_verify_service.py` | Test direct import governance |
| `tests/unit/test_manifest_config.py` | Test AiProvidersConfig + migration |
| `.ai-engineering/manifest.yml` | Update to new schema |
| `src/ai_engineering/templates/.ai-engineering/manifest.yml` | Update template |

## Assumptions

- The disjoint sets `_KNOWN_IDES` and `_VALID_AI_PROVIDERS` in operations.py are sufficient for migration detection
- `validate_content_integrity()` is importable without side effects
- No external tools depend on the `providers.ides` field containing AI providers
- The `primary` field in `AiProvidersConfig` defaults to the first entry in `enabled`

## Risks

| Risk | Mitigation |
|------|-----------|
| Legacy manifest.yml breaks on load | Migration in loader transparently converts old format |
| Release users expect tag without --wait | Behavioral change documented in CLI output with clear next-step message |
| verify governance loses subprocess isolation | Direct import is simpler and provides richer output; no isolation needed for same-process validation |
| Updater touches manifest.yml | Updater uses `update_manifest_field` which preserves structure; new fields are additive |

## Dependencies

- None external. Builds on spec-073 (dead commands removed).
- Does NOT touch any files from spec-072 (installer/autodetect.py, wizard.py).
