/**
 * TelemetryPort — driven port for observability.
 *
 * v3 decision: OTel from Phase 0 (not deferred to Phase 9). Distributed
 * tracing spans the full execution: CLI → MCP server → LLM bridge.
 *
 * Local NDJSON file (`framework-events.ndjson`) is the always-on sink.
 * OTel exporter is opt-in via env var. This is the foundation for all
 * downstream metrics (CLEAR framework: cost/latency/efficacy/assurance/reliability).
 */
export type EventLevel = "info" | "warn" | "error" | "audit";

export interface FrameworkEvent {
  readonly id: string;
  readonly timestamp: string; // ISO 8601
  readonly level: EventLevel;
  readonly type: string; // e.g. "skill.invoked", "gate.failed"
  readonly traceId?: string;
  readonly spanId?: string;
  readonly parentSpanId?: string;
  readonly attributes: Readonly<Record<string, unknown>>;
}

export interface TelemetryPort {
  emit(event: Omit<FrameworkEvent, "id" | "timestamp">): Promise<void>;
  startSpan(name: string, parentSpanId?: string): SpanHandle;
}

export interface SpanHandle {
  readonly spanId: string;
  readonly traceId: string;
  end(attributes?: Readonly<Record<string, unknown>>): void;
  setAttribute(key: string, value: unknown): void;
}
