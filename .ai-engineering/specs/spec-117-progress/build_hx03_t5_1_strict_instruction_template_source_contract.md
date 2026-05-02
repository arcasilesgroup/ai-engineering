# Build HX-03 T-5.1 Strict Instruction Template Source Contract

## Scope

- Continue the `HX-03 T-5.1` cutover by removing the remaining installer-side fallback that derived root instruction template counterparts from the legacy provider file map.

## Changes

- Removed the `_DEFAULT_ROOT_TEMPLATE_PATHS` compatibility fallback from `ai_engineering.installer.templates.resolve_instruction_template_sources(...)`.
- Hardened `resolve_instruction_template_sources(...)` so it now requires manifest `ownership.root_entry_points[*].sync.template_path` metadata for every governed root instruction destination.
- Added direct installer regression coverage proving manifest-declared template paths are used and missing root-entry metadata now fails fast.
- Updated the neighboring validator source-repo test so template counterpart discovery is exercised through explicit governed root-entry metadata instead of the old manifest-less fallback path.