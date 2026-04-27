# ai-engineering

> Multi-IDE AI agentic governance framework with subscription piggyback,
> federated plugins, and dual-plane security.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)
![Bun](https://img.shields.io/badge/bun-%3E%3D1.3-black)
![Python](https://img.shields.io/badge/python-%3E%3D3.13-blue)

`ai-engineering` is a **governance + automation framework** for teams
that build software with AI coding assistants (Claude Code, GitHub
Copilot, Codex CLI, Cursor, Gemini CLI, Antigravity, Cline). It gives
you SOLID/KISS/DRY/TDD/SDD discipline, regulated-industry compliance
controls, and a 3-tier plugin marketplace — **without** asking for any
new API key. You bring your own IDE subscription; the framework
piggybacks on it.

This repository hosts **v3.0**, a from-scratch redesign of the
framework. The architecture is documented in
[`docs/adr/`](./docs/adr/).

---

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

---

## What it gives you

### Subscription piggyback (no API keys)

Three layers of operation:

1. **Deterministic** (no LLM): install, plugin verification,
   release-gate, board sync, governance audit, risk acceptance,
   migration, mirror generation. ~70% of the value, zero token cost.
2. **IDE-host delegation**: skills like `/ai-specify`, `/ai-implement`,
   `/ai-debug` invoke the user's IDE in headless mode (`claude -p`,
   `cursor-agent -p`, `codex exec`, `gemini -p`). The IDE's subscription
   handles inference.
3. **BYOK opt-in**: only when no IDE host is present (CI flows). Uses
   an isolated LiteLLM bridge or — for regulated tier — TrueFoundry.

### Dual-Plane Architecture

Every action proposed by the LLM passes through a Deterministic Plane
**before** execution:

- **Input Guard** — regex + lightweight model scan for PII and known
  exploitation patterns
- **Identity Broker** — short-lived OBO tokens with minimum scopes
- **Policy Engine** (OPA / Rego) — declarative rules evaluated < 1ms
- **Immutable Audit Log** — hash-chained, SOC2/HIPAA/DORA ready

See [ADR-0002](./docs/adr/0002-dual-plane-architecture.md).

### Single Source of Truth + IDE mirrors

Skills live ONCE in `skills/catalog/<name>/SKILL.md`. The
`ai-eng sync-mirrors` command regenerates IDE-specific files for
Claude Code, Cursor, Codex CLI, GitHub Copilot, Gemini CLI, and
Antigravity — eliminating ~190 mirror files across 6 IDEs.

### Federated-curated plugin marketplace

Three-tier model:

- **OFFICIAL** (`@ai-engineering/*`) — team-signed
- **VERIFIED** (`@ai-engineering-verified/*`) — community-approved with
  human review + 30-day track record
- **COMMUNITY** — any GitHub repo with the
  `ai-engineering-plugin` topic; cryptographically attested via Sigstore
  keyless OIDC + SLSA v1.0 + CycloneDX SBOM + OpenSSF Scorecard ≥ 7.

Shai-Hulud 2.0 mitigations baked in: `--ignore-scripts` enforced in CI,
GitHub Actions pinned to immutable commit SHAs.

### Regulated industry profiles

`ai-eng install --profile banking | healthcare | fintech | airgapped`
activates four extra skills: `audit-trail`, `incident-respond`,
`compliance-report`, `data-classification`. LiteLLM is replaced by
TrueFoundry (in-cluster, zero-external-dependency PII redaction).
DORA, SOC2, HIPAA, PCI-DSS mappings included.

---

## Quick start

### Install

```bash
curl -fsSL https://get.ai-engineering.dev | bash
ai-eng --version
```

User-scope install (no `sudo`). Detects Bun runtime and installs it if
missing. Honors `XDG_CONFIG_HOME`.

### Bootstrap a new project

```bash
cd ~/projects/my-app
git init
ai-eng bootstrap
```

This generates `.ai-engineering/manifest.toml`, optional
`CONSTITUTION.md`, and IDE mirrors for whichever assistants you have
installed.

### Day-1 workflow inside Claude Code (or Cursor / Codex CLI / Copilot)

```
/ai-specify add magic-link auth with resend
# spec drafted at .ai-engineering/specs/spec-001-magic-link.md → review → approve

/ai-plan
# decomposed at .ai-engineering/specs/spec-001/plan.md → review → approve

/ai-implement
# builder agent runs RED-GREEN-REFACTOR per task, gates per task

/ai-pr
# pre-push gates in 3 lanes, opens PR, watches CI to green
```

### Plugin install

```bash
ai-eng plugin search soc2
ai-eng plugin install @ai-engineering-verified/soc2-pack
# verifies Sigstore + SLSA + SBOM, installs, generates IDE mirrors
```

---

## Architecture

### Repository layout (Screaming Architecture)

```
ai-engineering/
├── packages/                    # TypeScript + Bun (bun workspaces)
│   ├── cli/                     # ai-eng binary (bun build --compile)
│   ├── runtime/                 # domain core, application, adapters
│   │   └── src/
│   │       ├── governance/      ← Gate, Decision, RiskAcceptance, Policy
│   │       ├── skills/          ← Skill, Spec, Plan, Effort, Trigger
│   │       ├── agents/          ← Agent, Role, Capability
│   │       ├── observability/   ← Event, Lesson, Instinct
│   │       ├── platform/        ← IDE, Mirror, Hook
│   │       ├── delivery/        ← PullRequest, Branch, Release
│   │       └── shared/          ← kernel + ports + schemas
│   ├── mcp-server/              # Streamable HTTP stateless MCP server
│   ├── llm-bridge/              # TS thin wrapper -> Python LiteLLM
│   └── tui/                     # Optional Ink TUI dashboard
│
├── python/                      # Python + uv workspaces
│   ├── ai_eng_hooks/            # PreToolUse, PostToolUse, injection-guard
│   ├── ai_eng_evals/            # deepeval, ragas, promptfoo runners
│   └── ai_eng_litellm_bridge/   # HTTP localhost bridge (Docker-isolated)
│
├── skills/catalog/              # SOURCE OF TRUTH (Markdown SKILL.md)
│   ├── specify/                 ← /ai-specify
│   ├── plan/
│   ├── implement/
│   ├── test/
│   ├── debug/
│   ├── review/
│   ├── verify/
│   ├── commit/
│   └── pr/
│
├── agents/                      # builder, planner, verifier, reviewer,
│                                # explorer, orchestrator, security-scanner
│
├── docs/
│   ├── adr/                     # 10 architecture decision records
│   └── architecture/            # diagrams + overviews
│
└── tests/                       # E2E suites (unit/integration live next to code)
```

### Tech decisions at a glance

| Decision | Choice | Reference |
|----------|--------|-----------|
| Architecture | Hexagonal (Ports & Adapters) + Screaming | [ADR-0001](./docs/adr/0001-hexagonal-architecture.md), [ADR-0007](./docs/adr/0007-screaming-architecture.md) |
| Security model | Dual-Plane (Probabilistic + Deterministic) | [ADR-0002](./docs/adr/0002-dual-plane-architecture.md) |
| IDE protocol | MCP-first (Streamable HTTP stateless) | [ADR-0003](./docs/adr/0003-mcp-first-design.md) |
| Stack | Hybrid TypeScript+Bun + Python | [ADR-0004](./docs/adr/0004-hybrid-ts-python-stack.md) |
| LLM access | Subscription piggyback (no API keys) | [ADR-0005](./docs/adr/0005-subscription-piggyback.md) |
| Plugin distribution | 3-tier federated-curated | [ADR-0006](./docs/adr/0006-plugin-3-tier-distribution.md) |
| LLM router | LiteLLM Docker-isolated / TrueFoundry for regulated | [ADR-0008](./docs/adr/0008-litellm-isolation.md) |
| Telemetry | OpenTelemetry from Phase 0 | [ADR-0009](./docs/adr/0009-otel-from-day-zero.md) |
| Eval framework | CLEAR (Cost, Latency, Efficacy, Assurance, Reliability) | [ADR-0010](./docs/adr/0010-clear-framework-evals.md) |

---

## Status (alpha — Phases 0–8 landed, Phase 10 in progress)

This is an early-alpha redesign. Phases 0 through 8 are complete;
Phase 10 (docs site + release docs) is in progress alongside the
`v3.0.0-alpha.0` tag. Phase 9 (Ink TUI) is optional and not started.

| Phase | Scope | Status |
|-------|-------|--------|
| 0 — Foundation | bun + uv workspaces, ruff + Biome, CI matrix, NDJSON telemetry, CLI skeleton, manifest schema, ADRs | ✅ |
| 0.5 — Dual-Plane scaffolding | OPA Policy port, Identity Broker port, Audit Log port, Input Guard | ✅ |
| 1 — Domain core (TDD) | Skill, Spec, Decision, Gate, Event entities + property-based tests | ✅ |
| 2 — Application + Ports | use cases composed from ports + domain | ✅ |
| 3 — Driven adapters | FS, Git, Sigstore, OTel, GitHub Projects v2, Linear, Jira | ✅ |
| 4 — Driving adapters | full CLI, MCP server (Streamable HTTP stateless), IDE adapters | ✅ |
| 5 — LiteLLM bridge | Docker-isolated multi-LLM router; TS thin client | ✅ |
| 6 — Skills catalog | 29 core + 4 regulated SKILL.md | ✅ |
| 7 — Plugin system | search / install / verify / uninstall / update + Sigstore + SLSA + SBOM + Scorecard verification path (registry stubbed against local fixtures) | ✅ |
| 8 — Migration | v2 → v3 migrator scaffold (90-day compat layer ships with v3.0.0 stable) | ✅ |
| 9 — TUI + observability | Ink dashboards | ⏳ optional |
| 10 — Release + docs | Astro Starlight site, production readiness, release notes | 🚧 |

See [`docs/PRODUCTION_READINESS.md`](./docs/PRODUCTION_READINESS.md)
for the per-component readiness matrix, what's stubbed, and known
limitations. The full master plan with phase-level roadmap lives in
[`docs/architecture/master-plan.md`](./docs/architecture/master-plan.md).

---

## Development

```bash
git clone https://github.com/soydachi/ai-engineering.git
cd ai-engineering
bun install
uv sync

bun test                # TypeScript test suite
bunx pytest python/     # Python test suite
bun run lint            # Biome
bunx ruff check         # ruff
bun run typecheck       # tsc
```

### TDD discipline

Every domain change is RED-GREEN-REFACTOR. Coverage gate ≥ 80% on
domain logic, contract tests on adapters. See [ADR-0010](./docs/adr/0010-clear-framework-evals.md)
for the eval pyramid.

### Project values

- **SOLID** — single responsibility per module; ports invert
  dependencies.
- **KISS** — prefer 3 similar lines to a premature abstraction.
- **DRY** — single source of truth (skills, manifests, mirrors).
- **YAGNI** — no speculative features. Every line ties to a phase task.
- **TDD** — tests first, always.
- **SDD** (Spec-Driven Development) — every implementation traces to
  an approved spec.

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) and
[CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md). All contributions follow
the dual-plane discipline: tests + ports first, adapters second.

If you want to publish a plugin, read
[ADR-0006](./docs/adr/0006-plugin-3-tier-distribution.md) for the
trust model.

## Security

Vulnerabilities — please **do not** open public issues. See
[SECURITY.md](./SECURITY.md) for our coordinated disclosure policy.

## License

[MIT](./LICENSE) © 2026 ai-engineering contributors
