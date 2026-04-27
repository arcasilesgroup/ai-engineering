# Master Plan (v2 — Post-NotebookLM Review)

> **Source**: `/Users/soydachi/.claude/plans/no-crees-spec-me-tranquil-hartmanis.md`
> generated 2026-04-27 from 16 subagent research streams + NotebookLM
> deep research (52 web sources). Reproduced here in condensed form
> so contributors can read it without leaving the repo.

This document is the **macroscopic plan**. It is intentionally short —
the deep details live in the ADRs (`docs/adr/`) and the SKILL.md files
(`skills/catalog/`). When the plan and the ADRs disagree, the ADRs win.

## The 5 big decisions

| # | Decision | Reference |
|---|----------|-----------|
| 1 | Subscription piggyback (no API keys) | [ADR-0005](../adr/0005-subscription-piggyback.md) |
| 2 | Hybrid TS+Bun + Python | [ADR-0004](../adr/0004-hybrid-ts-python-stack.md) |
| 3 | Single Source of Truth + Mirror generation | [ADR-0003](../adr/0003-mcp-first-design.md), [ADR-0007](../adr/0007-screaming-architecture.md) |
| 4 | 3-tier federated-curated plugin marketplace | [ADR-0006](../adr/0006-plugin-3-tier-distribution.md) |
| 5 | Dual-Plane Architecture | [ADR-0002](../adr/0002-dual-plane-architecture.md) |

## Phase roadmap

| Phase | Scope | Wks | Status |
|-------|-------|----:|--------|
| 0 — Foundation | bun + uv workspaces, ruff + Biome, CI matrix, NDJSON telemetry, CLI skeleton, manifest schema, ADRs | 1 | ✅ |
| 0.5 — Dual-Plane scaffolding | OPA Policy port, Identity Broker port, Audit Log port, Input Guard | 0.5 | ✅ ports done; adapters in P3 |
| 1 — Domain core (TDD) | Skill, Spec, Decision (TTL), Gate, Event entities + property-based tests | 2 | ✅ |
| 2 — Application + Ports | use cases composed from ports + domain | 1.5 | 🚧 partial |
| 3 — Driven adapters | FS, Git, Sigstore, OTel, GitHub Projects v2, Linear, Jira | 2 | ⏳ |
| 4 — Driving adapters | full CLI, MCP server (Streamable HTTP stateless), IDE adapters | 1.5 | ⏳ |
| 5 — LiteLLM bridge | Docker-isolated multi-LLM router; TrueFoundry alternative for regulated | 1 | ⏳ |
| 6 — Skills catalog | full 29 core + 4 regulated SKILL.md | 2 | 🚧 9 core done |
| 7 — Plugin system | registry + Sigstore + SLSA + SBOM + Scorecard | 1 | ⏳ |
| 8 — Migration | v2 → v3 migrator with 90-day compat layer | 1 | ⏳ |
| 9 — TUI + observability | Ink dashboard (optional) | 1-2 | ⏳ |
| 10 — Release + docs | Astro Starlight site, launch | 1 | ⏳ |

**Total**: 13–14 weeks for public launch (Phase 0–10). 11–13 weeks for
MVP (Phase 0–8). Updated from v1 estimate (+1 week) to absorb the
NotebookLM review additions: OTel from Phase 0, Dual-Plane scaffolding,
LiteLLM hardening, Shai-Hulud 2.0 mitigations.

## What changed from v1

The v2 plan integrates 5 prioritized improvements + 1 missing trend
discovered during the NotebookLM review (52 web sources):

### IMMEDIATE (Phase 0, before any code)

1. **LiteLLM Bridge isolation** — Docker isolated unprivileged user,
   hard-pinned hashes. For `--profile=regulated`, replace with
   TrueFoundry (in-cluster, zero external dependencies for PII).
   Source: LiteLLM PyPI compromise March 2026 (versions 1.82.7/8).
2. **ContextOps Harness** — pivot static markdown mirrors → MCP-first
   with incremental context injection. ACE paper (Stanford+SambaNova,
   October 2025) showed 86% drift / latency reduction.

### CRITICAL (Phase 1–3)

3. **Shai-Hulud 2.0 mitigations** — `--ignore-scripts` enforced in
   CI; GitHub Actions pinned to immutable SHAs (not tags).
4. **MCP Streamable HTTP stateless + SSO** — local stateful daemons
   deprecated by 2026 MCP Roadmap; we ship CIMD/DCR for SSO from day
   one.

### DEFERRED (Phase 5+)

5. **CLEAR framework for evals** — Cost, Latency, Efficacy, Assurance,
   Reliability. Replaces single-run accuracy. arXiv 2511.14136.

### Missing trend (now integrated)

6. **Dual-Plane Architecture + Cognitive Debt** — separate Probabilistic
   Plane (LLM) from Deterministic Plane (OPA + Identity + Audit Log).
   This is the single biggest architectural change vs v1.

## Risk register (Top 10)

| # | Risk | Mitigation |
|---|------|------------|
| 1 | Bun on Windows path/symlink quirks | Win CI from P0; Node fallback documented |
| 2 | Mirror format drift between IDEs | Schema linter + snapshot tests per adapter |
| 3 | IDE rate-limit during heavy workflows | Documented limits + LiteLLM fallback (P5) |
| 4 | Malicious plugin passes verification | COMMUNITY tier "use at risk"; VERIFIED requires manual review + 30 days |
| 5 | Sigstore OIDC outage blocks releases | Bundle cache + 24h grace window |
| 6 | LiteLLM bridge latency unacceptable | p95 ≤ 50 ms bench + bypass mode |
| 7 | SOC2 reporting incomplete in real audit | External auditor pilot in P6 before release |
| 8 | Team adoption: dev #2 ignores framework | Pre-commit hooks force paths; `bootstrap --join` zero-friction |
| 9 | LESSONS.md grows and nobody reads | Rotation + `learn` skill injects relevant lessons into context |
| 10 | v2 → v3 migration corrupts state | Mandatory dry-run + atomic backup + `migrate --rollback` |

## Critical path

```
P0 → P1 → P2 (ports) → P3 (FS+Git+Sigstore+OTel) → P4 (CLI+ClaudeCode adapter)
   → P6 (12 core skills) → P7 (plugin system) → P10 (release)
```

P9 (TUI) is fully parallelizable. P3 board adapters parallel internally
(GitHub vs Linear vs Jira). P4 IDE adapters parallel after Claude Code lands.

## Demoable milestones

| End of phase | Demo |
|---|---|
| P1 | Domain tests at 100% with property-based suite |
| P2 | Bootstrap with fake-FS adapter |
| P3 | Real-FS bootstrap + Sigstore-signed commit |
| P4 | Same skill running in Claude Code + Cursor + Codex CLI simultaneously |
| P5 | Routing privacy-tier strict → Bedrock live |
| P6 | Roberto user journey end-to-end (alpha-ready) |
| P7 | Diego plugin author journey — signed plugin verified + installed |
| P8 | v2 → v3 migration recorded |
| P10 | Public launch + 4 user journeys documented |
