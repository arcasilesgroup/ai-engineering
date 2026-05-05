# Build: HX-03 T-3 Provider-Facing Catalog Rendering

## Scope

- Remove the last hard-coded provider-facing skill catalog drift in `GEMINI.md` and `.gemini/GEMINI.md`.
- Render the Gemini root-overlay skill groups and effort table from the manifest-backed public mirror contract instead of static template prose.
- Preserve provider compatibility filtering so Claude-only skills stay out of Gemini while provider-visible skills from newer manifest types stay represented.

## Changes

- Added manifest-backed Gemini catalog rendering helpers in `scripts/sync_command_mirrors.py`.
- `render_gemini_md_placeholders()` now computes:
  - filtered Gemini skill count
  - grouped skill catalog lines from `skills.registry` type metadata
  - effort-table rows from filtered skill frontmatter
- Replaced the hard-coded skill-group and effort-table blocks in `src/ai_engineering/templates/project/GEMINI.md` with render placeholders.
- Added regressions in `tests/unit/test_sync_mirrors.py` covering both the pure renderer output and the generated root/overlay files on disk.

## Outcome

- Gemini provider-facing catalogs now include the full filtered public surface, including `design`, `animation`, `canvas`, `research`, and other manifest-backed skills that the static template previously omitted.
- Claude-only `analyze-permissions` is no longer listed in Gemini grouped views or effort rows.
- The Gemini root overlay and `.gemini/GEMINI.md` are now contract-driven rather than manually curated snapshots.