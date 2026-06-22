# Design Intent — spec-171 Mintlify Documentation Portal

Auto-routed from /ai-plan (matched keywords: page, ui). Scope: visual and
information-architecture direction for `docs-portal/`. Theme final only
after operator sign-off at M0 (D-171-08).

## Aesthetic direction

- **Identity**: Arcasiles dark-IDE palette. Canonical color values live in
  the brand assets at `docs/design.pen` (readable only via Pencil MCP
  tools); M0 task T-1.2 extracts them and maps to `docs.json`
  `colors.primary` / `colors.light` / `colors.dark`. Until extraction,
  scaffold uses neutral placeholders — never invented brand colors.
- **Typography**: Mintlify defaults (no custom font loading at v1 — KISS).
  Code samples carry the same weight as prose; this is a CLI/agent product.
- **Tone**: engineer-grade, terse, zero emoji, `{ai} engineering` in prose,
  `ai-engineering` for identifiers (brand-voice contract).

## Information architecture

Two tabs:

1. **Documentation** — Get Started (installation, quickstart,
   governed-flow), Concepts (constitution, skills-and-agents, hooks,
   quality-gates, persistence), Guides (ide-setup, risk-acceptance,
   upgrading), Changelog (link-only).
2. **Reference** — generated: skills (54), agents (9), CLI, environment
   tunables. CardGroup index pages on top of per-item pages for scan-first
   navigation and deep links.

Landing `index.mdx`: one-paragraph value statement, the stat line
(54 skills · 9 agents · 6 surfaces · 1 governed flow), CTA cards to
quickstart and the governed flow.

## Component usage (Mintlify MDX)

- `CodeGroup` for install variants (uv / pipx / pip) — mirrors README.
- `Steps` for quickstart sequence.
- `Tabs` for per-IDE setup (Claude Code / Copilot / Codex / Antigravity /
  OpenCode / Cursor).
- Mermaid for the canonical chain and the six-layer module map.
- `Card`/`CardGroup` for landing CTAs and reference indexes.

## Constraints

- English only; no PII, operator names, or machine paths.
- Generated pages carry the GENERATED header; visual templates live in the
  generator, not hand-edited MDX.
