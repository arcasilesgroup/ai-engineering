# Build HX-03 T-5.1 Strict Root Entry Ownership Contract

## Scope

- Continue the `HX-03 T-5.1` cutover by removing the last ownership-map fallback that still synthesized governed root entry points without explicit manifest metadata.

## Changes

- Updated `src/ai_engineering/state/defaults.py` so governed root entry point ownership rules are emitted only from explicit `ownership.root_entry_points` metadata.
- Removed the historical behavior that silently added `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, and `.github/copilot-instructions.md` as framework-managed ownership entries when no manifest metadata was provided.
- Added state-level regression coverage proving `default_ownership_map()` no longer invents governed root entry rules without metadata and that the committed ownership snapshot is compared against the manifest-driven contract.
- Added updater coverage proving `_merge_missing_ownership_rules(...)` no longer injects synthetic root entry ownership rules when `root_entry_points` is absent.