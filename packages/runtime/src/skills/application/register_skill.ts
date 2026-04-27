import * as yaml from "js-yaml";

import {
  type IOError,
  type Result,
  type SkillId,
  ValidationError,
  err,
  isErr,
} from "../../shared/kernel/index.ts";
import type { FilesystemPort } from "../../shared/ports/filesystem.ts";
import type { LLMCapability } from "../../shared/ports/llm.ts";
import {
  type Skill,
  type SkillEffort,
  type SkillFrontmatter,
  type SkillTier,
  createSkill,
} from "../domain/skill.ts";
import { validateManifest } from "../../governance/application/validate_manifest.ts";

/**
 * RegisterSkill — load a SKILL.md from the filesystem, parse YAML
 * frontmatter, validate it against the canonical skill schema, and return
 * a frozen Skill domain entity.
 *
 * Constitution Article V: skills live ONCE in `skills/catalog/<name>/SKILL.md`.
 * Mirrors are generated; the registration use case only ever reads the
 * canonical location through `FilesystemPort` so the same code path serves
 * production, tests, and remote attestation-locked filesystems.
 */
const FRONTMATTER_RE = /^---\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)$/;

export interface RegisterSkillInput {
  readonly id: SkillId;
  readonly path: string;
}

export const registerSkill = async (
  input: RegisterSkillInput,
  fs: FilesystemPort,
): Promise<Result<Skill, ValidationError | IOError>> => {
  const read = await fs.read(input.path);
  if (isErr(read)) return read;

  const match = FRONTMATTER_RE.exec(read.value);
  if (!match) {
    return err(
      new ValidationError(
        `SKILL.md at ${input.path} is missing YAML frontmatter (--- header)`,
        "frontmatter",
      ),
    );
  }
  const frontmatterRaw = match[1] ?? "";
  const body = match[2] ?? "";

  let parsed: unknown;
  try {
    parsed = yaml.load(frontmatterRaw);
  } catch (cause) {
    return err(
      new ValidationError(
        `Failed to parse YAML frontmatter at ${input.path}: ${
          cause instanceof Error ? cause.message : String(cause)
        }`,
        "frontmatter",
      ),
    );
  }

  const validated = validateManifest(parsed, "skill");
  if (isErr(validated)) return validated;

  const manifest = validated.value;
  const frontmatter: SkillFrontmatter = Object.freeze({
    name: manifest.name,
    description: manifest.description,
    effort: manifest.effort as SkillEffort,
    tier: manifest.tier as SkillTier,
    capabilities: Object.freeze([
      ...(manifest.capabilities ?? []),
    ] as LLMCapability[]),
    ...(manifest.modelClass !== undefined
      ? { modelClass: manifest.modelClass }
      : {}),
    ...(manifest.handlers !== undefined
      ? { handlers: Object.freeze([...manifest.handlers]) }
      : {}),
    ...(manifest.governance !== undefined
      ? {
          governance: Object.freeze({
            blocking: manifest.governance.blocking ?? false,
          }),
        }
      : {}),
  });

  const hashResult = await fs.hash(input.path);
  if (isErr(hashResult)) return hashResult;

  return createSkill({
    id: input.id,
    frontmatter,
    body,
    contentHash: hashResult.value,
  });
};

export const __TEST_ONLY__ = Object.freeze({ FRONTMATTER_RE });
