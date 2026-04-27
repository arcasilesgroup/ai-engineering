import {
  type GateId,
  ValidationError,
  type Result,
  ok,
  err,
} from "../../shared/kernel/index.ts";
import type { Severity } from "./decision.ts";

/**
 * Gate — a deterministic check that produces verdicts (pass/fail).
 *
 * Examples: ruff, gitleaks, pytest, semgrep, pip-audit, OPA policy.
 *
 * v3 principle: never send an LLM to do a linter's job. Gates are
 * deterministic; their verdicts are inputs to release-gate aggregation.
 */

export type GateVerdict = "pass" | "fail" | "warn" | "error";

export interface GateOutcome {
  readonly gateId: GateId;
  readonly verdict: GateVerdict;
  readonly severity?: Severity;
  readonly findings: ReadonlyArray<GateFinding>;
  readonly executedAt: Date;
  readonly durationMs: number;
}

export interface GateFinding {
  readonly findingId: string;
  readonly severity: Severity;
  readonly message: string;
  readonly location?: { readonly file: string; readonly line?: number };
}

export const isBlocking = (outcome: GateOutcome): boolean => {
  if (outcome.verdict === "fail" || outcome.verdict === "error") {
    return outcome.findings.some(
      (f) => f.severity === "critical" || f.severity === "high",
    );
  }
  return false;
};

export const createGateOutcome = (input: {
  gateId: GateId;
  verdict: GateVerdict;
  findings?: ReadonlyArray<GateFinding>;
  executedAt: Date;
  durationMs: number;
}): Result<GateOutcome, ValidationError> => {
  if (input.durationMs < 0) {
    return err(
      new ValidationError("durationMs must be non-negative", "durationMs"),
    );
  }
  return ok(
    Object.freeze({
      gateId: input.gateId,
      verdict: input.verdict,
      findings: Object.freeze([...(input.findings ?? [])]),
      executedAt: input.executedAt,
      durationMs: input.durationMs,
    }),
  );
};
