# Verify HX-03 T-5.1 Strict Instruction Destination Metadata Contract

## Ordered Verification

1. `uv run pytest tests/integration/test_installer_integration.py::TestCopyProjectTemplates::test_instruction_file_destinations_require_root_entry_metadata tests/integration/test_installer_integration.py::TestCopyProjectTemplates::test_instruction_template_sources_use_manifest_declared_paths tests/unit/validator/test_validator_provider_resolution.py::TestInstructionFilesRootEntryPointMetadata::test_instruction_files_requires_root_entry_point_metadata tests/unit/validator/test_validator_provider_resolution.py::TestInstructionFilesRootEntryPointMetadata::test_instruction_files_uses_manifest_declared_template_path`
   - `PASS`

## Key Signals

- Installer and validator root instruction discovery now agree on the same strict requirement: governed destinations must be backed by explicit `ownership.root_entry_points` metadata.
- The validator no longer manufactures governed instruction surfaces when `.ai-engineering/manifest.yml` is absent.
- The manifest-governed happy path still passes when `sync.template_path` metadata is present and explicit.