# ADR-0009 — OpenTelemetry From Phase 0

- **Status**: Accepted
- **Date**: 2026-04-27
- **Source**: NotebookLM critique gap #1

## Context

The original v1 plan deferred OpenTelemetry instrumentation to Phase 9
("optional"). For an agentic framework that orchestrates LLMs, hooks,
MCP servers, and IDE adapters, deferred observability guarantees that
early debugging will require parsing raw NDJSON logs.

## Decision

OpenTelemetry is a **Phase 0 deliverable**, not optional.

Distributed tracing spans:

```
ai-eng CLI ──→ MCP server ──→ LLM bridge
   │              │                │
   └──── trace_id propagated through entire chain ────┘
```

Local always-on sink: `framework-events.ndjson`. Remote OTel exporter:
opt-in via `AI_ENGINEERING_OTEL_ENDPOINT` env var. Honors
`AI_ENGINEERING_TELEMETRY_DISABLED=1` to fully opt out.

## Consequences

- **Pro**: from the first commit, every action is traceable.
- **Pro**: CLEAR framework metrics (Cost, Latency, Efficacy, Assurance,
  Reliability) feed off this telemetry.
- **Con**: small cost on every action. Async + non-blocking; not a hot
  path concern.

## Implementation references

- `packages/runtime/src/shared/ports/telemetry.ts` — `TelemetryPort`
- `packages/runtime/src/observability/adapters/ndjson_writer.ts` — local sink
