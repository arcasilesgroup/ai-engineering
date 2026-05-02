# Verification: HX-06 Prompt And Tool Parity

## Passing Focused Evidence

- `1 passed`: `python -m pytest tests/unit/test_sync_mirrors.py::TestGenerationFunctions::test_copilot_agent_tools_and_delegation_match_metadata -q`
- `ruff`: `python -m ruff check tests/unit/test_sync_mirrors.py`

## Result

The public Copilot agent generator now has regression coverage for tool/delegation parity across all first-class agents.