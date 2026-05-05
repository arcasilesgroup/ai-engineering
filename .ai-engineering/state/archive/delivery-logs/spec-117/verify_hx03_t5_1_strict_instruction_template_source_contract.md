# Verify HX-03 T-5.1 Strict Instruction Template Source Contract

## Ordered Verification

1. `uv run pytest tests/integration/test_installer_integration.py::TestCopyProjectTemplates::test_instruction_template_sources_use_manifest_declared_paths tests/integration/test_installer_integration.py::TestCopyProjectTemplates::test_instruction_template_sources_require_root_entry_metadata tests/unit/test_validator.py::TestInstructionFiles::test_source_repo_includes_templates tests/unit/test_validator.py::TestInstructionFiles::test_non_source_repo_base_only`
   - `PASS`

## Key Signals

- Installer template counterpart resolution is now manifest-strict and no longer backfills `AGENTS.md`, `CLAUDE.md`, or Copilot template paths from the legacy provider map.
- The direct installer tests prove manifest-declared `sync.template_path` values are the only accepted source of truth for governed root instruction template counterparts.
- The adjacent validator source-repo regression continues to pass once the source-repo fixture provides the same governed root-entry metadata expected by the strict contract.