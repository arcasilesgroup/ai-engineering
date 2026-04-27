import { appendFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";
import { randomUUID } from "node:crypto";

import type {
  FrameworkEvent,
  SpanHandle,
  TelemetryPort,
} from "../../shared/ports/telemetry.ts";

/**
 * NdjsonTelemetryAdapter — local always-on telemetry sink.
 *
 * Writes one event per line to a newline-delimited JSON file. Cross-platform,
 * append-only, fork-safe. Pairs with OTel exporter for upstream forwarding.
 *
 * Honors `AI_ENGINEERING_TELEMETRY_DISABLED=1` env var (privacy opt-out).
 */
export class NdjsonTelemetryAdapter implements TelemetryPort {
  constructor(private readonly path: string) {}

  async emit(event: Omit<FrameworkEvent, "id" | "timestamp">): Promise<void> {
    if (process.env.AI_ENGINEERING_TELEMETRY_DISABLED === "1") return;
    const full: FrameworkEvent = {
      id: randomUUID(),
      timestamp: new Date().toISOString(),
      ...event,
    };
    await mkdir(dirname(this.path), { recursive: true });
    await appendFile(this.path, `${JSON.stringify(full)}\n`, "utf8");
  }

  startSpan(name: string, parentSpanId?: string): SpanHandle {
    const traceId = parentSpanId ?? randomUUID();
    const spanId = randomUUID();
    const startedAt = performance.now();
    const attributes: Record<string, unknown> = { name };

    const handle: SpanHandle = {
      spanId,
      traceId,
      setAttribute: (key, value) => {
        attributes[key] = value;
      },
      end: (extra) => {
        const durationMs = Math.round(performance.now() - startedAt);
        void this.emit({
          level: "info",
          type: "span.ended",
          traceId,
          spanId,
          parentSpanId,
          attributes: { ...attributes, ...(extra ?? {}), durationMs },
        });
      },
    };
    return handle;
  }
}
