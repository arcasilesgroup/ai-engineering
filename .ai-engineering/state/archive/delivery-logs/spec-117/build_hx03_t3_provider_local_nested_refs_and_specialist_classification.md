# Build: HX-03 T-3 Provider-Local Nested Refs And Specialist Classification

## Scope

- Remove provider-local leaks caused by nested `.claude/skills/ai-.../...` subpaths that were not rewritten by `translate_refs`.
- Stop treating specialist agent mirrors as unclassified byte-for-byte copies by stamping them with the internal `specialist-agents` family provenance.

## Changes

- Extended `translate_refs` in `scripts/sync_command_mirrors.py` to rewrite nested skill subpaths such as handlers, scripts, and resources under canonical `ai-*` skill directories into the target provider surface.
- Added focused unit coverage proving that generated Copilot skill mirrors and generated Codex agent mirrors no longer leak nested canonical handler paths.
- Added `generate_specialist_agent(...)` so specialist agent mirrors carry shared provenance markers and the explicit `mirror_family: specialist-agents` classification instead of remaining opaque copies.
- Regenerated derived mirrors with `uv run ai-eng sync` after both generator changes landed.

## Remaining Phase 3 Gaps

- Mixed manual/generated provenance inside `.github/instructions/` remains open.
- Provider-incompatible public files that still mention Claude-only operational surfaces outside the nested-path rewrite case remain open.