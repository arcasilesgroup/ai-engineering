# Cross-Cutting Standard: Observability

## Scope

Applies to all stacks. Covers the three pillars: logs, metrics, and traces.

## Principles

1. **Three pillars**: logs (events), metrics (aggregates), traces (request flows). Each serves a different need.
2. **Instrument at boundaries**: HTTP handlers, queue consumers, external calls, database queries.
3. **Correlation**: all telemetry carries a trace/correlation ID for cross-service correlation.
4. **Low overhead**: instrumentation must not degrade application performance (< 1% overhead target).
5. **Actionable alerts**: every alert must have a runbook or clear remediation path.

## Patterns

- **Metrics**: RED method for services (Rate, Errors, Duration), USE method for resources (Utilization, Saturation, Errors).
- **Traces**: OpenTelemetry SDK for distributed tracing. Propagate W3C trace context headers.
- **Health endpoints**: `/health` (liveness), `/ready` (readiness). Return structured JSON with component status.
- **SLIs/SLOs**: define Service Level Indicators (latency p99, error rate) and Objectives (99.9% availability).
- **Dashboards**: one dashboard per service with RED metrics, error rates, and resource utilization.

## Anti-patterns

- Alerting on symptoms without dashboards for diagnosis.
- Missing traces in async/background job flows.
- High-cardinality metric labels (user IDs, request IDs as metric dimensions).
- No health endpoints — relying on TCP checks only.

## Update Contract

This file is framework-managed and may be updated by framework releases.
