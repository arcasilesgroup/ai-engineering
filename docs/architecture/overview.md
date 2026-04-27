# Architecture Overview

> Pair this with [`master-plan.md`](./master-plan.md) (the WHAT/WHEN)
> and the ADRs in `docs/adr/` (the WHY for each decision).

## At-a-glance

```
                         ┌─────────────────────────┐
                         │   Developer's IDE host  │
                         │ (Claude Code / Cursor / │
                         │  Codex CLI / Copilot /  │
                         │  Gemini CLI / …)        │
                         └────────────┬────────────┘
                                      │ subscription piggyback
                                      ▼
              ┌──────────────────────────────────────────┐
              │      ai-engineering CLI (TS + Bun)       │
              │                                          │
              │  Layer 1 (no LLM):                       │
              │    install, doctor, plugin, board,       │
              │    governance, risk, sync-mirrors        │
              │                                          │
              │  Layer 2 (delegate to IDE):              │
              │    specify, plan, implement, debug,      │
              │    review, verify, commit, pr            │
              │                                          │
              │  Layer 3 (BYOK opt-in):                  │
              │    LiteLLM bridge (Docker isolated)      │
              └──────────────────────────────────────────┘
                                      │
                                      │ uses
                                      ▼
        ┌────────────────────────────────────────────────┐
        │       @ai-engineering/runtime (TS package)     │
        │                                                │
        │   ┌──────────── Hexagonal core ─────────────┐  │
        │   │  domain  ←  application  ←  adapters    │  │
        │   │  (pure)     (use cases)    (driven)     │  │
        │   └──────────────────────────────────────────┘  │
        │                                                │
        │   Bounded contexts (Screaming Architecture):   │
        │   governance · skills · agents ·               │
        │   observability · platform · delivery          │
        └────────────────────────────────────────────────┘
                          │                 │
                          │                 │
                          ▼                 ▼
                ┌──────────────────┐  ┌──────────────────┐
                │   MCP server     │  │ Python sidecars  │
                │ (Streamable HTTP │  │ ai_eng_hooks     │
                │  stateless +     │  │ ai_eng_evals     │
                │  SSO via CIMD/   │  │ ai_eng_litellm_  │
                │  DCR)            │  │   bridge         │
                └──────────────────┘  └──────────────────┘
```

## Dual-Plane execution slice

```
LLM PROPOSES       ┌──────── Probabilistic Plane ─────────┐
   action          │   Reasoning, planning, generation     │
                   └───────────────┬───────────────────────┘
                                   │ proposes
                                   ▼
                   ┌──────── Deterministic Plane ─────────┐
                   │  ┌────────────┐  ┌─────────────────┐  │
                   │  │Input Guard │→ │ Identity Broker │  │
                   │  └─────┬──────┘  └────────┬────────┘  │
                   │        ▼                  ▼           │
                   │  ┌────────────────────────────┐       │
                   │  │  Policy Engine (OPA)       │       │
                   │  │   allow / deny / ask-human │       │
                   │  └─────────────┬──────────────┘       │
                   │                ▼                      │
                   │     ┌─────────────────────┐           │
                   │     │   Immutable Audit    │          │
                   │     │  Log (hash chain)    │          │
                   │     └──────────┬───────────┘          │
                   └────────────────┴─────────────────────┘
                                    │ (only after allow)
                                    ▼
                              EXECUTION
```

## Single Source of Truth → IDE mirrors

```
              skills/catalog/<name>/SKILL.md
                          │
                ai-eng sync-mirrors
                          │
       ┌──────────────────┼──────────────────────┐
       ▼          ▼       ▼        ▼         ▼   ▼
  .claude/  .cursor/  .codex/  .github/  .gemini/  .agent/
   skills/   rules/   skills/   skills/   skills/   skills/
```

Mirrors carry the `DO NOT EDIT` header and `linguist-generated=true` in
`.gitattributes`. Hooks verify hash on `SessionStart` to detect tampering.

## Plugin trust pipeline

```
Plugin author publishes:
   .ai-engineering/plugin.toml (manifesto)
   tarball + SHA256
   plugin.sigstore.json (cosign keyless OIDC bundle)
   multiple.intoto.jsonl (SLSA v1.0 provenance)
   sbom.cdx.json (CycloneDX 1.6)
   OpenSSF Scorecard ≥ 7
                │
                ▼
ai-eng plugin install verifies all attestations against:
   - certificate identity regex (workflow path)
   - OIDC issuer (GitHub Actions)
   - Rekor transparency log entry
   - SLSA builder identity (slsa-github-generator pinned to immutable SHA)
   - SBOM CVEs cross-checked against OSV
   - yanked.json (revocation list)
```

## Where to read more

- Why hexagonal: [ADR-0001](../adr/0001-hexagonal-architecture.md)
- Why dual-plane: [ADR-0002](../adr/0002-dual-plane-architecture.md)
- Why MCP-first: [ADR-0003](../adr/0003-mcp-first-design.md)
- Why TS+Python hybrid: [ADR-0004](../adr/0004-hybrid-ts-python-stack.md)
- Why subscription piggyback: [ADR-0005](../adr/0005-subscription-piggyback.md)
- Plugin distribution model: [ADR-0006](../adr/0006-plugin-3-tier-distribution.md)
- LiteLLM isolation: [ADR-0008](../adr/0008-litellm-isolation.md)
