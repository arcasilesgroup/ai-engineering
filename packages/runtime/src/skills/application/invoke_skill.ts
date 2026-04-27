import {
  type Result,
  type SkillId,
  ValidationError,
  err,
  isErr,
  ok,
} from "../../shared/kernel/index.ts";
import type { LLMPort } from "../../shared/ports/llm.ts";
import type { TelemetryPort } from "../../shared/ports/telemetry.ts";
import type { Skill } from "../domain/skill.ts";
import {
  type TriggerMatch,
  NoSkillMatched,
  resolveTrigger,
} from "./resolve_trigger.ts";

/**
 * InvokeSkill — orchestrates capability negotiation + telemetry around the
 * decision to run a Skill.
 *
 * Constitution Article III (Dual-Plane Security): every probabilistic
 * action passes through deterministic checks first. We negotiate
 * `LLMPort.supports(capabilities)` BEFORE any inference happens so the
 * fallback chain or BYOK escalation can fire deterministically.
 *
 * This use case does NOT call `LLMPort.invoke`. The actual prompt
 * dispatch lives in the platform layer where the IDE host owns
 * concurrency, streaming, and rate-limit handling. Here we only:
 *   1. Resolve the trigger to a registered Skill.
 *   2. Confirm the routed provider supports its declared capabilities.
 *   3. Emit a `skill.invoked` audit event via TelemetryPort.
 */
export class CapabilityMismatch extends Error {
  readonly code = "CAPABILITY_MISMATCH";
  constructor(
    public readonly skillId: SkillId,
    public readonly missing: ReadonlyArray<string>,
  ) {
    super(
      `Skill ${skillId} requires capabilities the routed provider does not support: ${
        missing.join(", ") || "(none reported)"
      }`,
    );
    this.name = "CapabilityMismatch";
  }
}

export interface InvokeSkillInput {
  readonly intent: string;
  readonly registry: ReadonlyArray<Skill>;
}

export interface InvokeSkillOk {
  readonly skill: Skill;
  readonly match: TriggerMatch;
}

export type InvokeSkillError =
  | NoSkillMatched
  | CapabilityMismatch
  | ValidationError;

export const invokeSkill = async (
  input: InvokeSkillInput,
  llm: LLMPort,
  telemetry: TelemetryPort,
): Promise<Result<InvokeSkillOk, InvokeSkillError>> => {
  const matched = resolveTrigger(input.registry, input.intent);
  if (isErr(matched)) return matched;

  const skill = input.registry.find((s) => s.id === matched.value.skillId);
  if (!skill) {
    // Defensive: resolveTrigger drew from the same registry, so this only
    // fires if the caller hands us mutated state mid-call.
    return err(new NoSkillMatched(input.intent));
  }

  const supported = await llm.supports(skill.frontmatter.capabilities);
  if (!supported) {
    return err(
      new CapabilityMismatch(skill.id, skill.frontmatter.capabilities),
    );
  }

  await telemetry.emit({
    level: "audit",
    type: "skill.invoked",
    attributes: Object.freeze({
      skillId: skill.id,
      skillName: skill.frontmatter.name,
      tier: skill.frontmatter.tier,
      effort: skill.frontmatter.effort,
      score: matched.value.score,
      matchedTokens: matched.value.matchedTokens,
    }),
  });

  return ok(Object.freeze({ skill, match: matched.value }));
};
