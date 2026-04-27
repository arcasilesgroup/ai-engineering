import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { InMemorySpanExporter, SimpleSpanProcessor } from "@opentelemetry/sdk-trace-base";

import { OtelExporterAdapter } from "../otel_exporter.ts";

const ENDPOINT_VAR = "AI_ENGINEERING_OTEL_ENDPOINT";
const DISABLED_VAR = "AI_ENGINEERING_TELEMETRY_DISABLED";
const TRACEPARENT_VAR = "TRACEPARENT";
const SAMPLE_TRACEPARENT = "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01";
const ENDPOINT_URL = "http://localhost:4318/v1/traces";

const attr = (span: { attributes: Record<string, unknown> } | undefined, key: string): unknown =>
  span ? span.attributes[key] : undefined;

const resourceAttr = (
  span: { resource?: { attributes: Record<string, unknown> } } | undefined,
  key: string,
): unknown => (span?.resource ? span.resource.attributes[key] : undefined);

describe("OtelExporterAdapter — disabled / unconfigured", () => {
  afterEach(() => {
    process.env[ENDPOINT_VAR] = undefined;
    process.env[DISABLED_VAR] = undefined;
  });

  test("emit is a no-op when endpoint is unset", async () => {
    process.env[ENDPOINT_VAR] = undefined;
    const adapter = new OtelExporterAdapter();
    await expect(
      adapter.emit({ level: "info", type: "skill.invoked", attributes: {} }),
    ).resolves.toBeUndefined();
  });

  test("startSpan returns stub handle when endpoint is unset", () => {
    process.env[ENDPOINT_VAR] = undefined;
    const adapter = new OtelExporterAdapter();
    const handle = adapter.startSpan("noop.span");
    expect(typeof handle.spanId).toBe("string");
    expect(typeof handle.traceId).toBe("string");
    // Stub handle methods must not throw.
    handle.setAttribute("k", "v");
    handle.end({ extra: 1 });
  });

  test("emit is a no-op when AI_ENGINEERING_TELEMETRY_DISABLED=1", async () => {
    process.env[ENDPOINT_VAR] = ENDPOINT_URL;
    process.env[DISABLED_VAR] = "1";
    const exporter = new InMemorySpanExporter();
    const adapter = new OtelExporterAdapter({
      spanProcessor: new SimpleSpanProcessor(exporter),
    });
    await adapter.emit({
      level: "info",
      type: "skill.invoked",
      attributes: { skill: "code" },
    });
    await adapter.forceFlush();
    expect(exporter.getFinishedSpans()).toHaveLength(0);
    await adapter.shutdown();
  });

  test("startSpan returns stub handle when telemetry is disabled", () => {
    process.env[ENDPOINT_VAR] = ENDPOINT_URL;
    process.env[DISABLED_VAR] = "1";
    const exporter = new InMemorySpanExporter();
    const adapter = new OtelExporterAdapter({
      spanProcessor: new SimpleSpanProcessor(exporter),
    });
    const handle = adapter.startSpan("disabled.span");
    handle.setAttribute("k", "v");
    handle.end();
    expect(exporter.getFinishedSpans()).toHaveLength(0);
  });
});

describe("OtelExporterAdapter — endpoint configured", () => {
  let exporter: InMemorySpanExporter;
  let adapter: OtelExporterAdapter;

  beforeEach(() => {
    process.env[ENDPOINT_VAR] = ENDPOINT_URL;
    process.env[DISABLED_VAR] = undefined;
    exporter = new InMemorySpanExporter();
    adapter = new OtelExporterAdapter({
      spanProcessor: new SimpleSpanProcessor(exporter),
    });
  });

  afterEach(async () => {
    await adapter.shutdown();
    exporter.reset();
    process.env[ENDPOINT_VAR] = undefined;
    process.env[DISABLED_VAR] = undefined;
  });

  test("emit creates a span named after the event type with attributes", async () => {
    await adapter.emit({
      level: "info",
      type: "skill.invoked",
      attributes: { skill: "code", duration_ms: 42 },
    });
    await adapter.forceFlush();
    const spans = exporter.getFinishedSpans();
    expect(spans).toHaveLength(1);
    const [span] = spans;
    expect(span?.name).toBe("skill.invoked");
    expect(attr(span, "skill")).toBe("code");
    expect(attr(span, "duration_ms")).toBe(42);
    expect(attr(span, "event.level")).toBe("info");
  });

  test("emit propagates traceId/spanId when supplied", async () => {
    await adapter.emit({
      level: "audit",
      type: "gate.failed",
      traceId: "0123456789abcdef0123456789abcdef",
      spanId: "0123456789abcdef",
      attributes: { gate: "lint" },
    });
    await adapter.forceFlush();
    const spans = exporter.getFinishedSpans();
    expect(spans).toHaveLength(1);
    const [span] = spans;
    expect(attr(span, "event.level")).toBe("audit");
  });

  test("startSpan returns a real OTel-backed handle", async () => {
    const handle = adapter.startSpan("workflow.run");
    handle.setAttribute("workflow", "test");
    handle.end({ outcome: "ok" });
    await adapter.forceFlush();
    const spans = exporter.getFinishedSpans();
    expect(spans).toHaveLength(1);
    const [span] = spans;
    expect(span?.name).toBe("workflow.run");
    expect(attr(span, "workflow")).toBe("test");
    expect(attr(span, "outcome")).toBe("ok");
    expect(typeof handle.spanId).toBe("string");
    expect(handle.spanId.length).toBe(16);
    expect(handle.traceId.length).toBe(32);
  });

  test("startSpan with parentSpanId records parent attribute", async () => {
    const parent = adapter.startSpan("parent.span");
    const child = adapter.startSpan("child.span", parent.spanId);
    child.end();
    parent.end();
    await adapter.forceFlush();
    const spans = exporter.getFinishedSpans();
    expect(spans.length).toBeGreaterThanOrEqual(2);
    const childSpan = spans.find((s) => s.name === "child.span");
    expect(attr(childSpan, "parent.span_id")).toBe(parent.spanId);
  });

  test("traceparent env var is recorded as attribute when present", async () => {
    process.env[TRACEPARENT_VAR] = SAMPLE_TRACEPARENT;
    try {
      const handle = adapter.startSpan("traced.op");
      handle.end();
      await adapter.forceFlush();
      const spans = exporter.getFinishedSpans();
      const traced = spans.find((s) => s.name === "traced.op");
      expect(attr(traced, "traceparent")).toBe(SAMPLE_TRACEPARENT);
    } finally {
      process.env[TRACEPARENT_VAR] = undefined;
    }
  });

  test("resource carries service.name = ai-engineering", async () => {
    const handle = adapter.startSpan("any.op");
    handle.end();
    await adapter.forceFlush();
    const spans = exporter.getFinishedSpans();
    const [span] = spans;
    expect(resourceAttr(span, "service.name")).toBe("ai-engineering");
    expect(typeof resourceAttr(span, "service.version")).toBe("string");
  });
});
