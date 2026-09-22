# THIRD-PARTY-NOTICES.md

ai-engineering integrates the methods of third-party projects verbatim (§11.1).
Their licenses and provenance are listed in NOTICE.md; the content itself travels
inside `skills/ai-*/` with each source preserved byte-for-byte.

Bundled third-party content:
- LeafyGreen UI (mongodb/leafygreen-ui) — Apache-2.0 — © MongoDB, Inc. — the brand
  palette, copied verbatim into `brand/tokens.json`. Trademark rights are not granted
  by Apache-2.0 and are not claimed: no MongoDB logo, wordmark or leaf glyph is used.
- cloudflare/security-audit-skill — MIT — © Cloudflare
- unlazy (Leonxlnx) — MIT
- wayfinder (mattpocock) — MIT
- writing-agent-behavior (braintrustdata/agentbehavior) — Apache-2.0 — © Braintrust + Basis
- Loop-Engineering, design-orchestrator (claude-design-skills), graph-engineering,
  ai-design-audit — integrated with attribution; license issues open (H4)

Not bundled (offered as install commands only, §14.1): caveman, engram,
impeccable, hallmark, shadcn, astryx, emil-design-eng, ui-ux-pro-max, tasteskill,
tavily, exa, context7, mantis, skill-map.

Runtime dependencies: @clack/prompts (MIT), fast-wrap-ansi (MIT).
Dev dependencies: @changesets/changelog-github (MIT), @changesets/cli (MIT),
@hughescr/stryker-bun-runner (Apache-2.0), @stryker-mutator/core (Apache-2.0),
@types/bun (MIT), oxlint (MIT), oxlint-tsgolint (MIT).
