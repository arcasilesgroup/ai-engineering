# THIRD-PARTY-NOTICES.md

ai-engineering integrates the methods of third-party projects verbatim (§11.1).
Their licenses and provenance are listed in NOTICE.md; the content itself travels
inside `skills/ai-*/` with each source preserved byte-for-byte.

Bundled third-party content:
- LeafyGreen UI (mongodb/leafygreen-ui) — Apache-2.0 — © MongoDB, Inc. — the brand
  palette, copied verbatim into `brand/tokens.json`. Trademark rights are not granted
  by Apache-2.0 and are not claimed: no MongoDB logo, wordmark or leaf glyph is used.
- obra/superpowers (brainstorming, in `ai-brainstorm`) — MIT
- cloudflare/security-audit-skill (`ai-security`) — MIT — © Cloudflare
- ayghri/i-have-adhd (the voice reference in `ai-write`) — MIT
- agents.md convention (`ai-agents-md`) — MIT
- writing-agent-behavior (braintrustdata/agentbehavior, `ai-writing-behavior`) — Apache-2.0
  — © Braintrust + Basis
- graph-engineering (`ai-verify`), ai-audit-design — integrated with attribution; license
  issues open (H4)
- headstart (ai-architect) — MIT declared, but the cited upstream does not resolve to
  this content; redistribution rights unresolved (H4)
- agit-secret-guard (the spoken-secret classifier in `src/guards/spoken-secret.ts`) —
  supplied locally, license unknown; redistribution rights unresolved (H4)

Every bundled item above except the brand palette (which NOTICE.md treats separately,
under "The brand") has a row in NOTICE.md's attribution table, and its Redistribution
column records which rows are verified; publication is refused while any row is
unresolved (`scripts/release-policy.ts`).

No longer bundled: unlazy (Leonxlnx), wayfinder (mattpocock), Loop-Engineering and
design-orchestrator (claude-design-skills) shipped only inside the `ai-proof`, `ai-plan`,
`ai-goal` and `ai-design` skills, which were removed (#732); nothing from them remains in
`skills/`, `agents/`, `templates/` or `src/`.

Not bundled (offered as install commands only, §14.1): caveman, engram,
impeccable, hallmark, shadcn, astryx, emil-design-eng, ui-ux-pro-max, tasteskill,
tavily, exa, context7, mantis, skill-map.

Runtime dependencies: @clack/prompts (MIT), fast-wrap-ansi (MIT).
Dev dependencies: @changesets/changelog-github (MIT), @changesets/cli (MIT),
@hughescr/stryker-bun-runner (Apache-2.0), @stryker-mutator/core (Apache-2.0),
@types/bun (MIT), oxlint (MIT), oxlint-tsgolint (MIT).
