# Verify: HX-03 T-4.1 Instruction And Specialist Validator Parity

## Commands

```bash
uv run pytest tests/unit/test_validator.py -k 'GeneratedInstructionsMirror'
uv run pytest tests/unit/config/test_mirror_inventory.py tests/unit/test_sync_mirrors.py -k 'provider_maps_match_current_install_contract or validator_pairs_and_sync_roots_follow_inventory_contract or public_inventory_excludes_internal_and_manual_families'
uv run pytest tests/unit/config/test_mirror_inventory.py tests/unit/test_sync_mirrors.py tests/unit/test_validator.py -k 'mirror_sync or mirror_inventory or GeneratedInstructionsMirror or ClaudeSpecialistAgentsMirror'
uv run pytest tests/unit/test_validator.py -k 'ClaudeSpecialistAgentsMirror or ClaudeAgentsMirror'
uv run ai-eng validate -c mirror-sync
```

## Results

- The generated-instruction validator regressions passed, including the manual-file exclusion case and the desync case.
- The shared mirror-inventory contract tests passed after adding the generated/manual instruction split.
- The broader mirror-focused bundle passed (`15 passed`).
- The Claude specialist-agent validator regressions passed after the validator switched from raw byte-parity to wrapper-contract validation.
- `uv run ai-eng validate -c mirror-sync` no longer reports the prior instruction-root or Claude specialist false positives; the remaining repo-level failure is the pre-existing governance-template `README.md` desync.

## Conclusion

- `HX-03` Phase 4.1 now covers generated Copilot instruction parity and Claude specialist wrapper parity with executable validator coverage.
- The remaining Phase 4 queue narrows to the governance-template `README.md` desync and the negative-validation work still called for by `T-4.2`.