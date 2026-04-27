import {
  type EventId,
  ValidationError,
  type Result,
  ok,
  err,
} from "../../shared/kernel/index.ts";
import type { EventLevel } from "../../shared/ports/telemetry.ts";

/**
 * FrameworkEvent (domain entity, immutable).
 *
 * Persisted via TelemetryPort to NDJSON locally + OTel exporter remotely.
 * The schema is the single contract between the framework and observability
 * tooling.
 */
export interface DomainEvent {
  readonly id: EventId;
  readonly timestamp: Date;
  readonly level: EventLevel;
  readonly type: string;
  readonly traceId?: string;
  readonly spanId?: string;
  readonly parentSpanId?: string;
  readonly attributes: Readonly<Record<string, unknown>>;
}

const TYPE_RE = /^[a-z][a-z0-9._-]*$/;

export const createEvent = (input: {
  id: EventId;
  timestamp: Date;
  level: EventLevel;
  type: string;
  traceId?: string;
  spanId?: string;
  parentSpanId?: string;
  attributes?: Readonly<Record<string, unknown>>;
}): Result<DomainEvent, ValidationError> => {
  if (!TYPE_RE.test(input.type)) {
    return err(
      new ValidationError(
        `Event type must be lowercase dotted/dashed identifier (got "${input.type}")`,
        "type",
      ),
    );
  }
  return ok(
    Object.freeze({
      id: input.id,
      timestamp: input.timestamp,
      level: input.level,
      type: input.type,
      traceId: input.traceId,
      spanId: input.spanId,
      parentSpanId: input.parentSpanId,
      attributes: Object.freeze({ ...(input.attributes ?? {}) }),
    }),
  );
};
