# Build: HX-03 T-4.1 Instruction And Specialist Validator Parity

## Scope

- Split generated and manual Copilot instruction surfaces in the shared mirror inventory.
- Rewire `mirror_sync` so generated `.github/instructions/*.instructions.md` files are parity-validated against the installer template while manual instruction files remain excluded from that generated check.
- Align Claude template-agent validation with the real specialist-agent contract: first-class `ai-*` agents stay byte-for-byte, while specialist wrappers are validated as generated outputs with provenance metadata.

## Changes

- Added a `generated-instructions` mirror family and a shared `get_manual_instruction_files()` helper in `src/ai_engineering/config/mirror_inventory.py`.
- Updated `scripts/sync_command_mirrors.py` to consume the shared manual instruction filename list instead of duplicating it locally.
- Extended `src/ai_engineering/validator/_shared.py` and `src/ai_engineering/validator/categories/mirror_sync.py` so:
  - generated Copilot instruction mirrors are parity-checked against `src/ai_engineering/templates/project/instructions`
  - manual instruction files are excluded from that generated parity pass
  - Claude specialist agents are validated against the generated wrapper contract instead of being treated as raw byte-for-byte copies
- Added regression coverage in `tests/unit/config/test_mirror_inventory.py` and `tests/unit/test_validator.py` for the new inventory split, generated-instruction parity, manual exclusion, and Claude specialist wrapper parity.

## Outcome

- The shared mirror model no longer misclassifies generated Copilot instruction files as manual.
- `mirror_sync` now proves generated instruction parity and Claude specialist wrapper parity without importing the top-level sync script at CLI runtime.
- The repo-level `mirror_sync` CLI is reduced to a remaining governance-template README desync rather than failing on instruction-root blindness or specialist-agent false positives.