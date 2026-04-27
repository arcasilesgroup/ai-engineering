import { INVALID_PARAMS, type Resource, type ResourceContent } from "../jsonrpc.ts";
import type { AgentCatalogPort } from "../ports.ts";

/**
 * Agents handler — exposes `ai-engineering://agents/{name}` resources.
 *
 * Mirrors the skills handler shape so consumers can treat skills/agents
 * uniformly when listing the framework's executable surface.
 */
export const AGENT_URI_PREFIX = "ai-engineering://agents/";

export const listAgentResources = async (
  port: AgentCatalogPort,
): Promise<ReadonlyArray<Resource>> => {
  const agents = await port.list();
  return agents.map((a) => ({
    uri: a.uri,
    name: a.name,
    description: `AGENT.md for ${a.name}`,
    mimeType: "text/markdown",
  }));
};

export const readAgentResource = async (
  uri: string,
  port: AgentCatalogPort,
): Promise<
  | { ok: true; contents: ReadonlyArray<ResourceContent> }
  | { ok: false; code: number; message: string }
> => {
  const name = uri.slice(AGENT_URI_PREFIX.length);
  if (name.length === 0 || name.includes("/")) {
    return {
      ok: false,
      code: INVALID_PARAMS,
      message: `Invalid agent URI: ${uri}`,
    };
  }
  const body = await port.read(name);
  if (body === null) {
    return {
      ok: false,
      code: INVALID_PARAMS,
      message: `Agent not found: ${name}`,
    };
  }
  return {
    ok: true,
    contents: [{ uri, mimeType: "text/markdown", text: body }],
  };
};
