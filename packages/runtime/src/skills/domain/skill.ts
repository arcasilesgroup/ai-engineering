import {
  type SkillId,
  ValidationError,
  type Result,
  ok,
  err,
} from "../../shared/kernel/index.ts";
import type { LLMCapability } from "../../shared/ports/llm.ts";

/**
 * Skill — an executable contract written as Markdown with frontmatter.
 *
 * Skills are SOPs (Standard Operating Procedures) — verbs the user invokes
 * via slash commands (/ai-specify, /ai-plan, /ai-implement, …).
 *
 * Compatible with Anthropic Agent Skills spec (lowercase + hyphens, max
 * 64 chars name, max 1024 chars description).
 *
 * Trade-off: kept as a pure data class (anaemic on purpose) because the
 * actual SKILL.md content is plain Markdown — behavior lives in the
 * application layer (InvokeSkill use case).
 */

export type SkillEffort = "max" | "high" | "medium" | "low";
export type SkillTier = "core" | "regulated" | "plugin";

export interface SkillFrontmatter {
  readonly name: string;
  readonly description: string;
  readonly effort: SkillEffort;
  readonly tier: SkillTier;
  readonly capabilities: ReadonlyArray<LLMCapability>;
  readonly modelClass?: string;
  readonly handlers?: ReadonlyArray<string>;
  readonly governance?: { readonly blocking: boolean };
}

export interface Skill {
  readonly id: SkillId;
  readonly frontmatter: SkillFrontmatter;
  readonly body: string;
  readonly contentHash: string;
}

const NAME_RE = /^[a-z][a-z0-9-]{0,63}$/;
const MAX_DESCRIPTION_LEN = 1024;

export const createSkill = (input: {
  id: SkillId;
  frontmatter: SkillFrontmatter;
  body: string;
  contentHash: string;
}): Result<Skill, ValidationError> => {
  if (!NAME_RE.test(input.frontmatter.name)) {
    return err(
      new ValidationError(
        `Skill name must be lowercase alphanumeric with hyphens, max 64 chars: "${input.frontmatter.name}"`,
        "name",
      ),
    );
  }
  if (input.frontmatter.description.length === 0) {
    return err(
      new ValidationError("Skill description cannot be empty", "description"),
    );
  }
  if (input.frontmatter.description.length > MAX_DESCRIPTION_LEN) {
    return err(
      new ValidationError(
        `Skill description exceeds max ${MAX_DESCRIPTION_LEN} chars (got ${input.frontmatter.description.length})`,
        "description",
      ),
    );
  }
  if (input.body.trim().length === 0) {
    return err(new ValidationError("Skill body cannot be empty", "body"));
  }
  return ok(
    Object.freeze({ ...input, frontmatter: Object.freeze(input.frontmatter) }),
  );
};
