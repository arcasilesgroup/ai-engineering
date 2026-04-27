import { describe, expect, test } from "bun:test";

import { GateId } from "../../../shared/kernel/branded.ts";
import { isErr, isOk } from "../../../shared/kernel/result.ts";
import { createGateOutcome, isBlocking, type GateFinding } from "../gate.ts";

const NOW = new Date("2026-04-27T00:00:00Z");

const finding = (severity: GateFinding["severity"]): GateFinding => ({
  findingId: `F-${severity}`,
  severity,
  message: "test finding",
});

describe("GateOutcome — creation", () => {
  test("creates a passing outcome", () => {
    const r = createGateOutcome({
      gateId: GateId("ruff"),
      verdict: "pass",
      executedAt: NOW,
      durationMs: 120,
    });
    expect(isOk(r)).toBe(true);
    if (isOk(r)) {
      expect(r.value.verdict).toBe("pass");
      expect(r.value.findings).toHaveLength(0);
      expect(Object.isFrozen(r.value)).toBe(true);
    }
  });

  test("rejects negative durationMs", () => {
    const r = createGateOutcome({
      gateId: GateId("ruff"),
      verdict: "pass",
      executedAt: NOW,
      durationMs: -1,
    });
    expect(isErr(r)).toBe(true);
  });
});

describe("GateOutcome — isBlocking", () => {
  test("pass is never blocking", () => {
    const r = createGateOutcome({
      gateId: GateId("g"),
      verdict: "pass",
      executedAt: NOW,
      durationMs: 0,
    });
    if (isOk(r)) expect(isBlocking(r.value)).toBe(false);
  });

  test("fail with critical finding is blocking", () => {
    const r = createGateOutcome({
      gateId: GateId("g"),
      verdict: "fail",
      findings: [finding("critical")],
      executedAt: NOW,
      durationMs: 100,
    });
    if (isOk(r)) expect(isBlocking(r.value)).toBe(true);
  });

  test("fail with only low findings is NOT blocking", () => {
    const r = createGateOutcome({
      gateId: GateId("g"),
      verdict: "fail",
      findings: [finding("low"), finding("medium")],
      executedAt: NOW,
      durationMs: 100,
    });
    if (isOk(r)) expect(isBlocking(r.value)).toBe(false);
  });

  test("warn never blocks even with critical finding", () => {
    const r = createGateOutcome({
      gateId: GateId("g"),
      verdict: "warn",
      findings: [finding("critical")],
      executedAt: NOW,
      durationMs: 100,
    });
    if (isOk(r)) expect(isBlocking(r.value)).toBe(false);
  });
});
