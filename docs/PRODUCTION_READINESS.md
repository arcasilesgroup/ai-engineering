# Production Readiness — v3.0.0-alpha.0

> Snapshot captured at the cut of the `v3.0.0-alpha.0` tag. Updated as
> phases land. Source of truth: this file. The README's status table
> mirrors a condensed version.

`ai-engineering` v3 is a **clean-slate redesign**. This document tells
you, with no marketing gloss, what works today, what is stubbed or
requires manual setup, and what is deliberately deferred.

## Phase status

| Phase | Scope | Status | Evidence |
|-------|-------|--------|----------|
| **0** Foundation | bun + uv workspaces, ruff + Biome, CI matrix, NDJSON telemetry, CLI skeleton, manifest schema, ADRs | ✅ done | `package.json`, `pyproject.toml`, `.github/workflows/`, `shared/schemas/`, `docs/adr/` |
| **0.5** Dual-Plane scaffolding | OPA Policy port, Identity Broker port, Audit Log port, Input Guard | ✅ done | `packages/runtime/src/governance/`, `python/ai_eng_hooks/` |
| **1** Domain core (TDD) | `Skill`, `Spec`, `Decision` (TTL), `Gate`, `DomainEvent` + property-based tests via `fast-check` | ✅ done | `packages/runtime/src/{skills,governance,observability}/`, 285 TS tests pass |
| **2** Application + Ports | use cases composed from ports + domain | ✅ done | `packages/runtime/src/application/` |
| **3** Driven adapters | FS, Git, Sigstore, OTel, board adapters | ✅ done | `packages/runtime/src/adapters/`, `packages/runtime/src/observability/otel*` |
| **4** Driving adapters | full CLI, MCP server (Streamable HTTP stateless) | ✅ done | `packages/cli/src/commands/` (12 commands), `packages/mcp-server/` |
| **5** LiteLLM bridge | Docker-isolated multi-LLM router; TS thin client | ✅ done | `python/ai_eng_litellm_bridge/`, `packages/llm-bridge/` |
| **6** Skills catalog | full 29 core + 4 regulated SKILL.md | ✅ done | `skills/catalog/` (29 dirs), `skills/regulated/` (4 dirs) |
| **7** Plugin system | install / search / verify / uninstall / update; Sigstore + SLSA + SBOM + Scorecard verification path | ✅ done (registry stubbed) | `packages/cli/src/commands/plugin.ts` + tests |
| **8** Migration | v2 → v3 migrator scaffold | ✅ done | `packages/cli/src/commands/migrate.ts` + tests |
| **9** TUI + observability | Ink dashboard | ⏳ not started (optional) | `packages/tui/` empty shell |
| **10** Release + docs | Astro Starlight site, public launch | 🚧 in progress | `docs-site/`, this file, `RELEASE_NOTES_v3.0.0-alpha.0.md` |

## What works today (alpha)

These components are functional end-to-end inside the alpha and have
test coverage in CI.

### CLI commands (`packages/cli/src/commands/`)

Twelve sub-commands wired through `bun packages/cli/src/main.ts`:

- `bootstrap` — initialize a project with `.ai-engineering/manifest.toml`.
- `doctor` — local install health check (no LLM).
- `sync-mirrors` — regenerate IDE mirrors from `skills/catalog/`.
- `plugin {search,install,uninstall,update,verify}` — federated
  marketplace flows; verification path runs through the Sigstore +
  SLSA + SBOM + Scorecard pipeline.
- `governance` — audit + ownership boundary checks.
- `risk` — log-acceptance for findings, with TTL by severity.
- `release-gate` — 8-dimension production-release decision.
- `board {discover,sync,status,map}` — issue-tracker integration with
  fail-open semantics.
- `migrate` — v2 → v3 migrator (dry-run by default).
- `cleanup` — workspace hygiene (NDJSON rotation, cache prune).
- `llm` — invoke the LiteLLM bridge from the CLI.
- `skill` — list / show / validate skill metadata.

### MCP server (`packages/mcp-server/`)

- Streamable HTTP, stateless (per ADR-0003).
- SSO scaffolding for CIMD + DCR.
- Tools surface the runtime use cases (skills, governance, gates).

### Sigstore + supply-chain adapter

- Keyless OIDC verification (Phase 3.5).
- Hooks into `plugin install` and the release pipeline.

### Telemetry

- NDJSON local sink at `.ai-engineering/state/framework-events.ndjson`
  (always on).
- OpenTelemetry exporter (composite, per Phase 3.7) — emits to a local
  collector when `OTEL_EXPORTER_OTLP_ENDPOINT` is set.

### Plugin system (`packages/cli/src/commands/plugin.ts`)

- 3-tier model implemented: OFFICIAL / VERIFIED / COMMUNITY.
- Verification pipeline runs Sigstore bundle check, SLSA provenance
  check, CycloneDX SBOM read, OpenSSF Scorecard threshold check.
- Registry resolver currently stubbed (see _Stubbed / manual setup_
  below); the verification pipeline runs against locally-served test
  fixtures.

### LiteLLM bridge

- Python FastAPI service in `python/ai_eng_litellm_bridge/`.
- Hard-pinned dependency hashes to mitigate the March 2026 LiteLLM
  PyPI compromise.
- Ships with a Dockerfile that runs as a non-root user.
- TS thin client at `packages/llm-bridge/`.

### Skill catalog

- 29 core SKILL.md files under `skills/catalog/`.
- 4 regulated SKILL.md files under `skills/regulated/` (audit-trail,
  incident-respond, compliance-report, data-classification).
- Frontmatter validated against `shared/schemas/skill.schema.json`.

### Agent definitions

- 7 agents under `agents/`: `builder`, `planner`, `verifier`,
  `reviewer`, `explorer`, `orchestrator`, `security-scanner`.

## What's stubbed or requires manual setup

The alpha **deliberately** ships these as installable hooks rather than
bundled binaries — both to keep the install footprint small and so the
user picks the version they trust.

| Capability | Reason | How to enable |
|-----------|--------|----------------|
| `cosign` (Sigstore CLI) | Plugin signature verification calls out to it. | Install from the [Sigstore project](https://docs.sigstore.dev/cosign/installation/). |
| `slsa-verifier` | Provenance verification calls out to it. | Install from the [slsa-framework releases](https://github.com/slsa-framework/slsa-verifier). |
| `opa` | Runtime policy evaluation. | Install from the [OPA project](https://www.openpolicyagent.org/docs/latest/#running-opa). |
| OTel collector | Required only if you set `OTEL_EXPORTER_OTLP_ENDPOINT`. | Run any OTLP-compatible collector (Grafana Alloy, OTel Collector, Honeycomb agent…). |
| Docker | Required to run the LiteLLM bridge in its sandbox. | Any compliant runtime (Docker Desktop, Podman, OrbStack, colima). |
| `gitleaks` | Pre-commit secret scan. | The `commit` skill calls `gitleaks protect --staged`; the binary must be on `$PATH`. |

The plugin **registry resolver** points at a local fixture directory
during the alpha. The production registry repository (referenced by
ADR-0006) lands as part of the public-launch milestone (Phase 10
follow-up).

## Known limitations (deferred)

1. **TUI / Ink dashboard** (Phase 9) — not implemented. The CLI's
   default text output covers all flows; a TUI is purely a UX nicety.
2. **Production installer URL** (`https://get.ai-engineering.dev`) —
   not yet served. Build-from-source instructions in
   `GETTING_STARTED.md` and the docs site quickstart cover the alpha.
3. **`ai-eng plugin install` from the public registry** — works against
   local fixtures. Public registry is gated on the registry repository
   shipping (post-alpha).
4. **Native Windows** — only WSL2 is supported during alpha. Bun on
   Windows path/symlink quirks are tracked as risk #1 in the master
   plan.
5. **TrueFoundry adapter for the regulated profile** — interface is in
   place but the concrete adapter is a stub. Regulated tier currently
   refuses to use the LiteLLM bridge and relies on subscription
   piggyback exclusively.
6. **CLEAR framework eval runner** — skill evals are scaffolded under
   `skills/catalog/eval/` but the runner that produces the per-skill
   CLEAR scorecard is post-alpha.
7. **`--legacy` v2 compatibility layer** — the migrator is one-shot
   for the alpha. The 90-day compat layer ships with v3.0.0 stable.

## Test counts

| Suite | Files | Tests | Pass | Skip | Fail |
|-------|------:|------:|-----:|-----:|-----:|
| `bun test` (TypeScript) | 28 | 288 | 285 | 3 | 0 |
| `pytest` (Python) | 5 | 89 | n/a (collection only) | n/a | n/a |

TypeScript coverage gate: domain ≥ 80%, application ≥ 70% (see
`bunfig.toml` thresholds + Article II of the CONSTITUTION).
Python coverage is not yet enforced because the bridge tests run
against Docker and are mocked at the boundary; the gate moves to ≥ 70%
once Phase 5 ships its end-to-end harness.

## Security posture

| Control | Status | Reference |
|---------|--------|-----------|
| Dual-Plane Architecture (Probabilistic + Deterministic) | ✅ ports defined; hooks live | ADR-0002 |
| Input Guard (regex + lightweight model scan) | ✅ live | `python/ai_eng_hooks/src/ai_eng_hooks/input_guard.py` |
| Identity Broker (short-lived OBO tokens) | ✅ port; adapter stub | `packages/runtime/src/governance/identity_broker.ts` |
| OPA Policy port | ✅ port; adapter requires `opa` | `packages/runtime/src/governance/policy.ts` |
| Immutable, hash-chained Audit Log | ✅ port + reference adapter | `packages/runtime/src/governance/audit_log.ts` |
| Sigstore keyless OIDC verification | ✅ adapter | `packages/runtime/src/adapters/sigstore.ts` |
| SLSA v1.0 provenance verification | ✅ via `slsa-verifier` | `packages/cli/src/commands/plugin.ts` |
| CycloneDX SBOM read + OSV cross-check | ✅ minimal | `packages/cli/src/commands/plugin.ts` |
| OpenSSF Scorecard ≥ 7 enforcement | ✅ for VERIFIED/COMMUNITY | ADR-0006 |
| `--ignore-scripts` enforced in CI | ✅ | `.github/workflows/ci.yml` |
| GitHub Actions pinned to immutable commit SHAs | ✅ | every workflow under `.github/workflows/` |
| Shai-Hulud 2.0 mitigations | ✅ | ADR-0006, dependabot config, gitleaks |
| LiteLLM Docker isolation (non-root, hard-pinned hashes) | ✅ | `python/ai_eng_litellm_bridge/Dockerfile` |
| `gitleaks` pre-commit secret scan | ✅ | the `commit` skill |
| CodeQL on TS + Python | ✅ | `.github/workflows/codeql.yml` |
| OpenSSF Scorecard on the repo itself | ✅ | `.github/workflows/scorecard.yml` |

## Compliance

The four regulated-tier skills map to the following standards. Activate
them with `ai-eng install --profile banking|healthcare|fintech|airgapped`.

| Skill | SOC2 | ISO 27001 | HIPAA | PCI-DSS | DORA | GDPR |
|-------|------|-----------|-------|---------|------|------|
| `audit-trail` | CC7.2, CC7.3 | A.12.4 | 164.312(b) | 10.2, 10.3 | Art 11–13 | Art 30 |
| `incident-respond` | CC7.4 | A.16 | 164.308(a)(6) | 12.10 | Art 17–23 | Art 33–34 |
| `compliance-report` | CC2, CC4 | A.18 | 164.316(a) | 12.10.5 | Art 5–14 | Art 30, 32 |
| `data-classification` | CC6.1 | A.8.2 | 164.514 | 3, 9.4 | Art 9 | Art 4, 6, 9 |

The `compliance-report` skill emits cosign-signed CSV (audit firm),
JSON (Vanta / Drata), and PDF (board) outputs from a single source.

## Source of truth

| What | Where |
|------|-------|
| Skills (33: 29 core + 4 regulated) | `skills/catalog/`, `skills/regulated/` |
| Agents (7) | `agents/` |
| ADRs (10) | `docs/adr/` |
| CONSTITUTION (10 articles) | `CONSTITUTION.md` |
| Master plan | `docs/architecture/master-plan.md` |
| Manifest schema | `shared/schemas/manifest.schema.json` |
| Plugin manifest schema | `shared/schemas/plugin.schema.json` |
| Telemetry sink | `.ai-engineering/state/framework-events.ndjson` |
| CLI binary | `bun packages/cli/src/main.ts` (alpha) |
