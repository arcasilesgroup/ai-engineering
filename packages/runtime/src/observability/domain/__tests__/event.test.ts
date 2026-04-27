import { describe, expect, test } from "bun:test";
import fc from "fast-check";

import { EventId } from "../../../shared/kernel/branded.ts";
import { isErr, isOk } from "../../../shared/kernel/result.ts";
import { createEvent } from "../event.ts";

const NOW = new Date();

describe("DomainEvent", () => {
  test("creates a valid event", () => {
    const r = createEvent({
      id: EventId("evt-1"),
      timestamp: NOW,
      level: "info",
      type: "skill.invoked",
      attributes: { skill: "specify" },
    });
    expect(isOk(r)).toBe(true);
    if (isOk(r)) {
      expect(Object.isFrozen(r.value)).toBe(true);
      expect(Object.isFrozen(r.value.attributes)).toBe(true);
    }
  });

  test.each([["Skill.Invoked"], ["1bad"], [""], ["foo bar"], ["UPPER"]])(
    "rejects invalid type %s",
    (type) => {
      const r = createEvent({
        id: EventId("evt-1"),
        timestamp: NOW,
        level: "info",
        type,
      });
      expect(isErr(r)).toBe(true);
    },
  );

  test("property: any [a-z][a-z0-9._-]* type is accepted", () => {
    fc.assert(
      fc.property(fc.stringMatching(/^[a-z][a-z0-9._-]{0,63}$/), (type) => {
        const r = createEvent({
          id: EventId("evt-1"),
          timestamp: NOW,
          level: "info",
          type,
        });
        return isOk(r);
      }),
      { numRuns: 200 },
    );
  });
});
