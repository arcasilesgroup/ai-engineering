import { describe, expect, test } from "bun:test";
import fc from "fast-check";

import { GateId } from "../../../shared/kernel/branded.ts";
import { isErr, isOk } from "../../../shared/kernel/result.ts";
import {
  type GateFinding,
  type GateOutcome,
  type GateVerdict,
  createGateOutcome,
} from "../../domain/gate.ts";
import type { Severity } from "../../domain/decision.ts";
import { runReleaseGate } from "../run_release_gate.ts";

const NOW = new Date("2026-04-27T12:00:00Z");

const outcome = (
  gateId: string,
  verdict: GateVerdict,
  findings: ReadonlyArray<GateFinding> = [],
): GateOutcome => {
  const r = createGateOutcome({
    gateId: GateId(gateId),
    verdict,
    findings,
    executedAt: NOW,
    durationMs: 10,
  });
  if (!isOk(r)) throw new Error("test fixture invalid");
  return r.value;
};

const finding = (severity: Severity): GateFinding => ({
  findingId: `f-${severity}`,
  severity,
  message: `${severity} finding`,
});

describe("runReleaseGate — happy path", () => {
  test("all outcomes pass → GO", () => {
    const result = runReleaseGate([
      outcome("ruff", "pass"),
      outcome("pytest", "pass"),
    ]);
    expect(isOk(result)).toBe(true);
    if (isOk(result)) {
      expect(result.value.verdict).toBe("GO");
      expect(result.value.totals.pass).toBe(2);
      expect(result.value.totals.fail).toBe(0);
      expect(Object.isFrozen(result.value)).toBe(true);
      expect(Object.isFrozen(result.value.totals)).toBe(true);
    }
  });

  test("failure with critical/high finding → NO-GO", () => {
    const result = runReleaseGate([
      outcome("ruff", "pass"),
      outcome("pytest", "fail", [finding("high")]),
    ]);
    expect(isOk(result)).toBe(true);
    if (isOk(result)) {
      expect(result.value.verdict).toBe("NO-GO");
      expect(result.value.totals.fail).toBe(1);
    }
  });

  test("failure with only medium/low findings → CONDITIONAL", () => {
    const result = runReleaseGate([
      outcome("pytest", "pass"),
      outcome("ruff", "fail", [finding("medium")]),
    ]);
    expect(isOk(result)).toBe(true);
    if (isOk(result)) {
      expect(result.value.verdict).toBe("CONDITIONAL");
    }
  });

  test("warn-only outcomes → CONDITIONAL", () => {
    const result = runReleaseGate([
      outcome("ruff", "pass"),
      outcome("semgrep", "warn", [finding("low")]),
    ]);
    expect(isOk(result)).toBe(true);
    if (isOk(result)) {
      expect(result.value.verdict).toBe("CONDITIONAL");
      expect(result.value.totals.warn).toBe(1);
    }
  });

  test("error verdict with critical finding → NO-GO", () => {
    const result = runReleaseGate([
      outcome("pytest", "error", [finding("critical")]),
    ]);
    expect(isOk(result)).toBe(true);
    if (isOk(result)) {
      expect(result.value.verdict).toBe("NO-GO");
    }
  });

  test("aggregate exposes blocking outcomes flagged via isBlocking", () => {
    const result = runReleaseGate([
      outcome("pytest", "fail", [finding("critical")]),
      outcome("ruff", "pass"),
    ]);
    expect(isOk(result)).toBe(true);
    if (isOk(result)) {
      expect(result.value.blocking).toHaveLength(1);
      expect(result.value.blocking[0]?.gateId).toBe(GateId("pytest"));
    }
  });
});

describe("runReleaseGate — error paths", () => {
  test("rejects empty outcome list", () => {
    const result = runReleaseGate([]);
    expect(isErr(result)).toBe(true);
  });
});

describe("runReleaseGate — property-based: monotonicity", () => {
  test("NO-GO is sticky: any blocking outcome forces NO-GO", () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.constantFrom<GateVerdict>("pass", "fail", "warn", "error"),
          { minLength: 1, maxLength: 6 },
        ),
        fc.constantFrom<Severity>("critical", "high"),
        (verdicts, blockingSeverity) => {
          const outcomes = verdicts.map((v, i) =>
            outcome(
              `g${i}`,
              v,
              v === "fail" || v === "error" ? [finding(blockingSeverity)] : [],
            ),
          );
          // inject a guaranteed blocking outcome
          outcomes.push(
            outcome("blocker", "fail", [finding(blockingSeverity)]),
          );
          const r = runReleaseGate(outcomes);
          if (!isOk(r)) return false;
          return r.value.verdict === "NO-GO";
        },
      ),
      { numRuns: 100 },
    );
  });

  test("all-pass set always yields GO", () => {
    fc.assert(
      fc.property(fc.integer({ min: 1, max: 8 }), (n) => {
        const outcomes = Array.from({ length: n }, (_, i) =>
          outcome(`g${i}`, "pass"),
        );
        const r = runReleaseGate(outcomes);
        return isOk(r) && r.value.verdict === "GO";
      }),
      { numRuns: 50 },
    );
  });
});
