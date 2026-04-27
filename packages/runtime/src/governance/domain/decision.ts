import {
  type DecisionId,
  ValidationError,
  type Result,
  ok,
  err,
} from "../../shared/kernel/index.ts";

/**
 * Decision — formalised risk acceptance with TTL by severity.
 *
 * D-105-14 lesson: risk acceptance is logged-acceptance, NOT weakening.
 * It MUST have:
 *   - non-empty justification
 *   - finding-id (stable identifier of what we're accepting)
 *   - owner (who is accountable)
 *   - spec-ref (which spec authorized this)
 *   - TTL by severity (Critical 15d / High 30d / Medium 60d / Low 90d)
 *
 * Up to 2 renewals per finding. After that, must remediate.
 */

export type Severity = "critical" | "high" | "medium" | "low";

export const TTL_DAYS_BY_SEVERITY: Readonly<Record<Severity, number>> =
  Object.freeze({
    critical: 15,
    high: 30,
    medium: 60,
    low: 90,
  });

export const MAX_RENEWALS = 2;

export interface Decision {
  readonly id: DecisionId;
  readonly findingId: string;
  readonly severity: Severity;
  readonly justification: string;
  readonly owner: string;
  readonly specRef: string;
  readonly issuedAt: Date;
  readonly expiresAt: Date;
  readonly renewals: number;
}

export interface DecisionInput {
  readonly id: DecisionId;
  readonly findingId: string;
  readonly severity: Severity;
  readonly justification: string;
  readonly owner: string;
  readonly specRef: string;
  readonly issuedAt: Date;
  readonly renewals?: number;
}

export const createDecision = (
  input: DecisionInput,
): Result<Decision, ValidationError> => {
  if (input.justification.trim().length === 0) {
    return err(
      new ValidationError(
        "Decision justification cannot be empty",
        "justification",
      ),
    );
  }
  if (input.findingId.trim().length === 0) {
    return err(
      new ValidationError("Decision findingId cannot be empty", "findingId"),
    );
  }
  if (input.owner.trim().length === 0) {
    return err(new ValidationError("Decision owner cannot be empty", "owner"));
  }
  if (input.specRef.trim().length === 0) {
    return err(
      new ValidationError("Decision specRef cannot be empty", "specRef"),
    );
  }
  const renewals = input.renewals ?? 0;
  if (renewals < 0 || renewals > MAX_RENEWALS) {
    return err(
      new ValidationError(
        `Decision renewals must be in [0, ${MAX_RENEWALS}], got ${renewals}`,
        "renewals",
      ),
    );
  }
  const ttlMs = TTL_DAYS_BY_SEVERITY[input.severity] * 24 * 60 * 60 * 1000;
  const expiresAt = new Date(input.issuedAt.getTime() + ttlMs);

  return ok(
    Object.freeze({
      id: input.id,
      findingId: input.findingId,
      severity: input.severity,
      justification: input.justification,
      owner: input.owner,
      specRef: input.specRef,
      issuedAt: input.issuedAt,
      expiresAt,
      renewals,
    }),
  );
};

export const isExpired = (decision: Decision, now: Date): boolean =>
  now.getTime() >= decision.expiresAt.getTime();

export const renew = (
  decision: Decision,
  now: Date,
): Result<Decision, ValidationError> => {
  if (decision.renewals >= MAX_RENEWALS) {
    return err(
      new ValidationError(
        `Decision ${decision.id} cannot be renewed beyond ${MAX_RENEWALS} times — must remediate`,
        "renewals",
      ),
    );
  }
  return createDecision({
    id: decision.id,
    findingId: decision.findingId,
    severity: decision.severity,
    justification: decision.justification,
    owner: decision.owner,
    specRef: decision.specRef,
    issuedAt: now,
    renewals: decision.renewals + 1,
  });
};
