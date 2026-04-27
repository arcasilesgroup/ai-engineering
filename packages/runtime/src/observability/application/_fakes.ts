import type {
  FrameworkEvent,
  SpanHandle,
  TelemetryPort,
} from "../../shared/ports/telemetry.ts";

/**
 * In-memory fake for TelemetryPort — used by application-layer tests.
 *
 * Preserves the order of emitted events so tests can assert observability
 * side effects without touching the filesystem.
 */
export class FakeTelemetryPort implements TelemetryPort {
  readonly emitted: Array<Omit<FrameworkEvent, "id" | "timestamp">> = [];

  async emit(event: Omit<FrameworkEvent, "id" | "timestamp">): Promise<void> {
    this.emitted.push(event);
  }

  startSpan(name: string, parentSpanId?: string): SpanHandle {
    const traceId = parentSpanId ?? "trace-fake";
    const spanId = `span-${this.emitted.length}`;
    const handle: SpanHandle = {
      spanId,
      traceId,
      setAttribute: () => {},
      end: (extra) => {
        void this.emit({
          level: "info",
          type: "span.ended",
          traceId,
          spanId,
          ...(parentSpanId !== undefined ? { parentSpanId } : {}),
          attributes: { name, ...(extra ?? {}) },
        });
      },
    };
    return handle;
  }
}
