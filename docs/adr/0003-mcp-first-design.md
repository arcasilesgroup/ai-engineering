# ADR-0003 — MCP-First Design (Streamable HTTP Stateless)

- **Status**: Accepted
- **Date**: 2026-04-27
- **Source**: 2026 MCP Roadmap (mar-2026, Linux Foundation)

## Context

v1 plan relied on generating static markdown files (`.cursor/rules/*.mdc`,
`.codex/skills/`, etc.) for each IDE. The 2026 MCP Roadmap deprecated
local stateful daemons and standardized on **Streamable HTTP stateless**
to handle load balancers, horizontal scaling, and SSO-integrated auth.

## Decision

Build the framework as an **MCP server first**, with mirror generation
as a fallback for IDEs that don't yet speak MCP.

- **Primary**: `@ai-engineering/mcp-server` exposes capabilities (skills,
  agents, gates, decisions, plugins) over Streamable HTTP.
- **Fallback**: `ai-eng sync-mirrors` generates markdown for legacy IDE
  paths until they upgrade.
- **Auth**: SSO via CIMD (Client ID Metadata Documents) or DCR (Dynamic
  Client Registration).
- **Observability**: structured audit trails via OpenTelemetry → SIEM
  (Splunk HEC adapter included).

## Consequences

- **Pro**: IDEs query the framework dynamically — context drift goes
  from "regenerate static files" to "fetch what you need on demand"
  (ContextOps Harness pattern from ACE paper Stanford+SambaNova).
- **Pro**: load balancers, multi-region, and SSO integrate naturally.
- **Pro**: MCP roadmap is officially Linux Foundation governed —
  long-term stable.
- **Con**: requires MCP support from the IDE host. Most IDEs already
  have it (Claude Code, Cursor, Codex CLI). Antigravity supports it
  too. Cline through extensions.
- **Con**: more complex than copying files. Mitigated by keeping the
  fallback path for IDE without MCP.

## Implementation references

- `packages/mcp-server/` — server package
- `packages/cli/src/commands/sync_mirrors.ts` — fallback generator
