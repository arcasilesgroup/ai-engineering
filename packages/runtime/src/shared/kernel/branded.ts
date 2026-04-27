/**
 * Branded (nominal) types for compile-time identity guarantees.
 *
 * In a structural type system like TypeScript, `string` is `string`. This
 * module gives us nominal identifiers so a `SkillId` cannot accidentally
 * be passed where an `AgentId` is expected.
 *
 * Trade-off: minor ceremony (must use the constructor) for catastrophic
 * bug prevention (id mix-ups in 4-layer architecture).
 */
declare const brand: unique symbol;
export type Brand<T, B> = T & { readonly [brand]: B };

export type SkillId = Brand<string, "SkillId">;
export type AgentId = Brand<string, "AgentId">;
export type SpecId = Brand<string, "SpecId">;
export type PlanId = Brand<string, "PlanId">;
export type DecisionId = Brand<string, "DecisionId">;
export type GateId = Brand<string, "GateId">;
export type EventId = Brand<string, "EventId">;
export type PolicyId = Brand<string, "PolicyId">;
export type AuditEntryId = Brand<string, "AuditEntryId">;
export type IdentityTokenId = Brand<string, "IdentityTokenId">;

const NON_EMPTY_RE = /\S/;

const makeId =
  <B extends string>(brandName: B) =>
  (raw: string): Brand<string, B> => {
    if (!NON_EMPTY_RE.test(raw)) {
      throw new Error(`${brandName} cannot be empty or whitespace-only`);
    }
    return raw as Brand<string, B>;
  };

export const SkillId = makeId<"SkillId">("SkillId");
export const AgentId = makeId<"AgentId">("AgentId");
export const SpecId = makeId<"SpecId">("SpecId");
export const PlanId = makeId<"PlanId">("PlanId");
export const DecisionId = makeId<"DecisionId">("DecisionId");
export const GateId = makeId<"GateId">("GateId");
export const EventId = makeId<"EventId">("EventId");
export const PolicyId = makeId<"PolicyId">("PolicyId");
export const AuditEntryId = makeId<"AuditEntryId">("AuditEntryId");
export const IdentityTokenId = makeId<"IdentityTokenId">("IdentityTokenId");
