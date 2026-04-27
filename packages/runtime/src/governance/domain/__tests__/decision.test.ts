import { describe, expect, test } from "bun:test";
import fc from "fast-check";

import { DecisionId } from "../../../shared/kernel/branded.ts";
import { isErr, isOk } from "../../../shared/kernel/result.ts";
import {
  TTL_DAYS_BY_SEVERITY,
  MAX_RENEWALS,
  createDecision,
  isExpired,
  renew,
  type DecisionInput,
} from "../decision.ts";

const baseInput = (overrides: Partial<DecisionInput> = {}): DecisionInput => ({
  id: DecisionId("DEC-001"),
  findingId: "CVE-2026-1234",
  severity: "high",
  justification: "False positive in test fixture; tracked in spec-099",
  owner: "alice@example.com",
  specRef: "spec-099",
  issuedAt: new Date("2026-04-27T00:00:00Z"),
  ...overrides,
});

describe("Decision — happy path", () => {
  test("creates with expiresAt = issuedAt + TTL[severity]", () => {
    const result = createDecision(baseInput({ severity: "high" }));
    expect(isOk(result)).toBe(true);
    if (isOk(result)) {
      const expected = new Date(
        baseInput().issuedAt.getTime() + TTL_DAYS_BY_SEVERITY.high * 86400000,
      );
      expect(result.value.expiresAt.toISOString()).toBe(expected.toISOString());
      expect(Object.isFrozen(result.value)).toBe(true);
    }
  });

  test("severity TTL ladder is correct", () => {
    expect(TTL_DAYS_BY_SEVERITY.critical).toBe(15);
    expect(TTL_DAYS_BY_SEVERITY.high).toBe(30);
    expect(TTL_DAYS_BY_SEVERITY.medium).toBe(60);
    expect(TTL_DAYS_BY_SEVERITY.low).toBe(90);
  });
});

describe("Decision — validation", () => {
  test.each(["justification", "findingId", "owner", "specRef"] as const)(
    "rejects empty %s",
    (field) => {
      const result = createDecision(baseInput({ [field]: "" }));
      expect(isErr(result)).toBe(true);
    },
  );

  test("rejects whitespace-only justification", () => {
    expect(isErr(createDecision(baseInput({ justification: "   " })))).toBe(
      true,
    );
  });

  test("rejects renewals > MAX_RENEWALS", () => {
    expect(
      isErr(createDecision(baseInput({ renewals: MAX_RENEWALS + 1 }))),
    ).toBe(true);
  });

  test("rejects negative renewals", () => {
    expect(isErr(createDecision(baseInput({ renewals: -1 })))).toBe(true);
  });
});

describe("Decision — expiration", () => {
  test("not expired before TTL", () => {
    const result = createDecision(baseInput({ severity: "high" }));
    expect(isOk(result)).toBe(true);
    if (isOk(result)) {
      const oneDayLater = new Date(baseInput().issuedAt.getTime() + 86400000);
      expect(isExpired(result.value, oneDayLater)).toBe(false);
    }
  });

  test("expired exactly at TTL boundary", () => {
    const result = createDecision(baseInput({ severity: "high" }));
    expect(isOk(result)).toBe(true);
    if (isOk(result)) {
      expect(isExpired(result.value, result.value.expiresAt)).toBe(true);
    }
  });
});

describe("Decision — renewal", () => {
  test("first renewal increments counter and resets clock", () => {
    const initial = createDecision(baseInput());
    expect(isOk(initial)).toBe(true);
    if (!isOk(initial)) return;
    const now = new Date(initial.value.expiresAt.getTime());
    const renewed = renew(initial.value, now);
    expect(isOk(renewed)).toBe(true);
    if (isOk(renewed)) {
      expect(renewed.value.renewals).toBe(1);
      expect(renewed.value.issuedAt.toISOString()).toBe(now.toISOString());
    }
  });

  test("rejects 3rd renewal (>MAX_RENEWALS)", () => {
    let decision = createDecision(baseInput());
    expect(isOk(decision)).toBe(true);
    if (!isOk(decision)) return;
    let current = decision.value;
    for (let i = 0; i < MAX_RENEWALS; i++) {
      const r = renew(current, new Date(current.expiresAt));
      expect(isOk(r)).toBe(true);
      if (isOk(r)) current = r.value;
    }
    const tooMany = renew(current, new Date(current.expiresAt));
    expect(isErr(tooMany)).toBe(true);
  });
});

describe("Decision — property-based: TTL invariant", () => {
  test("expiresAt - issuedAt always equals TTL[severity] in days", () => {
    fc.assert(
      fc.property(
        fc.constantFrom("critical", "high", "medium", "low" as const),
        fc.date({ min: new Date("2024-01-01"), max: new Date("2030-12-31") }),
        (severity, issuedAt) => {
          const result = createDecision(baseInput({ severity, issuedAt }));
          if (!isOk(result)) return false;
          const diffDays =
            (result.value.expiresAt.getTime() - issuedAt.getTime()) / 86400000;
          return diffDays === TTL_DAYS_BY_SEVERITY[severity];
        },
      ),
      { numRuns: 200 },
    );
  });
});
