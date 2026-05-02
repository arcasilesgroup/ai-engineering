# Build: HX-03 T-3 Provider Compatibility Filtering

## Scope

- Stop publishing Claude-only public skills into non-Claude mirrors when the compatibility boundary is explicit in frontmatter.
- Make Gemini-facing skill counts derive from the filtered public surface rather than the raw canonical skill inventory.

## Changes

- Added a shared `is_provider_compatible(...)` helper in `scripts/sync_command_mirrors.py` and kept `is_copilot_compatible(...)` as the Copilot-specific wrapper.
- Filtered Codex and Gemini skill generation through the shared provider compatibility contract instead of generating every canonical skill unconditionally.
- Updated `render_gemini_md_placeholders(...)` so Gemini skill totals reflect only Gemini-compatible public skills.
- Marked `ai-analyze-permissions` as `codex_compatible: false` and `gemini_compatible: false` in addition to its existing Copilot opt-out, making the Claude-only boundary explicit.
- Expanded focused sync tests to cover provider-specific compatibility flags, Gemini count filtering, and the absence of `ai-analyze-permissions` from Codex and Gemini mirrors.
- Regenerated mirrors with `uv run ai-eng sync` after the generator and canonical skill metadata changes.

## Remaining Phase 3 Gaps

- Provider-facing root overlays and catalogs still need their broader filtered-count rendering pass.
- Some surviving `.claude` mentions in non-Claude mirrors appear to be intentional multi-platform audit content and still need explicit triage before further filtering.
