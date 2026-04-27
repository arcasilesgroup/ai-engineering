import { describe, expect, test } from "bun:test";
import fc from "fast-check";

import { DecisionId } from "../../../shared/kernel/branded.ts";
import { isErr, isOk } from "../../../shared/kernel/result.ts";
import { TTL_DAYS_BY_SEVERITY, type Severity } from "../../domain/decision.ts";
import { InMemoryDecisionStore } from "../_fakes.ts";
import { acceptRisk, type AcceptRiskInput } from "../accept_risk.ts";

const baseInput = (
  overrides: Partial<AcceptRiskInput> = {},
): AcceptRiskInput => ({
  id: DecisionId("DEC-001"),
  findingId: "CVE-2026-1234",
  severity: "high",
  justification: "False positive in test fixture; tracked in spec-099",
  owner: "alice@example.com",
  specRef: "spec-099",
  issuedAt: new Date("2026-04-27T00:00:00Z"),
  ...overrides,
});

describe("acceptRisk — happy path", () => {
  test("creates a Decision with TTL and persists it", async () => {
    const store = new InMemoryDecisionStore();
    const result = await acceptRisk(baseInput({ severity: "high" }), store);
    expect(isOk(result)).toBe(true);
    if (isOk(result)) {
      const expectedExpiry = new Date(
        baseInput().issuedAt.getTime() + TTL_DAYS_BY_SEVERITY.high * 86400000,
      );
      expect(result.value.expiresAt.toISOString()).toBe(
        expectedExpiry.toISOString(),
      );
      expect(Object.isFrozen(result.value)).toBe(true);

      const found = await store.findById(DecisionId("DEC-001"));
      expect(isOk(found)).toBe(true);
      if (isOk(found)) {
        expect(found.value.id).toBe(result.value.id);
        expect(found.value.findingId).toBe("CVE-2026-1234");
      }
    }
  });

  test("save count increments by exactly one", async () => {
    const store = new InMemoryDecisionStore();
    expect(store.size).toBe(0);
    await acceptRisk(baseInput(), store);
    expect(store.size).toBe(1);
  });
});

describe("acceptRisk — error paths", () => {
  test("rejects empty justification (validation error from domain)", async () => {
    const store = new InMemoryDecisionStore();
    const result = await acceptRisk(baseInput({ justification: "" }), store);
    expect(isErr(result)).toBe(true);
    expect(store.size).toBe(0);
  });

  test("rejects empty owner", async () => {
    const store = new InMemoryDecisionStore();
    const result = await acceptRisk(baseInput({ owner: "" }), store);
    expect(isErr(result)).toBe(true);
    expect(store.size).toBe(0);
  });

  test("rejects whitespace-only specRef", async () => {
    const store = new InMemoryDecisionStore();
    const result = await acceptRisk(baseInput({ specRef: "   " }), store);
    expect(isErr(result)).toBe(true);
    expect(store.size).toBe(0);
  });

  test("findById returns NotFound for unknown id", async () => {
    const store = new InMemoryDecisionStore();
    const found = await store.findById(DecisionId("DEC-missing"));
    expect(isErr(found)).toBe(true);
  });
});

describe("acceptRisk — property-based: severity drives TTL", () => {
  test("TTL is exactly TTL_DAYS_BY_SEVERITY[severity]", () => {
    fc.assert(
      fc.asyncProperty(
        fc.constantFrom<Severity>("critical", "high", "medium", "low"),
        async (severity) => {
          const store = new InMemoryDecisionStore();
          const r = await acceptRisk(baseInput({ severity }), store);
          if (!isOk(r)) return false;
          const days =
            (r.value.expiresAt.getTime() - r.value.issuedAt.getTime()) /
            86400000;
          return days === TTL_DAYS_BY_SEVERITY[severity];
        },
      ),
      { numRuns: 20 },
    );
  });
});
