# Build HX-03 T-5.1 Strict Instruction Destination Metadata Contract

## Scope

- Continue the `HX-03 T-5.1` cutover by removing the remaining validator and installer tolerance for governed root instruction destinations that were implied by provider maps instead of explicit manifest ownership metadata.

## Changes

- Hardened `ai_engineering.installer.templates.resolve_instruction_file_destinations(...)` so enabled governed root instruction destinations now require explicit `ownership.root_entry_points` metadata instead of being reconstructed from the legacy provider map alone.
- Hardened `ai_engineering.validator._shared._resolve_instruction_files(...)` so manifest-less validator runs no longer invent `CLAUDE.md`, `AGENTS.md`, and Copilot instruction surfaces from the historical fallback set.
- Added a direct installer regression proving destination resolution now fails fast without root-entry metadata.
- Added a validator provider-resolution regression proving manifest presence without `root_entry_points` is no longer enough for governed instruction discovery.