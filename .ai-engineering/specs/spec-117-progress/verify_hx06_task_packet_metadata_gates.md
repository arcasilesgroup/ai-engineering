# Verification: HX-06 Task-Packet Metadata Gates

## Passing Focused Evidence

- `13 passed`: `python -m pytest tests/unit/test_capabilities.py tests/unit/test_validator.py::TestManifestCoherence::test_task_capability_acceptance_passes_for_build_source_write tests/unit/test_validator.py::TestManifestCoherence::test_task_capability_acceptance_rejects_illegal_source_writer tests/unit/test_validator.py::TestManifestCoherence::test_task_capability_acceptance_rejects_illegal_tool_request tests/unit/test_validator.py::TestManifestCoherence::test_task_capability_acceptance_rejects_provider_incompatible_packet -q`
- `23 passed`: combined focused HX-06 suite covering capability cards, projection, internal specialist topology, and task-packet metadata gates.
- `ruff`: `python -m ruff check src/ai_engineering/state/capabilities.py src/ai_engineering/validator/categories/manifest_coherence.py tests/unit/test_capabilities.py tests/unit/test_validator.py --select I,F,E9`

## Result

Illegal task-packet tool requests and provider-incompatible execution are now blocked deterministically by `manifest-coherence`.