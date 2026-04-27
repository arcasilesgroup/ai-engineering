# ADR-0001 — Hexagonal Architecture (Ports & Adapters)

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decider**: ai-engineering core team

## Context

`ai-engineering` integrates with **multiple frontends** (Claude Code, Cursor,
Codex CLI, GitHub Copilot, Gemini CLI, Antigravity) and **multiple backends**
(LLM providers, board providers, storage, signers). Tightly coupling the
domain to any of those means swapping any one of them rewrites half the
codebase.

## Decision

Adopt the **Ports and Adapters** style (Cockburn 2005) with a fat domain.

```
┌──────────────────── interfaces (driving) ─────────────────────┐
│  CLI · MCP server · IDE adapters · hooks                      │
└─────────────────────────┬─────────────────────────────────────┘
                          │ uses
┌──────────────── application (use cases) ─────────────────────┐
│  BootstrapProject, InvokeSkill, RunGate, SyncMirrors, ...    │
└─────────────────────────┬─────────────────────────────────────┘
                          │ uses
┌──────────────────── domain (pure) ───────────────────────────┐
│  Skill · Spec · Plan · Gate · Decision · Event · Policy ·    │
│  IdentityToken · AuditEntry — invariants, state machines      │
└─────────────────────────┬─────────────────────────────────────┘
                          │ depends on (only) ports
┌──────────────────────── ports ────────────────────────────────┐
│  FilesystemPort · LLMPort · TelemetryPort · PolicyPort ·     │
│  IdentityPort · AuditLogPort · SignaturePort · BoardPort      │
└─────────────────────────┬─────────────────────────────────────┘
                          │ implemented by
┌─────────────────── adapters (driven) ─────────────────────────┐
│  decision_store_json · OpaPolicyAdapter · ndjson_writer ·    │
│  github_adapter · azure_devops_adapter · sigstore_adapter    │
└───────────────────────────────────────────────────────────────┘
```

**Rules**

- Domain has zero `node:fs`, `node:net`, framework imports.
- Ports are TypeScript interfaces (or Python ABCs) only.
- Adapters depend on ports, never the other way around.
- Use cases live in `<context>/application` and orchestrate ports.

## Consequences

- **Pro**: swap an IDE adapter without touching the domain. Banking client
  can replace LiteLLM with TrueFoundry by writing one adapter.
- **Pro**: tests of the domain need zero I/O.
- **Con**: more files than a 2-layer monolith. Mitigated by having each
  bounded context small and self-contained.
- **Con**: adapter bugs are real and need contract tests. Mitigated by
  shared contract test suite per port.

## Alternatives considered

- **Layered architecture** — too many layers blur direction; ports are clearer.
- **Clean Architecture (Onion)** — same shape, more verbose nomenclature.
- **Anaemic domain + service layer** — drifts to procedural; dropped.
