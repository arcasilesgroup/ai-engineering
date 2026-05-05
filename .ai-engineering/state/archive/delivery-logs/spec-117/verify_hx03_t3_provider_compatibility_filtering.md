# Verify: HX-03 T-3 Provider Compatibility Filtering

## Commands

```bash
uv run pytest tests/unit/test_sync_mirrors.py -k 'codex_incompatible_when_false or gemini_incompatible_when_false or render_gemini_md_uses_filtered_skill_count' -q
uv run ai-eng sync
uv run pytest tests/unit/test_sync_mirrors.py -q
uv run ai-eng sync --check
```

## Result

- The focused provider-compatibility helper tests passed for both Codex and Gemini opt-outs.
- The Gemini count regression passed after the renderer switched to the filtered provider-compatible skill set.
- `uv run ai-eng sync` removed the stale Codex and Gemini `ai-analyze-permissions` mirrors and regenerated the provider surfaces cleanly.
- The full sync-script suite passed and `uv run ai-eng sync --check` returned `PASS` after regeneration.

## Coverage Notes

- This subslice verifies explicit provider compatibility filtering for public skills plus Gemini-facing count alignment.
- Root overlay and broader catalog filtering remain open for later `HX-03` work.
