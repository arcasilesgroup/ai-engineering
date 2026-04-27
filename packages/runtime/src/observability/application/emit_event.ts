import {
  type EventId,
  type Result,
  type ValidationError,
  isErr,
} from "../../shared/kernel/index.ts";
import type {
  EventLevel,
  TelemetryPort,
} from "../../shared/ports/telemetry.ts";
import { type DomainEvent, createEvent } from "../domain/event.ts";

/**
 * EmitEvent — validates a candidate event via the domain factory and forwards
 * it to the TelemetryPort.
 *
 * Validation lives in the domain (`createEvent`); this use case is the thin
 * shell that wires the validated entity to the port. Domain-level rules
 * (lowercase dotted/dashed types, frozen attributes) are enforced before the
 * port observes anything — so adapters cannot receive malformed events.
 */
export interface EmitEventInput {
  readonly id: EventId;
  readonly timestamp: Date;
  readonly level: EventLevel;
  readonly type: string;
  readonly traceId?: string;
  readonly spanId?: string;
  readonly parentSpanId?: string;
  readonly attributes?: Readonly<Record<string, unknown>>;
}

export const emitEvent = async (
  input: EmitEventInput,
  telemetry: TelemetryPort,
): Promise<Result<DomainEvent, ValidationError>> => {
  const created = createEvent(input);
  if (isErr(created)) return created;

  await telemetry.emit({
    level: created.value.level,
    type: created.value.type,
    ...(created.value.traceId !== undefined
      ? { traceId: created.value.traceId }
      : {}),
    ...(created.value.spanId !== undefined
      ? { spanId: created.value.spanId }
      : {}),
    ...(created.value.parentSpanId !== undefined
      ? { parentSpanId: created.value.parentSpanId }
      : {}),
    attributes: created.value.attributes,
  });
  return created;
};
