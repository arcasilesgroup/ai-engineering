# Verify: HX-03 T-2 Mirror Inventory Reference Model

## Commands

```bash
uv run pytest tests/unit/config/test_mirror_inventory.py -q
uv run pytest tests/unit/test_sync_mirrors.py tests/unit/config/test_mirror_inventory.py -q
uv run pytest tests/unit/test_validator.py -k 'MirrorSync or CopilotSkillsMirror or ClaudeSkillsMirror or ClaudeAgentsMirror or CodexSkillsMirror or CodexAgentsMirror or CopilotAgentsMirror' -q
uv run pytest tests/unit/test_installer.py -k 'provider_tree_maps or instructions or common_files' -q
uv run ai-eng sync
uv run ai-eng sync --check
```

## Result

- All focused mirror-inventory, sync, validator mirror-sync, and installer mapping checks passed.
- `uv run ai-eng sync --check` returned `PASS` after the generated mirrors were regenerated with the new provenance markers.
- Editor diagnostics reported no errors in the touched source and test files.

## Coverage Notes

- The slice now has executable coverage for mirror-family inventory completeness, public/internal filtering, shared provider maps, validator pair roots, and generated provenance/edit-policy metadata.
- Remaining HX-03 work is downstream of this shared contract rather than blocked by it.