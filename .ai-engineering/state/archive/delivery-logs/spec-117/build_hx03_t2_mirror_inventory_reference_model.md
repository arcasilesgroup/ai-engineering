# Build: HX-03 T-2 Mirror Inventory Reference Model

## Scope

- Establish one shared mirror-family inventory for sync, validator, and installer consumers.
- Replace divergent hard-coded root maps with the shared contract.
- Add explicit provenance and edit-policy markers to generated provider-local mirrors.

## Changes

- Added `src/ai_engineering/config/mirror_inventory.py` as the shared reference model for mirror families, public/internal classification, provider file/tree maps, validator pair roots, and generated provenance fields.
- Rewired `scripts/sync_command_mirrors.py` to consume the shared family inventory for provider-local roots and to stamp generated mirror frontmatter with `mirror_family`, `generated_by`, `canonical_source`, and `edit_policy`.
- Rewired `src/ai_engineering/validator/_shared.py` and `src/ai_engineering/installer/templates.py` to consume the same shared path contract instead of maintaining separate inventories.
- Added `tests/unit/config/test_mirror_inventory.py` and extended `tests/unit/test_sync_mirrors.py` to lock the shared inventory and provenance semantics.
- Regenerated derived mirror surfaces with `uv run ai-eng sync` so the repository matches the new generated contract.

## Notes

- Manual instruction files remain classified as `edit_policy: manual` and stay outside the public generated family set.
- Public generated families now expose explicit non-editability metadata through frontmatter rather than relying on implicit convention.