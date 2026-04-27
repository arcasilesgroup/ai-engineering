import { describe, expect, test } from "bun:test";

import type { FrameworkEvent, SpanHandle, TelemetryPort } from "../../../shared/ports/telemetry.ts";
import { CompositeTelemetryAdapter } from "../composite_telemetry.ts";

interface RecordedSpan {
  name: string;
  parentSpanId: string | undefined;
  attributes: Record<string, unknown>;
  endedWith: Record<string, unknown> | undefined;
  ended: boolean;
}

const spanAttr = (span: RecordedSpan | undefined, key: string): unknown =>
  span ? span.attributes[key] : undefined;

class RecordingTelemetryPort implements TelemetryPort {
  readonly emitted: Array<Omit<FrameworkEvent, "id" | "timestamp">> = [];
  readonly spans: RecordedSpan[] = [];

  async emit(event: Omit<FrameworkEvent, "id" | "timestamp">): Promise<void> {
    this.emitted.push(event);
  }

  startSpan(name: string, parentSpanId?: string): SpanHandle {
    const recorded: RecordedSpan = {
      name,
      parentSpanId,
      attributes: {},
      endedWith: undefined,
      ended: false,
    };
    this.spans.push(recorded);
    return {
      spanId: `span-${this.spans.length}`,
      traceId: parentSpanId ?? `trace-${this.spans.length}`,
      setAttribute: (key, value) => {
        recorded.attributes[key] = value;
      },
      end: (attrs) => {
        recorded.ended = true;
        recorded.endedWith = attrs ? { ...attrs } : undefined;
      },
    };
  }
}

class ThrowingTelemetryPort implements TelemetryPort {
  emit(_event: Omit<FrameworkEvent, "id" | "timestamp">): Promise<void> {
    return Promise.reject(new Error("boom"));
  }

  startSpan(): SpanHandle {
    throw new Error("startSpan exploded");
  }
}

describe("CompositeTelemetryAdapter — emit fan-out", () => {
  test("forwards emit to every wrapped adapter", async () => {
    const a = new RecordingTelemetryPort();
    const b = new RecordingTelemetryPort();
    const composite = new CompositeTelemetryAdapter([a, b]);
    await composite.emit({
      level: "info",
      type: "skill.invoked",
      attributes: { skill: "code" },
    });
    expect(a.emitted).toHaveLength(1);
    expect(b.emitted).toHaveLength(1);
    expect(a.emitted[0]?.type).toBe("skill.invoked");
    expect(b.emitted[0]?.type).toBe("skill.invoked");
  });

  test("rejection in one adapter does not block the other", async () => {
    const ok = new RecordingTelemetryPort();
    const broken = new ThrowingTelemetryPort();
    const composite = new CompositeTelemetryAdapter([broken, ok]);
    await composite.emit({
      level: "warn",
      type: "gate.failed",
      attributes: {},
    });
    expect(ok.emitted).toHaveLength(1);
  });

  test("emit returns void even if all adapters reject", async () => {
    const composite = new CompositeTelemetryAdapter([
      new ThrowingTelemetryPort(),
      new ThrowingTelemetryPort(),
    ]);
    await expect(
      composite.emit({ level: "info", type: "noop", attributes: {} }),
    ).resolves.toBeUndefined();
  });

  test("works with a single adapter", async () => {
    const a = new RecordingTelemetryPort();
    const composite = new CompositeTelemetryAdapter([a]);
    await composite.emit({ level: "info", type: "single", attributes: {} });
    expect(a.emitted).toHaveLength(1);
  });

  test("works with zero adapters", async () => {
    const composite = new CompositeTelemetryAdapter([]);
    await expect(
      composite.emit({ level: "info", type: "noop", attributes: {} }),
    ).resolves.toBeUndefined();
  });
});

describe("CompositeTelemetryAdapter — span fan-out", () => {
  test("setAttribute fans out to all wrapped spans", () => {
    const a = new RecordingTelemetryPort();
    const b = new RecordingTelemetryPort();
    const composite = new CompositeTelemetryAdapter([a, b]);
    const handle = composite.startSpan("workflow.run");
    handle.setAttribute("workflow", "test");
    handle.end({ outcome: "ok" });
    expect(a.spans).toHaveLength(1);
    expect(b.spans).toHaveLength(1);
    expect(spanAttr(a.spans[0], "workflow")).toBe("test");
    expect(spanAttr(b.spans[0], "workflow")).toBe("test");
    expect(a.spans[0]?.ended).toBe(true);
    expect(b.spans[0]?.ended).toBe(true);
    expect(a.spans[0]?.endedWith).toEqual({ outcome: "ok" });
    expect(b.spans[0]?.endedWith).toEqual({ outcome: "ok" });
  });

  test("propagates parentSpanId to every wrapped startSpan", () => {
    const a = new RecordingTelemetryPort();
    const b = new RecordingTelemetryPort();
    const composite = new CompositeTelemetryAdapter([a, b]);
    composite.startSpan("child", "parent-123");
    expect(a.spans[0]?.parentSpanId).toBe("parent-123");
    expect(b.spans[0]?.parentSpanId).toBe("parent-123");
  });

  test("startSpan failure in one adapter does not break the other", () => {
    const a = new RecordingTelemetryPort();
    const broken = new ThrowingTelemetryPort();
    const composite = new CompositeTelemetryAdapter([broken, a]);
    const handle = composite.startSpan("resilient.span");
    expect(typeof handle.spanId).toBe("string");
    handle.setAttribute("k", "v");
    handle.end();
    expect(a.spans).toHaveLength(1);
    expect(spanAttr(a.spans[0], "k")).toBe("v");
    expect(a.spans[0]?.ended).toBe(true);
  });

  test("end fan-out tolerates a span that throws on end", () => {
    const a = new RecordingTelemetryPort();
    const composite = new CompositeTelemetryAdapter([a]);
    const handle = composite.startSpan("op");
    // Override one span's end to throw via custom adapter.
    const explodingAdapter: TelemetryPort = {
      emit: async () => {},
      startSpan: () => ({
        spanId: "x",
        traceId: "y",
        setAttribute: () => {
          throw new Error("nope");
        },
        end: () => {
          throw new Error("nope-end");
        },
      }),
    };
    const composite2 = new CompositeTelemetryAdapter([explodingAdapter, a]);
    const h2 = composite2.startSpan("op2");
    expect(() => h2.setAttribute("k", "v")).not.toThrow();
    expect(() => h2.end({ extra: 1 })).not.toThrow();
    expect(handle.spanId).toBeTruthy();
  });
});
