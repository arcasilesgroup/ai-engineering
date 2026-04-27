import {
  type DecisionId,
  NotFoundError,
  type Result,
  err,
  ok,
} from "../../shared/kernel/index.ts";
import type { GateOutcome } from "../domain/gate.ts";
import type { Decision } from "../domain/decision.ts";
import type { DecisionStorePort, StoreError } from "./accept_risk.ts";

/**
 * In-memory adapters used by application-layer tests.
 *
 * Real adapters (e.g. `decision_store_json`) live in `governance/adapters/`
 * and ship outside this file.
 */
export class InMemoryDecisionStore implements DecisionStorePort {
  private readonly entries = new Map<string, Decision>();

  async save(decision: Decision): Promise<Result<void, StoreError>> {
    this.entries.set(decision.id, decision);
    return ok(undefined);
  }

  async findById(
    id: DecisionId,
  ): Promise<Result<Decision, NotFoundError | StoreError>> {
    const found = this.entries.get(id);
    if (!found) return err(new NotFoundError("Decision", id));
    return ok(found);
  }

  get size(): number {
    return this.entries.size;
  }
}

/**
 * Helper to build a frozen `GateOutcome` without re-importing the factory in
 * every test file.
 */
export const fakeGateOutcomes = (
  outcomes: ReadonlyArray<GateOutcome>,
): ReadonlyArray<GateOutcome> => Object.freeze([...outcomes]);
