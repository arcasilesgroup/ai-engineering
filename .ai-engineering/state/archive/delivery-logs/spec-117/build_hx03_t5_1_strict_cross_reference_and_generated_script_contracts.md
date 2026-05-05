# Build HX-03 T-5.1 Strict Cross Reference And Generated Script Contracts

## Scope

- Start the `HX-03 T-5.1` cutover by removing the last manifest-less cross-reference fallback and locking the generated `ai-create` provider scripts to provider-local skill roots with direct sync tests.

## Changes

- Removed the historical `_FALLBACK_CROSS_REFERENCE_FILES` path from `scripts/sync_command_mirrors.py`.
- Hardened `_resolve_cross_reference_files(...)` so the source repo must provide `.ai-engineering/manifest.yml` instead of silently reusing the legacy hardcoded root surface list.
- Added a focused regression proving missing-manifest cross-reference resolution now fails with `FileNotFoundError`.
- Added a direct generated-surface regression proving the Codex, Gemini, and Copilot `ai-create/scripts/scaffold-skill.sh` mirrors use provider-local `SKILL_DIR` roots and no longer fall back to `.claude/skills/...`.