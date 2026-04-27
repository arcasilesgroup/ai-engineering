// Public surface of @ai-engineering/mcp-server.
//
// Hexagonal layers:
//   - jsonrpc       — JSON-RPC 2.0 envelope primitives (no transport)
//   - ports         — driven port interfaces (catalogs, decisions, manifest)
//   - handlers/*    — pure dispatch logic per MCP capability
//   - server        — composes handlers behind a Fetch handler
//   - main          — Bun.serve entry point (the only Bun-bound module)
//
// The server is stateless per ADR-0003: every request validates its own
// bearer token, no in-memory session map. Compatible with horizontal
// scaling and SSO-integrated load balancers.

export { createServer, type ServerDeps } from "./server.ts";
export type {
  AcceptRiskCommand,
  AgentCatalogPort,
  DecisionsPort,
  ManifestPort,
  RunReleaseGateFn,
  SkillCatalogPort,
} from "./ports.ts";
export {
  failure,
  INTERNAL_ERROR,
  INVALID_PARAMS,
  INVALID_REQUEST,
  METHOD_NOT_FOUND,
  PARSE_ERROR,
  parseEnvelope,
  success,
  type JsonRpcError,
  type JsonRpcId,
  type JsonRpcRequest,
  type JsonRpcResponse,
  type JsonRpcSuccess,
  type Prompt,
  type PromptResult,
  type Resource,
  type ResourceContent,
  type Tool,
  type ToolResult,
} from "./jsonrpc.ts";
export {
  AGENT_URI_PREFIX,
  listAgentResources,
  readAgentResource,
} from "./handlers/agents.ts";
export {
  acceptRiskTool,
  callAcceptRisk,
  callRunReleaseGate,
  runReleaseGateTool,
} from "./handlers/governance.ts";
export {
  SKILL_URI_PREFIX,
  listSkillResources,
  readSkillResource,
} from "./handlers/skills.ts";
