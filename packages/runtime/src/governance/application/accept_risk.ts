import {
  type DecisionId,
  type NotFoundError,
  type Result,
  type ValidationError,
  isErr,
} from "../../shared/kernel/index.ts";
import {
  type Decision,
  type Severity,
  createDecision,
} from "../domain/decision.ts";

/**
 * AcceptRisk — record a logged risk acceptance.
 *
 * Constitution Article VII: risk acceptance is logged-acceptance, NOT
 * weakening. Justification, finding-id, owner, spec-ref, severity, TTL —
 * all enforced by `createDecision` in the domain layer. This use case
 * orchestrates validation + persistence via a port.
 */
export interface AcceptRiskInput {
  readonly id: DecisionId;
  readonly findingId: string;
  readonly severity: Severity;
  readonly justification: string;
  readonly owner: string;
  readonly specRef: string;
  readonly issuedAt: Date;
  readonly renewals?: number;
}

/**
 * Minimal port for persisting decisions. The application layer needs only
 * record-and-find; richer queries live in the adapter layer.
 */
export interface DecisionStorePort {
  save(decision: Decision): Promise<Result<void, StoreError>>;
  findById(
    id: DecisionId,
  ): Promise<Result<Decision, NotFoundError | StoreError>>;
}

export class StoreError extends Error {
  readonly retryable: boolean;
  constructor(message: string, retryable = false) {
    super(message);
    this.name = "StoreError";
    this.retryable = retryable;
  }
}

export const acceptRisk = async (
  input: AcceptRiskInput,
  store: DecisionStorePort,
): Promise<Result<Decision, ValidationError | StoreError>> => {
  const created = createDecision(input);
  if (isErr(created)) return created;

  const saved = await store.save(created.value);
  if (isErr(saved)) return saved;

  return created;
};
