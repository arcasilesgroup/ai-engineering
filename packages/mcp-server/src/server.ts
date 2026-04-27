import { AGENT_URI_PREFIX, listAgentResources, readAgentResource } from "./handlers/agents.ts";
import {
  acceptRiskTool,
  callAcceptRisk,
  callRunReleaseGate,
  runReleaseGateTool,
} from "./handlers/governance.ts";
import { SKILL_URI_PREFIX, listSkillResources, readSkillResource } from "./handlers/skills.ts";
import {
  INTERNAL_ERROR,
  INVALID_PARAMS,
  INVALID_REQUEST,
  type JsonRpcId,
  type JsonRpcResponse,
  METHOD_NOT_FOUND,
  PARSE_ERROR,
  type Prompt,
  type PromptResult,
  type Resource,
  type Tool,
  failure,
  parseEnvelope,
  success,
} from "./jsonrpc.ts";
import type { ServerDeps } from "./ports.ts";

export type { ServerDeps } from "./ports.ts";

/**
 * MCP server — Streamable HTTP, stateless (ADR-0003).
 *
 * `createServer` returns a `(req: Request) => Promise<Response>` handler.
 * The factory has no dependency on `Bun.serve` — it accepts a Web `Request`
 * and returns a Web `Response`, so it composes with any runtime that
 * speaks the Fetch API. `main.ts` is the ONLY file that imports
 * `Bun.serve` directly.
 *
 * Routing:
 *   - POST `/jsonrpc`  → JSON-RPC 2.0 dispatch
 *   - GET  `/sse`      → server-sent events (placeholder; not implemented
 *                        in this phase — returns 501)
 *   - any other path   → 404
 *
 * Auth: bearer-token middleware. Empty/missing token → 401 + audit event.
 * Phase 7 plugin trust expands this with CIMD/DCR + ServerCard metadata.
 *
 * Statelessness: createServer is a pure function. No module-level
 * caches, no shared sessions. Each invocation gets the deps closure
 * passed at construction; per-request state lives in the request object.
 */
const PROTOCOL_VERSION = "2024-11-05";
const SERVER_INFO = Object.freeze({
  name: "ai-engineering",
  version: "3.0.0-alpha.0",
});

const FRAMEWORK_CONSTITUTION_PROMPT = "framework_constitution";

type Handler = (req: Request) => Promise<Response>;

export const createServer = (deps: ServerDeps): Handler => {
  return async (req: Request): Promise<Response> => {
    const url = new URL(req.url);

    if (url.pathname === "/jsonrpc") {
      if (req.method !== "POST") {
        return new Response("Method Not Allowed", {
          status: 405,
          headers: { Allow: "POST" },
        });
      }
      return handleJsonRpc(req, deps);
    }

    if (url.pathname === "/sse") {
      // Streamable HTTP SSE channel is optional in MCP. Stub for now;
      // Phase 7 plugin trust will wire OAuth + ServerCard metadata.
      return new Response("Not Implemented", { status: 501 });
    }

    if (url.pathname === "/health") {
      return Response.json({ status: "ok", server: SERVER_INFO });
    }

    return new Response("Not Found", { status: 404 });
  };
};

const handleJsonRpc = async (req: Request, deps: ServerDeps): Promise<Response> => {
  const auth = req.headers.get("authorization") ?? "";
  const token = extractBearerToken(auth);
  if (token === null) {
    await deps.telemetry.emit({
      level: "audit",
      type: "mcp.unauthenticated",
      attributes: { method: req.method, url: req.url },
    });
    return new Response("Unauthorized", {
      status: 401,
      headers: { "WWW-Authenticate": "Bearer" },
    });
  }

  const raw = await req.text();
  const envelope = parseEnvelope(raw);
  if (envelope === null) {
    return jsonResponse(failure(null, PARSE_ERROR, "Parse error"));
  }
  const id: JsonRpcId = envelope.id ?? null;

  if (envelope.jsonrpc !== "2.0") {
    return jsonResponse(failure(id, INVALID_REQUEST, 'jsonrpc must be "2.0"'));
  }

  await deps.telemetry.emit({
    level: "info",
    type: "mcp.request",
    attributes: { method: envelope.method, tokenLen: token.length },
  });

  try {
    const response = await dispatch(envelope.method, envelope.params, deps, id);
    return jsonResponse(response);
  } catch (cause) {
    const message = cause instanceof Error ? cause.message : String(cause);
    await deps.telemetry.emit({
      level: "error",
      type: "mcp.internal_error",
      attributes: { method: envelope.method, message },
    });
    return jsonResponse(failure(id, INTERNAL_ERROR, message));
  }
};

const extractBearerToken = (authHeader: string): string | null => {
  const match = /^Bearer\s+(\S+)$/i.exec(authHeader.trim());
  if (!match) return null;
  const token = match[1] ?? "";
  return token.length === 0 ? null : token;
};

const jsonResponse = (body: JsonRpcResponse): Response =>
  new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });

const dispatch = async (
  method: string,
  params: Record<string, unknown> | undefined,
  deps: ServerDeps,
  id: JsonRpcId,
): Promise<JsonRpcResponse> => {
  switch (method) {
    case "initialize":
      return success(id, {
        protocolVersion: PROTOCOL_VERSION,
        serverInfo: SERVER_INFO,
        capabilities: {
          resources: { subscribe: false, listChanged: false },
          tools: { listChanged: false },
          prompts: { listChanged: false },
        },
      });

    case "ping":
      return success(id, {});

    case "resources/list":
      return success(id, {
        resources: await collectResources(deps),
      });

    case "resources/read":
      return readResource(id, params, deps);

    case "tools/list":
      return success(id, { tools: listTools() });

    case "tools/call":
      return callTool(id, params, deps);

    case "prompts/list":
      return success(id, { prompts: listPrompts() });

    case "prompts/get":
      return getPrompt(id, params, deps);

    default:
      return failure(id, METHOD_NOT_FOUND, `Method not found: ${method}`);
  }
};

const collectResources = async (deps: ServerDeps): Promise<ReadonlyArray<Resource>> => {
  const [skills, agents] = await Promise.all([
    listSkillResources(deps.skills),
    listAgentResources(deps.agents),
  ]);
  return [
    ...skills,
    ...agents,
    {
      uri: "ai-engineering://manifest",
      name: "manifest",
      description: "Parsed framework manifest (ai-engineering.toml)",
      mimeType: "application/json",
    },
    {
      uri: "ai-engineering://decisions",
      name: "decisions",
      description: "Active risk acceptances (logged-acceptance, not weakening)",
      mimeType: "application/json",
    },
  ];
};

const readResource = async (
  id: JsonRpcId,
  params: Record<string, unknown> | undefined,
  deps: ServerDeps,
): Promise<JsonRpcResponse> => {
  const uri = typeof params?.uri === "string" ? (params.uri as string) : "";
  if (uri.length === 0) {
    return failure(id, INVALID_PARAMS, 'resources/read requires "uri"');
  }
  if (uri.startsWith(SKILL_URI_PREFIX)) {
    const r = await readSkillResource(uri, deps.skills);
    return r.ok ? success(id, { contents: r.contents }) : failure(id, r.code, r.message);
  }
  if (uri.startsWith(AGENT_URI_PREFIX)) {
    const r = await readAgentResource(uri, deps.agents);
    return r.ok ? success(id, { contents: r.contents }) : failure(id, r.code, r.message);
  }
  if (uri === "ai-engineering://manifest") {
    const data = await deps.manifest.load();
    return success(id, {
      contents: [
        {
          uri,
          mimeType: "application/json",
          text: JSON.stringify(data),
        },
      ],
    });
  }
  if (uri === "ai-engineering://decisions") {
    const list = await deps.decisions.list();
    return success(id, {
      contents: [
        {
          uri,
          mimeType: "application/json",
          text: JSON.stringify(list),
        },
      ],
    });
  }
  return failure(id, INVALID_PARAMS, `Unknown resource URI: ${uri}`);
};

const listSkillsTool: Tool = Object.freeze({
  name: "list_skills",
  description: "Enumerate skills exposed by this MCP server.",
  inputSchema: {
    type: "object",
    properties: {},
    additionalProperties: false,
  },
});

const listTools = (): ReadonlyArray<Tool> => [acceptRiskTool, runReleaseGateTool, listSkillsTool];

const callTool = async (
  id: JsonRpcId,
  params: Record<string, unknown> | undefined,
  deps: ServerDeps,
): Promise<JsonRpcResponse> => {
  const name = typeof params?.name === "string" ? (params.name as string) : "";
  const args = (params?.arguments ?? {}) as Record<string, unknown>;

  switch (name) {
    case "accept_risk": {
      const r = await callAcceptRisk(args, deps.decisions);
      return r.ok ? success(id, r.result) : failure(id, r.code, r.message);
    }
    case "run_release_gate": {
      const result = await callRunReleaseGate(deps.runReleaseGate);
      return success(id, result);
    }
    case "list_skills": {
      const skills = await deps.skills.list();
      return success(id, {
        content: [
          {
            type: "text",
            text: JSON.stringify(skills),
          },
        ],
      });
    }
    default:
      return failure(id, INVALID_PARAMS, `Unknown tool: ${name}`);
  }
};

const listPrompts = (): ReadonlyArray<Prompt> => [
  {
    name: FRAMEWORK_CONSTITUTION_PROMPT,
    description:
      "Returns CONSTITUTION.md verbatim — the source of governance for every skill and agent.",
  },
];

const getPrompt = async (
  id: JsonRpcId,
  params: Record<string, unknown> | undefined,
  deps: ServerDeps,
): Promise<JsonRpcResponse> => {
  const name = typeof params?.name === "string" ? (params.name as string) : "";
  if (name !== FRAMEWORK_CONSTITUTION_PROMPT) {
    return failure(id, INVALID_PARAMS, `Unknown prompt: ${name}`);
  }
  const result: PromptResult = {
    description: "Framework constitution (verbatim)",
    messages: [
      {
        role: "system",
        content: { type: "text", text: deps.constitution },
      },
    ],
  };
  return success(id, result);
};
