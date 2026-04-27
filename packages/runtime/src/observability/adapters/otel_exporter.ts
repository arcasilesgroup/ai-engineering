import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import type { Span, Tracer } from "@opentelemetry/api";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { resourceFromAttributes } from "@opentelemetry/resources";
import {
  BasicTracerProvider,
  SimpleSpanProcessor,
  type SpanProcessor,
} from "@opentelemetry/sdk-trace-base";
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION } from "@opentelemetry/semantic-conventions";

import type { FrameworkEvent, SpanHandle, TelemetryPort } from "../../shared/ports/telemetry.ts";

const SERVICE_NAME = "ai-engineering";
const TRACER_NAME = "@ai-engineering/runtime";

const ENDPOINT_VAR = "AI_ENGINEERING_OTEL_ENDPOINT";
const DISABLED_VAR = "AI_ENGINEERING_TELEMETRY_DISABLED";
const TRACEPARENT_VAR = "TRACEPARENT";

/**
 * Constructor injection point for tests. In production code, callers pass
 * nothing and the adapter wires up an OTLP HTTP exporter when the env var
 * is set. Tests pass `spanProcessor` (typically a SimpleSpanProcessor wrapping
 * an InMemorySpanExporter) for offline assertions.
 */
export interface OtelExporterAdapterOptions {
  spanProcessor?: SpanProcessor;
}

const STUB_SPAN_HANDLE: SpanHandle = Object.freeze({
  spanId: "0".repeat(16),
  traceId: "0".repeat(32),
  setAttribute: () => {},
  end: () => {},
});

const readServiceVersion = (): string => {
  try {
    const here = dirname(fileURLToPath(import.meta.url));
    // src/observability/adapters/otel_exporter.ts → ../../../package.json
    const pkgPath = resolve(here, "../../../package.json");
    const raw = readFileSync(pkgPath, "utf8");
    const parsed: unknown = JSON.parse(raw);
    if (
      parsed &&
      typeof parsed === "object" &&
      "version" in parsed &&
      typeof (parsed as { version: unknown }).version === "string"
    ) {
      return (parsed as { version: string }).version;
    }
  } catch {
    // Fall through to default below.
  }
  return "0.0.0";
};

/**
 * OtelExporterAdapter — TelemetryPort implementation backed by OpenTelemetry.
 *
 * Honors:
 *   - AI_ENGINEERING_TELEMETRY_DISABLED=1 → full no-op
 *   - AI_ENGINEERING_OTEL_ENDPOINT unset  → no-op (NDJSON sink remains active
 *     via the composite adapter)
 *   - TRACEPARENT env (W3C trace context) → recorded as `traceparent` attribute
 *
 * Emit semantics: each event becomes a synchronous span named after the event
 * `type`. The span carries the event's attributes plus a `event.level` label.
 * For `startSpan`, the returned `SpanHandle` is backed by a real OTel `Span`.
 */
export class OtelExporterAdapter implements TelemetryPort {
  private readonly provider: BasicTracerProvider | null;
  private readonly tracer: Tracer | null;

  constructor(options: OtelExporterAdapterOptions = {}) {
    if (!OtelExporterAdapter.isEnabled(options.spanProcessor)) {
      this.provider = null;
      this.tracer = null;
      return;
    }
    const processor = options.spanProcessor ?? this.defaultSpanProcessor();
    const resource = resourceFromAttributes({
      [ATTR_SERVICE_NAME]: SERVICE_NAME,
      [ATTR_SERVICE_VERSION]: readServiceVersion(),
    });
    this.provider = new BasicTracerProvider({
      resource,
      spanProcessors: [processor],
    });
    this.tracer = this.provider.getTracer(TRACER_NAME);
  }

  private static isEnabled(injected?: SpanProcessor): boolean {
    if (process.env[DISABLED_VAR] === "1") return false;
    if (injected) return true;
    return Boolean(process.env[ENDPOINT_VAR]);
  }

  private defaultSpanProcessor(): SpanProcessor {
    const url = process.env[ENDPOINT_VAR] ?? "";
    const exporter = new OTLPTraceExporter({ url });
    return new SimpleSpanProcessor(exporter);
  }

  async emit(event: Omit<FrameworkEvent, "id" | "timestamp">): Promise<void> {
    if (!this.tracer) return;
    const span = this.tracer.startSpan(event.type);
    span.setAttribute("event.level", event.level);
    if (event.traceId) span.setAttribute("event.trace_id", event.traceId);
    if (event.spanId) span.setAttribute("event.span_id", event.spanId);
    if (event.parentSpanId) {
      span.setAttribute("event.parent_span_id", event.parentSpanId);
    }
    this.applyAttributes(span, event.attributes);
    span.end();
  }

  startSpan(name: string, parentSpanId?: string): SpanHandle {
    if (!this.tracer) return STUB_SPAN_HANDLE;
    const span = this.tracer.startSpan(name);
    if (parentSpanId) span.setAttribute("parent.span_id", parentSpanId);
    const traceparent = process.env[TRACEPARENT_VAR];
    if (traceparent) span.setAttribute("traceparent", traceparent);
    const ctx = span.spanContext();
    return {
      spanId: ctx.spanId,
      traceId: ctx.traceId,
      setAttribute: (key, value) => {
        const safe = this.toAttributeValue(value);
        if (safe !== undefined) span.setAttribute(key, safe);
      },
      end: (extra) => {
        if (extra) this.applyAttributes(span, extra);
        span.end();
      },
    };
  }

  async forceFlush(): Promise<void> {
    if (this.provider) await this.provider.forceFlush();
  }

  async shutdown(): Promise<void> {
    if (this.provider) await this.provider.shutdown();
  }

  private applyAttributes(span: Span, attrs: Readonly<Record<string, unknown>>): void {
    for (const [key, value] of Object.entries(attrs)) {
      const safe = this.toAttributeValue(value);
      if (safe !== undefined) span.setAttribute(key, safe);
    }
  }

  private toAttributeValue(
    value: unknown,
  ): string | number | boolean | string[] | number[] | boolean[] | undefined {
    if (value === null || value === undefined) return undefined;
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      return value;
    }
    if (Array.isArray(value)) {
      const arr = value.filter((v) => v !== null && v !== undefined);
      if (arr.every((v) => typeof v === "string")) return arr as string[];
      if (arr.every((v) => typeof v === "number")) return arr as number[];
      if (arr.every((v) => typeof v === "boolean")) return arr as boolean[];
      return arr.map((v) => String(v));
    }
    return JSON.stringify(value);
  }
}
