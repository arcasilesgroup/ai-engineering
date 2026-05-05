# Verify: HX-03 T-3 Specialist Internal Namespace Cutover

## Commands

```bash
uv run pytest tests/unit/config/test_mirror_inventory.py tests/unit/test_sync_mirrors.py -k 'provider_maps_match_current_install_contract or translate_specialist_agent_path'
uv run ai-eng sync
uv run pytest tests/unit/test_sync_mirrors.py -k 'SpecialistInternalNamespaces or generate_specialist_agent_includes_internal_family_provenance'
uv run pytest tests/unit/test_constitution_skill_paths.py -k verifier_architecture
uv run pytest tests/unit/config/test_mirror_inventory.py tests/unit/test_sync_mirrors.py tests/unit/test_constitution_skill_paths.py
uv run ai-eng sync --check
python -m json.tool .ai-engineering/specs/task-ledger.json >/dev/null
uv run ai-eng validate -c cross-reference
uv run ai-eng validate -c file-existence
```

## Results

- The narrow translation and inventory-target regressions passed (`4 passed`).
- `uv run ai-eng sync` regenerated the provider mirrors successfully and removed the old top-level specialist paths as orphans.
- The focused generated-surface regressions passed (`3 passed`) and the constitution-path compatibility assertions for the relocated specialist mirror passed (`8 passed`).
- The broader mirror contract bundle passed (`113 passed`).
- `uv run ai-eng sync --check` finished clean with no drift.
- The recorded work-plane artifacts stayed coherent: `task-ledger.json` parsed successfully and the validation CLI passed cross-reference plus file-existence checks after the new progress files were linked from the ledger.

## Conclusion

- The provider-local specialist namespace cutover is green.
- Provider-facing review and verify surfaces now resolve internal specialist paths consistently across live mirrors and install templates.