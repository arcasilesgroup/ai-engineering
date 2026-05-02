# Verification: HX-06 Internal Topology Parity

## Passing Focused Evidence

- `10 passed`: `python -m pytest tests/unit/test_capabilities.py tests/unit/test_sync_mirrors.py::TestGenerationFunctions::test_generate_specialist_agent_adds_internal_provenance tests/unit/test_sync_mirrors.py::TestGenerationFunctions::test_specialist_agent_output_paths_are_provider_internal_roots tests/unit/test_validator.py::TestClaudeSpecialistAgentsMirror::test_claude_specialist_agents_mirror_sync_ok -q`
- `ruff`: `python -m ruff check src/ai_engineering/state/capabilities.py scripts/sync_command_mirrors.py tests/unit/test_capabilities.py tests/unit/test_sync_mirrors.py`

## Known Unrelated Residuals

- `tests/unit/test_sync_mirrors.py::TestSyncDriftDetection::test_check_mode_returns_zero` still reports broad pre-existing mirror drift across generated provider skill and agent surfaces. The specialist internal-root contract itself is covered by focused tests.

## Result

Internal specialist agents remain generated and usable, but no longer behave like public first-class agent capability outputs.