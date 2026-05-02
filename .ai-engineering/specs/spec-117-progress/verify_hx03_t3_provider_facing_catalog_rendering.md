# Verify: HX-03 T-3 Provider-Facing Catalog Rendering

## Commands

```bash
uv run pytest tests/unit/test_sync_mirrors.py -k 'render_gemini_md_uses_filtered_skill_count or write_gemini_md_renders_filtered_skill_catalog_and_effort_rows'
uv run ai-eng sync
uv run pytest tests/unit/test_sync_mirrors.py -k 'write_gemini_md_renders_filtered_skill_catalog_and_effort_rows or generated_gemini_surfaces_use_filtered_skill_catalog'
uv run ai-eng sync --check
uv run pytest tests/unit/config/test_mirror_inventory.py tests/unit/test_sync_mirrors.py tests/unit/test_constitution_skill_paths.py
uv run ai-eng validate -c cross-reference
uv run ai-eng validate -c file-existence
```

## Results

- The narrow Gemini rendering regressions passed after the catalog became contract-driven.
- `uv run ai-eng sync` regenerated the root and `.gemini/` overlays successfully.
- The generated-file regression passed, confirming `GEMINI.md` and `.gemini/GEMINI.md` match and no longer list Claude-only `analyze-permissions` while now including the `Design` and `Writing` groups.
- `uv run ai-eng sync --check` finished clean.
- The broader mirror suite passed (`115 passed`).
- Cross-reference and file-existence validation both passed after the new progress artifacts were linked from the work plane.

## Conclusion

- The provider-facing Gemini catalog is now derived from the filtered mirror contract instead of a stale hand-maintained snapshot.
- `HX-03` Phase 3 is green across focused rendering tests, full mirror coverage, and structural validators.