---
"ai-engineering": major
---

The `ai-eng findings check` verb is removed from the public CLI. It reads the review rounds of one external pipeline, annotates findings and never gates, and nothing shipped to a governed repository (no hook, CI template, skill or agent) ever ran it: it was a maintainer instrument for measuring signal precision on this repository's own reviews. It now lives at `scripts/findings-check.ts` with its tests, run as `bun scripts/findings-check.ts <rounds.json|->` (the `check` word is gone). The package description now reads "Guardrails for the AI coding agents you already run", the same sentence as the README hero.
