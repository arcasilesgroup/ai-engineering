# Build Handoff: HX-06 Task-Packet Metadata Gates

## Scope

- Routed optional ledger `mutationClasses`, `toolRequests`, and `provider` metadata into `CapabilityTaskPacket` construction.
- Kept inferred mutation classes as the compatibility default when ledger packets do not declare explicit mutation metadata.
- Added deterministic validator failures for illegal tool requests and provider-incompatible task packets.

## Implemented Files

- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `tests/unit/test_capabilities.py`
- `tests/unit/test_validator.py`

## Result

`manifest-coherence` now consumes explicit task-packet execution metadata instead of only deriving authority from write scopes.