# Changelog

All notable changes to this project will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [3.0.0-alpha.0] — 2026-04-27

### Added — full clean-slate redesign

- **Hexagonal architecture** with bounded contexts under
  `packages/runtime/src/{governance,skills,agents,observability,platform,delivery}`
  and shared kernel + ports under `packages/runtime/src/shared/`.
- **Dual-Plane Architecture** — Probabilistic Plane (LLM) separated from
  Deterministic Plane (Input Guard, Identity Broker, Policy Engine,
  Audit Log). See [ADR-0002](./docs/adr/0002-dual-plane-architecture.md).
- **Subscription piggyback model** — framework no longer asks the
  developer for any API key. Three layers: deterministic, IDE-host
  delegation, BYOK opt-in. See [ADR-0005](./docs/adr/0005-subscription-piggyback.md).
- **Single Source of Truth + IDE mirror generation** — skills live once
  in `skills/catalog/<name>/SKILL.md`; `ai-eng sync-mirrors` regenerates
  IDE-specific files for Claude Code, Cursor, Codex CLI, GitHub Copilot,
  Gemini CLI, and Antigravity.
- **MCP-first** server with Streamable HTTP stateless support. ADR-0003.
- **Hybrid TS+Bun + Python** stack. Bun for CLI/runtime/MCP/IDE adapters,
  Python for hooks/evals/LiteLLM bridge. ADR-0004.
- **3-tier federated-curated plugin marketplace** (OFFICIAL / VERIFIED
  / COMMUNITY) with mandatory Sigstore + SLSA v1.0 + CycloneDX SBOM +
  OpenSSF Scorecard ≥ 7. ADR-0006.
- **OpenTelemetry from Phase 0** (not deferred). ADR-0009.
- **CLEAR framework for skill evals** (Cost, Latency, Efficacy,
  Assurance, Reliability). ADR-0010.
- **LiteLLM bridge** isolated in Docker, hard-pinned versions; replaced
  by TrueFoundry for `--profile=regulated`. ADR-0008.
- **Shai-Hulud 2.0 mitigations** — `--ignore-scripts` enforced in CI,
  GitHub Actions pinned to immutable commit SHAs.
- **Domain models with TDD**: `Skill`, `Spec`, `Decision` (TTL by
  severity), `Gate`, `DomainEvent`, with property-based tests via
  `fast-check`.
- **9 core skill SKILL.md files**: `specify`, `plan`, `implement`,
  `test`, `debug`, `review`, `verify`, `commit`, `pr`.
- **7 agent definitions**: `builder`, `planner`, `verifier`, `reviewer`,
  `explorer`, `orchestrator`, `security-scanner` (NEW).
- **Open source readiness**: README, CONTRIBUTING, CODE_OF_CONDUCT,
  SECURITY, CONSTITUTION, PR + issue templates, CODEOWNERS, dependabot.
- **CI workflows**: matrix Bun + Python, CodeQL, OpenSSF Scorecard,
  gitleaks. All actions pinned to immutable SHAs.
- **JSON Schemas** for skill frontmatter and plugin manifest under
  `shared/schemas/`.
- **10 ADRs** documenting every framework-level decision.
- **Input Guard hook** (Python) with deterministic regex + severity
  ladder (PII + manipulation patterns).

### Removed

- All legacy v2 artifacts. The migration path lives in Phase 8 of the
  master plan; legacy users should expect a `--legacy` compatibility
  layer for 90 days when v3.0.0 stable ships.

### Added — Phases 2–8 (post-foundation)

- **Phase 2 — Application use cases**
  - Governance, skills, and observability use cases composed from
    ports + domain. Application layer kept fat-domain-thin to honour
    Hexagonal Architecture (ADR-0001).
- **Phase 3 — Driven adapters**
  - **3.5 Sigstore signature adapter** — keyless OIDC bundle
    verification wired into the plugin install pipeline.
  - **3.7 Real OTel exporter + composite telemetry** — NDJSON local
    sink + OTLP exporter coexist via a composite. `OTEL_EXPORTER_OTLP_ENDPOINT`
    flips OTel on; the local sink stays always-on.
- **Phase 4 — Driving adapters**
  - **4.1 Complete CLI commands** — twelve sub-commands wired through
    `bun packages/cli/src/main.ts`: `bootstrap`, `doctor`,
    `sync-mirrors`, `plugin {search,install,verify,uninstall,update}`,
    `governance`, `risk`, `release-gate`, `board {discover,sync,status,map}`,
    `migrate`, `cleanup`, `llm`, `skill`. Runtime barrel exports
    flattened so the CLI imports from `@ai-engineering/runtime`.
  - **4.2 MCP server** — Streamable HTTP, stateless (per ADR-0003),
    with SSO scaffolding for CIMD + DCR. Tools surface the runtime
    use cases.
- **Phase 5 — LiteLLM bridge**
  - Docker-isolated FastAPI service running as a non-root user with
    hard-pinned dependency hashes (mitigation for the March 2026
    LiteLLM PyPI compromise — versions 1.82.7/8). TS thin client at
    `packages/llm-bridge/`.
- **Phase 6 — Skills catalog**
  - **+10 core SKILL.md files** (additions on top of the original 9):
    `bootstrap`, `start`, `commit`, `pr`, `release-gate`, `verify`,
    `governance`, `data`, `migrate`, `simplify`, plus the onboarding
    SDLC suite (`note`, `learn`, `explain`, `guide`, `hotfix`,
    `postmortem`, `resolve`, `risk-accept`, `eval`, `constitution`).
    Catalog now ships **29 core skills**.
  - **+4 regulated SKILL.md files** under `skills/regulated/`:
    `audit-trail`, `incident-respond`, `compliance-report`,
    `data-classification`. Activated by
    `ai-eng install --profile banking | healthcare | fintech | airgapped`.
- **Phase 7 — Plugin system**
  - `ai-eng plugin {search, install, verify, uninstall, update}` with
    full Sigstore keyless OIDC + SLSA v1.0 + CycloneDX SBOM + OpenSSF
    Scorecard ≥ 7 verification path. Registry resolver currently
    points at local fixtures; the public registry repository ships
    post-alpha.
- **Phase 8 — Migration scaffold**
  - `ai-eng migrate` v2 → v3 migrator (dry-run by default). The
    90-day compat layer ships with v3.0.0 stable.

### Added — Phase 10 (in progress)

- **Astro Starlight docs site** under `docs-site/` with auto-generated
  skill / agent / ADR indexes (`docs-site/scripts/generate.ts`).
- **`docs/PRODUCTION_READINESS.md`** — phase status, what works today,
  what's stubbed, known limitations, test counts, security posture,
  compliance mappings.
- **`RELEASE_NOTES_v3.0.0-alpha.0.md`** — short alpha release summary.

### Status

- **Phase 0** (Foundation) — ✅ complete
- **Phase 0.5** (Dual-Plane scaffolding — ports) — ✅ complete
- **Phase 1** (Domain core, TDD) — ✅ complete
- **Phase 2** (Application + Ports) — ✅ complete
- **Phase 3** (Driven adapters) — ✅ complete
- **Phase 4** (Driving adapters) — ✅ complete
- **Phase 5** (LiteLLM bridge) — ✅ complete
- **Phase 6** (Skills catalog: 29 core + 4 regulated) — ✅ complete
- **Phase 7** (Plugin system) — ✅ complete (registry stubbed)
- **Phase 8** (Migration scaffold) — ✅ complete
- **Phase 9** (TUI) — ⏳ not started (optional)
- **Phase 10** (Docs + release) — 🚧 in progress
- See [README.md status table](./README.md) and
  [`docs/PRODUCTION_READINESS.md`](./docs/PRODUCTION_READINESS.md).

[3.0.0-alpha.0]: https://github.com/soydachi/ai-engineering/releases/tag/v3.0.0-alpha.0
