# THIRD-PARTY-NOTICES.md

ai-engineering integrates the methods of third-party projects verbatim (§11.1).
Their licenses and provenance are listed in NOTICE.md; the content itself travels
inside `skills/ai-*/` with each source preserved byte-for-byte.

Bundled third-party content:
- cloudflare/security-audit-skill — MIT — © Cloudflare
- unlazy (Leonxlnx) — MIT
- wayfinder (mattpocock) — MIT
- rtk skill (autometa/Hermes Agent) — MIT
- writing-agent-behavior (braintrustdata/agentbehavior) — Apache-2.0 — © Braintrust + Basis
- Loop-Engineering, design-orchestrator (claude-design-skills), graph-engineering,
  ai-design-audit — integrated with attribution; license issues open (H4)

Not bundled (offered as install commands only, §14.1): rtk binary, caveman, engram,
impeccable, hallmark, shadcn, astryx, emil-design-eng, ui-ux-pro-max, tasteskill,
tavily, exa, context7, mantis, skill-map.

Runtime dependencies: @clack/prompts (MIT), @bomb.sh/args (MIT), @bomb.sh/tab (MIT).
Dev dependencies: archunit (MIT), dependency-cruiser (MIT), oxlint (MIT),
typescript (Apache-2.0), @types/bun (MIT).
