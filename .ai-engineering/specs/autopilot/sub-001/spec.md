---
id: sub-001
parent: spec-088
title: "Manifest Dedup"
status: planning
files:
  - .ai-engineering/manifest.yml
  - src/ai_engineering/templates/.ai-engineering/manifest.yml
depends_on: []
---

# Sub-Spec 001: Manifest Dedup

## Scope

Remove the dead nested `providers.ai_providers` from both manifest files (root + template). Only the top-level `ai_providers` key is read by code (13 references, confirmed by exhaustive grep). The nested version under `providers:` has zero consumers -- Pydantic `ProvidersConfig` doesn't even define the field. Decision D-088-01.

## Exploration
[EMPTY -- populated by Phase 2]
