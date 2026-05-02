# Verify HX-03 T-5.1 Strict Cross Reference And Generated Script Contracts

## Ordered Verification

1. `uv run pytest tests/unit/test_sync_mirrors.py -k 'generated_ai_create_scripts_use_provider_local_skill_roots or CrossReferenceResolution or check_mode_returns_zero'`
   - `PASS`
2. `uv run ai-eng sync --check`
   - `PASS`

## Key Signals

- Cross-reference resolution is now manifest-strict: the focused sync tests prove the helper no longer falls back to the legacy root-file list when `.ai-engineering/manifest.yml` is absent.
- The generated provider `ai-create` scripts are now pinned by executable regression coverage to provider-local `SKILL_DIR` roots for Codex, Gemini, and Copilot.
- The real repository still passes `sync --check`, so the stricter manifest requirement did not break the governed source repo workflow.