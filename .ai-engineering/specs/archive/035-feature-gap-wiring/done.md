---
spec: "035"
slug: "feature-gap-wiring"
completed: "2026-03-04"
---

# Done — Extend feature-gap with wiring detection

## Summary

Extended the `feature-gap` skill to detect wiring gaps — code that is implemented but not connected to any entry point, route, or consumer. Updated the scan agent thresholds to reflect wiring coverage.

Delivered:

1. **Feature-gap skill update** — metadata (description, tags), purpose section covering spec-vs-code AND implementation-vs-integration gaps, procedure step 5.5 (wiring gap detection with 6 categories), Wiring Matrix table in output section.
2. **Scan agent update** — mode table description includes wiring gaps, threshold table includes ">5 unwired exports" as critical threshold.
3. **Template + mirror sync** — all platform adaptors synchronized for updated feature-gap skill.

## Verification

- `ai-eng validate` — all categories pass.
- `ruff check src/ tests/` — clean.
- feature-gap SKILL.md metadata includes `wiring` and `dead-code-functional` tags.
- Procedure step 5.5 covers: exported but never imported, endpoints not registered, handlers not subscribed, modules without importers, CLI commands not registered.
- Output section includes Wiring Matrix table.
- Scan agent mode table and threshold table updated.

## Deferred

None — self-contained enhancement.
