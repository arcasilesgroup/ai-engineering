# Verify: HX-03 T-3 Provider-Local Nested Refs And Specialist Classification

## Commands

```bash
uv run pytest tests/unit/test_sync_mirrors.py -k 'generate_copilot_skill_rewrites_nested_handler_refs or generate_codex_agent_rewrites_nested_skill_handler_refs' -q
uv run pytest tests/unit/test_sync_mirrors.py -k 'generate_specialist_agent_includes_internal_family_provenance' -q
uv run pytest tests/unit/test_sync_mirrors.py -q
uv run ai-eng sync
uv run ai-eng sync --check
```

## Result

- The focused nested-ref leak tests passed after `translate_refs` learned to rewrite nested canonical skill subpaths.
- The focused specialist-agent provenance test passed after the dedicated generator replaced the old byte-for-byte copy path.
- The full sync-script test suite passed and `uv run ai-eng sync --check` returned `PASS` after regenerating the affected mirrors.

## Coverage Notes

- This subslice verifies both provider-local nested-handler rewrites and explicit internal classification for specialist mirrors.
- Broader Phase 3 compatibility filtering is still pending outside this local repair.