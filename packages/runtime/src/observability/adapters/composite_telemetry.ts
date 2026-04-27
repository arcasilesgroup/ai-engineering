import type { FrameworkEvent, SpanHandle, TelemetryPort } from "../../shared/ports/telemetry.ts";

/**
 * CompositeTelemetryAdapter — fan-out wrapper that broadcasts every emit and
 * span lifecycle event to a fixed list of inner TelemetryPort instances.
 *
 * Typical wiring: NDJSON local sink + OTel remote exporter.
 *
 * Resilience contract:
 *   - emit uses Promise.allSettled so one slow or failing sink never blocks
 *     another. Errors are swallowed (callers cannot recover anyway).
 *   - startSpan calls each underlying adapter; if one throws, the others
 *     still produce a span. The returned SpanHandle fans setAttribute and end
 *     out to every successfully started inner span, also tolerating individual
 *     failures.
 */
export class CompositeTelemetryAdapter implements TelemetryPort {
  constructor(private readonly inner: readonly TelemetryPort[]) {}

  async emit(event: Omit<FrameworkEvent, "id" | "timestamp">): Promise<void> {
    if (this.inner.length === 0) return;
    await Promise.allSettled(this.inner.map((port) => port.emit(event)));
  }

  startSpan(name: string, parentSpanId?: string): SpanHandle {
    const handles: SpanHandle[] = [];
    for (const port of this.inner) {
      try {
        handles.push(port.startSpan(name, parentSpanId));
      } catch {
        // Skip ports that fail to start a span.
      }
    }
    const primary = handles[0];
    return {
      spanId: primary?.spanId ?? "0".repeat(16),
      traceId: primary?.traceId ?? "0".repeat(32),
      setAttribute: (key, value) => {
        for (const handle of handles) {
          try {
            handle.setAttribute(key, value);
          } catch {
            // Tolerate per-span failures so one bad sink can't poison others.
          }
        }
      },
      end: (attrs) => {
        for (const handle of handles) {
          try {
            handle.end(attrs);
          } catch {
            // Same tolerance for end.
          }
        }
      },
    };
  }
}
