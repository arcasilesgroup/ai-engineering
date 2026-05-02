# Build HX-03 T-5.1 Strict Updater Manifest Contract

## Scope

- Continue the `HX-03 T-5.1` cutover by removing the updater-side fallback that still treated missing manifest state as "all providers active".

## Changes

- Updated `src/ai_engineering/updater/service.py` so `_initialize_update_context(...)` now requires the governed `.ai-engineering/manifest.yml` contract before resolving active providers.
- Removed the historical updater behavior that silently treated a missing manifest as `providers=None` and therefore skipped disabled-provider orphan detection.
- Added focused unit coverage proving updater context initialization now fails fast with `FileNotFoundError` when the manifest contract is absent.
- Updated the updater provider-filtering regression suite so missing-manifest runs now assert the new fail-fast contract instead of the retired "all providers active" fallback.
- Preserved the strict manifest-driven ownership merge path introduced in the previous T-5.1 slice.