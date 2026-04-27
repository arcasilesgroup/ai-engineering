import type { Result } from "../kernel/result.ts";
import type { PolicyViolation } from "../kernel/errors.ts";

/**
 * PolicyPort — Dual-Plane Architecture Deterministic Plane gatekeeper.
 *
 * Every action proposed by the LLM (the Probabilistic Plane) MUST pass
 * through this port BEFORE execution. This is what stops Excessive Agency
 * and Prompt Injection at the source.
 *
 * Implementations:
 * - OpaPolicyAdapter — uses Open Policy Agent + Rego
 * - CedarPolicyAdapter — AWS-native natural-language policies
 * - InMemoryPolicyAdapter — for tests
 *
 * Decisions are recorded in the AuditLogPort regardless of allow/deny.
 */
export interface PolicyDecisionRequest {
  readonly action: string; // e.g. "execute_bash", "edit_file", "delete_branch"
  readonly resource: string; // e.g. "/path/to/file", "main"
  readonly actor: string; // agent id or "human"
  readonly context: Readonly<Record<string, unknown>>;
}

export type PolicyDecision =
  | { readonly verdict: "allow"; readonly reason: string }
  | {
      readonly verdict: "deny";
      readonly reason: string;
      readonly policyId: string;
    }
  | { readonly verdict: "ask-human"; readonly reason: string };

export interface PolicyPort {
  evaluate(
    req: PolicyDecisionRequest,
  ): Promise<Result<PolicyDecision, PolicyViolation>>;
}
