# Release notes — v3.0.0-alpha.0

> _Tag this with `git tag v3.0.0-alpha.0` once the docs site lands._
> Date target: 2026-04-27. Status: alpha.

## Summary

`v3.0.0-alpha.0` is the first public alpha of `ai-engineering` after a
**clean-slate redesign**. The framework now piggybacks on whichever AI
coding subscription you already pay for, refuses to ship unsigned
plugins, and pushes every LLM-proposed action through a deterministic
guard plane before it ever runs.

This release covers Phases 0 through 8 of the master plan. Phase 9 (a
Ink TUI) is optional and Phase 10 (the docs site, this file, and the
production readiness checklist) is in progress alongside the tag.

## Highlights

- **Clean-slate redesign** — no v2 code carried over. All v2 artifacts
  were wiped before Phase 0 landed.
- **Hybrid TS+Bun + Python** — Bun for CLI / runtime / MCP / IDE
  adapters, Python for hooks / evals / the LiteLLM bridge.
- **Subscription piggyback** — the framework never asks the developer
  for an API key in the default path. Three execution layers:
  deterministic (no LLM), IDE-host delegation, BYOK opt-in.
- **Dual-Plane Architecture** — every action proposed by the LLM
  passes through Input Guard → Identity Broker → Policy Engine → Audit
  Log before execution. ADR-0002.
- **3-tier federated-curated plugin marketplace** — OFFICIAL,
  VERIFIED, COMMUNITY. Mandatory Sigstore keyless OIDC + SLSA v1.0 +
  CycloneDX SBOM + OpenSSF Scorecard ≥ 7. Shai-Hulud 2.0 mitigations
  baked in.
- **MCP-first** — Streamable HTTP, stateless, with SSO scaffolding via
  CIMD/DCR. ADR-0003.
- **33 skills** ship in this release: 29 core under `skills/catalog/`
  plus 4 regulated under `skills/regulated/` (`audit-trail`,
  `incident-respond`, `compliance-report`, `data-classification`).
- **7 agents** ship: `builder`, `planner`, `verifier`, `reviewer`,
  `explorer`, `orchestrator`, `security-scanner`.
- **OpenTelemetry from Phase 0** — composite NDJSON local sink + OTLP
  exporter. No telemetry is deferred.
- **Plugin marketplace skeleton** — `ai-eng plugin search / install /
  verify / uninstall / update` runs end-to-end against local fixtures.
  Public registry repository ships post-alpha.
- **Regulated profiles** — `ai-eng install --profile banking |
  healthcare | fintech | airgapped` activates the four extra skills
  and pins LiteLLM to TrueFoundry (in-cluster, zero external deps).
  DORA, SOC2, HIPAA, PCI-DSS mappings included.

## Try it

```bash
git clone https://github.com/soydachi/ai-engineering.git
cd ai-engineering

bun install --ignore-scripts
bun run build

# 285 TS tests + 89 Python tests
bun test
uv run pytest python/

# Local dev binary
bun packages/cli/src/main.ts --help
```

For a 5-minute on-ramp, see
[`GETTING_STARTED.md`](./GETTING_STARTED.md) or the docs site at
[ai-engineering.dev](https://ai-engineering.dev) (post-launch).

## What's not in this release

- **TUI / Ink dashboard** (Phase 9) — optional; not started.
- **Production installer URL** — `curl https://get.ai-engineering.dev`
  is not yet served.
- **Native Windows** — only WSL2 is supported during alpha.
- **Public plugin registry repo** — verification works against local
  fixtures.
- **CLEAR-framework skill scorecard runner** — scaffolded; full runner
  ships post-alpha.
- **`--legacy` v2 compatibility layer** — bundled with v3.0.0 stable.

The full picture lives in
[`docs/PRODUCTION_READINESS.md`](./docs/PRODUCTION_READINESS.md).

## Breaking changes

Everything. v2 → v3 is a clean break. The v2 → v3 migrator
(`ai-eng migrate`) is in place; the 90-day compat layer ships with
v3.0.0 stable.

## Acknowledgements

This redesign integrates findings from the NotebookLM deep research
(52 web sources, 16 subagent research streams). The five biggest
shifts versus v1:

1. LiteLLM Bridge isolation (after the March 2026 PyPI compromise).
2. ContextOps Harness — pivoting static markdown mirrors to MCP-first.
3. Shai-Hulud 2.0 mitigations.
4. MCP Streamable HTTP stateless + SSO from day one.
5. The Dual-Plane Architecture itself, separating the Probabilistic
   Plane (LLM) from the Deterministic Plane (OPA + Identity + Audit
   Log).

## Where to read more

- [`README.md`](./README.md) — full project overview.
- [`CHANGELOG.md`](./CHANGELOG.md) — itemized list.
- [`docs/PRODUCTION_READINESS.md`](./docs/PRODUCTION_READINESS.md) —
  per-component readiness, security posture, compliance mappings.
- [`docs/adr/`](./docs/adr/) — 10 ADRs.
- [`docs/architecture/master-plan.md`](./docs/architecture/master-plan.md)
  — phase roadmap.

[v3.0.0-alpha.0]: https://github.com/soydachi/ai-engineering/releases/tag/v3.0.0-alpha.0
