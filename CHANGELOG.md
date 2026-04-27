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

### Status

- **Phase 0** (Foundation) — ✅ complete
- **Phase 0.5** (Dual-Plane scaffolding — ports) — ✅ complete
- **Phase 1** (Domain core, TDD) — ✅ complete
- **Phase 2** (Application + Ports) — 🚧 partial
- **Phase 3** (Driven adapters) — ⏳ stubs only
- **Phase 4-10** — see [README.md status table](./README.md#status-alpha--phase-0--phase-1-landed)

[3.0.0-alpha.0]: https://github.com/soydachi/ai-engineering/releases/tag/v3.0.0-alpha.0
