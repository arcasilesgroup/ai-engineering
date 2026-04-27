---
name: guide
description: Use to navigate the framework — architecture tour, find a topic across skills/ADRs/manifest, or do decision archaeology on a past choice. Subcommands tour | find <topic> | history <decision-id>. Trigger for "show me the architecture", "where is X documented", "why did we decide Y", "walk me through the framework".
effort: high
tier: core
capabilities: [tool_use]
---

# /ai-guide

Onboarding and navigation. Three subcommands — `tour` for architecture
overview, `find` for cross-corpus search, `history` for decision
archaeology.

## When to use

- New contributor needs to understand the framework — "tour"
- "Where is X documented?" — `find <topic>`
- "Why did we decide Y?" — `history <decision-id>`
- Audit prep — re-read relevant ADRs and decisions

## Subcommands

### `tour`

Walks the architecture from the high-level diagrams in `docs/adr/` and
`README.md`. Output:

1. The 10 articles of the constitution and what they govern.
2. ADR-by-ADR walkthrough (hexagonal, dual-plane, MCP-first, etc.) with
   one-paragraph summaries and links to source.
3. The skills + agents catalog, grouped by lifecycle phase.
4. The Layer 1 / Layer 2 / Layer 3 subscription model.
5. Where to file a question (CONTRIBUTING, GitHub Discussions).

### `find <topic>`

Cross-corpus search across:

- `skills/catalog/<name>/SKILL.md` — slash-command surface
- `docs/adr/*.md` — accepted decisions
- `.ai-engineering/manifest.toml` — profile and overrides
- `CONSTITUTION.md` — articles
- `LESSONS.md` — historical reviewer feedback

Returns a ranked list with snippet, source file, and the suggested next
skill (`/ai-explain` for deeper unpacking).

### `history <decision-id>`

Walks the decision archaeology for a specific topic:

1. **Decision-store entries** — every `decision-store.json` entry
   matching the id (risk acceptance, gate exception, scope change).
2. **Git log** — commits referencing the id.
3. **ADR linkage** — if the decision originated from an ADR, surface it.
4. **Spec linkage** — the spec that owns this decision.
5. **Outcome** — was the TTL renewed, expired, or remediated.

Output is a chronological narrative, not a raw dump.

## Process

1. **Resolve subcommand** — `tour | find | history`. Reject unknown
   verbs with usage hint.
2. **Index sources** on first invocation; cache for the session.
3. **Render output** as a navigable summary, not a wall of text.
4. **Cross-link to `/ai-explain`** when the user wants engineering-grade
   detail rather than a tour.
5. **Emit telemetry** — `guide.tour_rendered`, `guide.find_query`,
   `guide.history_walked`.

## Hard rules

- NEVER fabricate ADRs or decisions — only surface what's on disk.
- NEVER summarize a decision without linking the source file.
- `find` must search ALL listed corpora, not just `skills/`.
- `history` must reconstruct chronology from audit log, not memory.

## Common mistakes

- Treating `tour` as a marketing pitch instead of an architecture map
- `find` returning hits only from skills, missing ADRs and manifest
- `history` skipping git log — decisions live in commits too
- Linking to outdated ADR versions instead of the latest accepted state
- Not suggesting `/ai-explain` for users who want deeper unpacking
