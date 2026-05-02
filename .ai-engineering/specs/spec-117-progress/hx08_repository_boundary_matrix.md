# HX-08 Repository Boundary Matrix

## Authority Rules

| Family | Authoritative Layer | Repository Role | Projection Role | Out Of Scope |
| --- | --- | --- | --- | --- |
| Manifest typed config | `config/loader.py` and `config/manifest.py` | Expose typed load and comment-preserving patch through `ManifestRepository`. | Consume repository raw snapshots for sub-block projections. | Rewriting manifest schema or removing compatibility defaults. |
| Manifest partial readers | `state/repository.py` | Expose raw snapshot and dotted partial reads. | Normalize specialized views such as required tools and SDK prereqs. | Forcing all consumers through strict full-manifest validation. |
| Install state | `state/service.py` install-state helpers | Expose migration-preserving load path through `DurableStateRepository`. | None in Track A. | Replacing migration semantics with generic JSON storage. |
| Decision store | `state/models.py` and stable state path | Expose load/save path through `DurableStateRepository`. | Active-decision slices stay derived where already implemented. | Redesigning risk lifecycle semantics. |
| Ownership map | `state/defaults.py`, `state/control_plane.py`, stable state path | Expose load/save path through `DurableStateRepository`. | Ownership projections remain downstream views. | Redesigning control-plane ownership vocabulary. |
| Framework capabilities | `state/observability.py`, `state/capabilities.py`, stable state path | Expose load/save path through `DurableStateRepository`. | Capability catalog remains a generated projection. | Redesigning capability-card semantics from `HX-06`. |
| Framework events | `state/observability.py` and audit-chain helpers | Expose stable path and delegate append through `DurableStateRepository`. | Audit-chain validation remains separate. | Changing event append format, event vocabulary, or trace semantics. |

## Leaking Consumers Addressed

- `state/manifest.py` no longer owns its own YAML raw-reader implementation; projection loaders consume `ManifestRepository.load_raw()`.
- `StateService` no longer owns duplicated decision, ownership, or framework-capabilities file paths; it delegates to `DurableStateRepository` as a compatibility facade.

## Compatibility Readers Preserved

- Raw manifest snapshots and dotted partial reads are first-class repository APIs.
- Missing or unreadable raw manifests still degrade to `{}`.
- Missing partial paths still degrade to `None`.
- Typed missing manifests still return `ManifestConfig()` through the existing loader.
- Install-state legacy migration still runs through `state.service.load_install_state()`.

## Deferred Leakage

Direct path constants in lower-level authority modules remain allowed when they define canonical artifact identity. Broad CLI/installer/doctor/updater convergence is deferred to `HX-09`, and adapter/runtime cleanup is deferred to `HX-10`.
