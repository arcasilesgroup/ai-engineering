import { INVALID_PARAMS, type Resource, type ResourceContent } from "../jsonrpc.ts";
import type { SkillCatalogPort } from "../ports.ts";

/**
 * Skills handler — exposes `ai-engineering://skills/{name}` resources.
 *
 * Resource URI scheme: `ai-engineering://skills/<name>` returns the raw
 * SKILL.md content (frontmatter + body). Discovery happens via
 * `resources/list`; full read via `resources/read`.
 */
export const SKILL_URI_PREFIX = "ai-engineering://skills/";

export const listSkillResources = async (
  port: SkillCatalogPort,
): Promise<ReadonlyArray<Resource>> => {
  const skills = await port.list();
  return skills.map((s) => ({
    uri: s.uri,
    name: s.name,
    description: `SKILL.md for /ai-${s.name}`,
    mimeType: "text/markdown",
  }));
};

export const readSkillResource = async (
  uri: string,
  port: SkillCatalogPort,
): Promise<
  | { ok: true; contents: ReadonlyArray<ResourceContent> }
  | { ok: false; code: number; message: string }
> => {
  const name = uri.slice(SKILL_URI_PREFIX.length);
  if (name.length === 0 || name.includes("/")) {
    return {
      ok: false,
      code: INVALID_PARAMS,
      message: `Invalid skill URI: ${uri}`,
    };
  }
  const body = await port.read(name);
  if (body === null) {
    return {
      ok: false,
      code: INVALID_PARAMS,
      message: `Skill not found: ${name}`,
    };
  }
  return {
    ok: true,
    contents: [{ uri, mimeType: "text/markdown", text: body }],
  };
};
