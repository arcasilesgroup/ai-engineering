---
title: ai-engineering
description: Multi-IDE AI agentic governance framework with subscription piggyback, federated plugins, and dual-plane security.
template: splash
hero:
  tagline: SOLID/KISS/DRY/TDD discipline plus regulated-industry compliance — without ever asking for an API key.
  actions:
    - text: 5-minute on-ramp
      link: /quickstart/
      icon: rocket
      variant: primary
    - text: Read the architecture
      link: /architecture/overview/
      icon: open-book
    - text: Browse the skills catalog
      link: /skills/
      icon: list-format
---

`ai-engineering` is a **governance + automation framework** for teams who
build software with AI coding assistants — Claude Code, GitHub Copilot,
Codex CLI, Cursor, Gemini CLI, Antigravity, Cline. It piggybacks on the
IDE subscription you already pay for, refuses to ship unsigned plugins,
and pushes every LLM-proposed action through a deterministic guard plane
before it ever runs.

## Why does this exist

Building software with AI agents at the speed of 2026 is easy. Doing it
**correctly** — with auditable governance, deterministic gates, supply
chain integrity, and regulated-industry compliance — is not. Existing
frameworks either:

- Force you to bring API keys (duplicate billing).
- Distribute plugins with weak supply chain protection (Shai-Hulud
  taught us why that ends badly).
- Treat the LLM as a monolith (Excessive Agency, Prompt Injection
  vulnerabilities).
- Ignore observability until you're already debugging in production.

`ai-engineering` v3 fixes those four problems.

## What you get out of the box

### Subscription piggyback (no API keys)

Three execution layers:

1. **Deterministic** (no LLM): install, plugin verification,
   release-gate, board sync, governance audit, risk acceptance,
   migration, mirror generation. ~70% of the value, zero token cost.
2. **IDE-host delegation**: skills like `/ai-specify`, `/ai-implement`,
   `/ai-debug` invoke the user's IDE in headless mode (`claude -p`,
   `cursor-agent -p`, `codex exec`, `gemini -p`). The IDE's subscription
   pays for inference.
3. **BYOK opt-in**: only when no IDE host is present (CI flows). Uses
   an isolated LiteLLM bridge — or, for regulated tier, TrueFoundry.

See [ADR-0005](/adr/) for the rationale.

### Dual-Plane Architecture

Every action proposed by the LLM passes through a Deterministic Plane
**before** execution:

- **Input Guard** — regex + lightweight model scan for PII and known
  exploitation patterns.
- **Identity Broker** — short-lived OBO tokens with minimum scopes.
- **Policy Engine** (OPA / Rego) — declarative rules evaluated < 1 ms.
- **Immutable Audit Log** — hash-chained, SOC2/HIPAA/DORA ready.

### Single Source of Truth + IDE mirrors

Skills live ONCE in `skills/catalog/<name>/SKILL.md`. The
`ai-eng sync-mirrors` command regenerates IDE-specific files for Claude
Code, Cursor, Codex CLI, GitHub Copilot, Gemini CLI, and Antigravity —
eliminating ~190 mirror files across 6 IDEs.

### Federated-curated plugin marketplace

Three-tier model:

- **OFFICIAL** (`@ai-engineering/*`) — team-signed.
- **VERIFIED** (`@ai-engineering-verified/*`) — community-approved with
  human review + 30-day track record.
- **COMMUNITY** — any GitHub repo with the `ai-engineering-plugin`
  topic; cryptographically attested via Sigstore keyless OIDC + SLSA
  v1.0 + CycloneDX SBOM + OpenSSF Scorecard ≥ 7.

### Regulated industry profiles

`ai-eng install --profile banking | healthcare | fintech | airgapped`
activates four extra skills: `audit-trail`, `incident-respond`,
`compliance-report`, `data-classification`. LiteLLM is replaced by
TrueFoundry (in-cluster, zero-external-dependency PII redaction). DORA,
SOC2, HIPAA, PCI-DSS mappings included.

## Status

This is an early-alpha redesign — version `3.0.0-alpha.0`. Phases 0
through 8 have landed (foundation, dual-plane scaffolding, domain core,
application layer, MCP server, LiteLLM bridge, plugin system, full skill
catalog). Phase 9 (TUI) is optional and Phase 10 (this docs site) is in
progress. See the [master plan](/architecture/master-plan/) for the
phase-level roadmap.

## Where to go next

- **[5-minute on-ramp →](/quickstart/)** — your first project end-to-end.
- **[Architecture overview →](/architecture/overview/)** — diagrams of
  the dual-plane model, the hexagonal core, and the mirror pipeline.
- **[Master plan →](/architecture/master-plan/)** — phase status and
  critical path.
- **[Architecture decisions →](/adr/)** — the ten ADRs that ground
  every framework-level choice.
- **[Skills catalog →](/skills/)** — 33 SKILL.md files (29 core + 4
  regulated).
- **[Agents →](/agents/)** — 7 agent role definitions.
