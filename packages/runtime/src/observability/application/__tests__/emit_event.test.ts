import { describe, expect, test } from "bun:test";
import fc from "fast-check";

import { EventId } from "../../../shared/kernel/branded.ts";
import { isErr, isOk } from "../../../shared/kernel/result.ts";
import type { EventLevel } from "../../../shared/ports/telemetry.ts";
import { FakeTelemetryPort } from "../_fakes.ts";
import { emitEvent } from "../emit_event.ts";

const NOW = new Date("2026-04-27T12:00:00Z");

describe("emitEvent — happy path", () => {
  test("validates input via createEvent and emits via TelemetryPort", async () => {
    const fake = new FakeTelemetryPort();
    const result = await emitEvent(
      {
        id: EventId("evt-1"),
        timestamp: NOW,
        level: "info",
        type: "skill.invoked",
        attributes: { skill: "specify" },
      },
      fake,
    );
    expect(isOk(result)).toBe(true);
    expect(fake.emitted).toHaveLength(1);
    const [emitted] = fake.emitted;
    expect(emitted?.type).toBe("skill.invoked");
    expect(emitted?.attributes).toEqual({ skill: "specify" });
  });

  test("returned event is frozen", async () => {
    const fake = new FakeTelemetryPort();
    const result = await emitEvent(
      {
        id: EventId("evt-2"),
        timestamp: NOW,
        level: "audit",
        type: "gate.failed",
      },
      fake,
    );
    expect(isOk(result)).toBe(true);
    if (isOk(result)) {
      expect(Object.isFrozen(result.value)).toBe(true);
      expect(Object.isFrozen(result.value.attributes)).toBe(true);
    }
  });
});

describe("emitEvent — error paths", () => {
  test("rejects invalid event type (uppercase)", async () => {
    const fake = new FakeTelemetryPort();
    const result = await emitEvent(
      {
        id: EventId("evt-bad"),
        timestamp: NOW,
        level: "info",
        type: "Skill.Invoked",
      },
      fake,
    );
    expect(isErr(result)).toBe(true);
    expect(fake.emitted).toHaveLength(0);
  });

  test("rejects empty event type", async () => {
    const fake = new FakeTelemetryPort();
    const result = await emitEvent(
      {
        id: EventId("evt-bad"),
        timestamp: NOW,
        level: "info",
        type: "",
      },
      fake,
    );
    expect(isErr(result)).toBe(true);
    expect(fake.emitted).toHaveLength(0);
  });

  test("does not emit when validation fails", async () => {
    const fake = new FakeTelemetryPort();
    await emitEvent(
      {
        id: EventId("evt-bad"),
        timestamp: NOW,
        level: "info",
        type: "BAD TYPE",
      },
      fake,
    );
    expect(fake.emitted).toHaveLength(0);
  });
});

describe("emitEvent — property-based", () => {
  test("any valid event type is emitted exactly once", () => {
    fc.assert(
      fc.asyncProperty(
        fc.stringMatching(/^[a-z][a-z0-9._-]{0,32}$/),
        fc.constantFrom<EventLevel>("info", "warn", "error", "audit"),
        async (type, level) => {
          const fake = new FakeTelemetryPort();
          const result = await emitEvent(
            {
              id: EventId("evt-prop"),
              timestamp: NOW,
              level,
              type,
            },
            fake,
          );
          return isOk(result) && fake.emitted.length === 1;
        },
      ),
      { numRuns: 50 },
    );
  });
});
