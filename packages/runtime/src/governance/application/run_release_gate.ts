import {
  ValidationError,
  type Result,
  err,
  ok,
} from "../../shared/kernel/index.ts";
import { type GateOutcome, isBlocking } from "../domain/gate.ts";

/**
 * RunReleaseGate — aggregate gate outcomes into a release verdict.
 *
 * Verdicts:
 *   - GO          → every outcome passed; release is unblocked.
 *   - CONDITIONAL → at least one warn/non-blocking failure; release proceeds
 *                   with risk acceptance / explicit approval.
 *   - NO-GO       → at least one blocking outcome (fail/error with
 *                   critical/high finding); release is halted.
 *
 * Pure function: no I/O, no port. Aggregation lives in application because
 * it composes domain primitives (GateOutcome, isBlocking) into a release
 * decision — a workflow concern, not an entity invariant.
 */
export type ReleaseVerdict = "GO" | "CONDITIONAL" | "NO-GO";

export interface ReleaseAggregate {
  readonly verdict: ReleaseVerdict;
  readonly totals: Readonly<{
    pass: number;
    fail: number;
    warn: number;
    error: number;
  }>;
  readonly blocking: ReadonlyArray<GateOutcome>;
  readonly outcomes: ReadonlyArray<GateOutcome>;
}

export const runReleaseGate = (
  outcomes: ReadonlyArray<GateOutcome>,
): Result<ReleaseAggregate, ValidationError> => {
  if (outcomes.length === 0) {
    return err(
      new ValidationError(
        "runReleaseGate requires at least one GateOutcome",
        "outcomes",
      ),
    );
  }

  const totals = { pass: 0, fail: 0, warn: 0, error: 0 };
  const blocking: GateOutcome[] = [];
  for (const o of outcomes) {
    totals[o.verdict] += 1;
    if (isBlocking(o)) blocking.push(o);
  }

  const verdict: ReleaseVerdict =
    blocking.length > 0
      ? "NO-GO"
      : totals.fail === 0 && totals.warn === 0 && totals.error === 0
        ? "GO"
        : "CONDITIONAL";

  return ok(
    Object.freeze({
      verdict,
      totals: Object.freeze({ ...totals }),
      blocking: Object.freeze([...blocking]),
      outcomes: Object.freeze([...outcomes]),
    }),
  );
};
