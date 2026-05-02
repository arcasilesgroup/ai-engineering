# Build: HX-08 Runtime Core Extraction Track A

## Summary

Implemented a focused runtime repository boundary for manifest and durable-state artifacts.

## Boundary Matrix

| Surface | Authority | Repository API | Compatibility Kept |
| --- | --- | --- | --- |
| Manifest typed reads | `config/loader.py` | `ManifestRepository.load_typed()` | Default manifest behavior and `ai_providers` migration remain unchanged. |
| Manifest raw snapshots | `state/repository.py` | `ManifestRepository.load_raw()` | Partial readers can keep using raw snapshots without requiring strict full-manifest validation. |
| Manifest partial reads | `state/repository.py` | `ManifestRepository.get_partial()` | Dotted-path compatibility reads return `None` when absent. |
| Manifest field patching | `config/loader.py` | `ManifestRepository.patch_field()` | Comment-preserving `ruamel.yaml` writes remain single-sourced. |
| Manifest projections | `state/manifest.py` | `_read_raw_manifest()` delegates to `ManifestRepository.load_raw()` | Required-tools, SDK prereqs, and Python env mode projection behavior remains unchanged. |
| Install state | `state/service.py` | `DurableStateRepository.load_install_state()` | Legacy install-state migration and carry-forward behavior remain single-sourced in `state.service`. |
| Decision store | `state/repository.py` | `load_decisions()` / `save_decisions()` | `StateService` stays as a compatibility facade over the repository. |
| Ownership map | `state/repository.py` | `load_ownership()` / `save_ownership()` | Existing ownership-map model and default generation remain unchanged. |
| Framework capabilities | `state/repository.py` | `load_framework_capabilities()` / `save_framework_capabilities()` | Projection file path is stable. |
| Framework events | `state/repository.py` | `framework_events_path` / `append_framework_event()` delegate | Event append semantics remain owned by observability and outside Track A redesign. |

## Changes

- Added `src/ai_engineering/state/repository.py` with `ManifestRepository` and `DurableStateRepository`.
- Routed `state/manifest.py` raw manifest projection reads through `ManifestRepository`.
- Routed `StateService` stable state-family reads/writes through `DurableStateRepository` while preserving the existing facade.
- Added `tests/unit/test_runtime_repositories.py` covering typed/raw/partial/patch manifest behavior, durable-state family paths and loaders, `StateService` compatibility, and install-state migration preservation.

## Deferred Boundaries

- Event vocabulary, event schema, and task traces remain owned by `HX-05`.
- Kernel execution and findings semantics remain owned by `HX-04`.
- Installer, doctor, updater convergence remains deferred to `HX-09`.
- CLI adapter and asset-runtime cleanup remains deferred to `HX-10`.
