# Build HX-03 T-4.2 Generated Mirror Provenance Validation

## Scope

- Extend `mirror_sync` so generated mirror surfaces fail when provenance frontmatter drifts even if the repo and template copies still match byte-for-byte.

## Changes

- Added generated provenance validation for Codex, Gemini, and Copilot skill and agent mirrors plus provider-local internal specialist mirrors.
- Derived expected `canonical_source` values from each governed mirror family instead of trusting pair parity alone.
- Restricted Codex and Gemini public-agent provenance scans to `ai-*.md` so provider-local `internal/` specialists remain classified under `specialist-agents`.
- Normalized Copilot public-agent provenance derivation so filenames that already carry `ai-` map back to the correct Claude canonical source.
- Aligned `.ai-engineering/README.md` with the installer template to clear the last pre-existing governance mirror desync before re-running the real repo validator.