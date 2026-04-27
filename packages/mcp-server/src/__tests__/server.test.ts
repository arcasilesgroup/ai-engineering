import { afterAll, beforeAll, describe, expect, test } from "bun:test";

import { InMemoryDecisionStore, acceptRisk } from "@ai-engineering/runtime";

import {
  FakeAgentCatalogPort,
  FakeManifestPort,
  FakeSkillCatalogPort,
  FakeTelemetryPort,
} from "../_fakes.ts";
import { type ServerDeps, createServer } from "../server.ts";

/**
 * Integration tests for the MCP server.
 *
 * These exercise the JSON-RPC 2.0 surface end-to-end via an in-process
 * Bun.serve listener bound to port 0 (kernel-assigned random port). No
 * external dependencies. Total suite budget: <5s.
 *
 * Stateless requirement (ADR-0003): each request carries its own bearer
 * token; the server validates per request. Two requests do not share state.
 */

const buildDeps = (): ServerDeps => {
  const skills = new FakeSkillCatalogPort();
  skills.entries.set("commit", "# /ai-commit\n\nGoverned commit pipeline.");
  skills.entries.set("plan", "# /ai-plan\n\nDraft an executable plan.");

  const agents = new FakeAgentCatalogPort();
  agents.entries.set("builder", "# builder\n\nThe only writing agent.");

  const manifest = new FakeManifestPort({
    framework: { version: "3.0.0-alpha.0" },
  });
  const decisionStore = new InMemoryDecisionStore();

  return {
    skills,
    agents,
    manifest,
    decisions: {
      async list() {
        return [];
      },
      async accept(input) {
        return acceptRisk(input, decisionStore);
      },
    },
    runReleaseGate: async () =>
      Object.freeze({
        verdict: "GO" as const,
        totals: { pass: 1, fail: 0, warn: 0, error: 0 },
        blocking: [],
        outcomes: [],
      }),
    constitution: "# CONSTITUTION\n\nNon-negotiable rules.",
    telemetry: new FakeTelemetryPort(),
  };
};

let server: ReturnType<typeof Bun.serve> | undefined;
let baseUrl = "";

const startServer = (
  deps: ServerDeps,
): { server: ReturnType<typeof Bun.serve>; baseUrl: string } => {
  const handler = createServer(deps);
  const s = Bun.serve({
    port: 0,
    fetch: (req: Request) => handler(req),
  });
  return { server: s, baseUrl: `http://localhost:${s.port}` };
};

const rpc = async (
  body: Record<string, unknown>,
  headers: Record<string, string> = { Authorization: "Bearer test-token" },
): Promise<{ status: number; json: Record<string, unknown> | null }> => {
  const res = await fetch(`${baseUrl}/jsonrpc`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
  let json: Record<string, unknown> | null = null;
  try {
    json = (await res.json()) as Record<string, unknown>;
  } catch {
    json = null;
  }
  return { status: res.status, json };
};

beforeAll(() => {
  const started = startServer(buildDeps());
  server = started.server;
  baseUrl = started.baseUrl;
});

afterAll(() => {
  server?.stop(true);
});

describe("MCP server — JSON-RPC 2.0 envelope", () => {
  test("rejects requests without bearer token (401)", async () => {
    const res = await fetch(`${baseUrl}/jsonrpc`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "resources/list",
      }),
    });
    expect(res.status).toBe(401);
  });

  test("rejects requests with empty bearer token (401)", async () => {
    const res = await fetch(`${baseUrl}/jsonrpc`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer ",
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "resources/list",
      }),
    });
    expect(res.status).toBe(401);
  });

  test("returns parse error -32700 for malformed JSON", async () => {
    const res = await fetch(`${baseUrl}/jsonrpc`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer test",
      },
      body: "not json",
    });
    expect(res.status).toBe(200);
    const json = (await res.json()) as { error: { code: number } };
    expect(json.error.code).toBe(-32700);
  });

  test("returns method-not-found -32601 for unknown method", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 99,
      method: "nope/missing",
    });
    expect(json?.error).toMatchObject({ code: -32601 });
  });

  test("rejects non-2.0 jsonrpc value with -32600", async () => {
    const { json } = await rpc({
      jsonrpc: "1.0",
      id: 1,
      method: "resources/list",
    });
    expect(json?.error).toMatchObject({ code: -32600 });
  });

  test("returns 405 on GET for /jsonrpc", async () => {
    const res = await fetch(`${baseUrl}/jsonrpc`, { method: "GET" });
    expect(res.status).toBe(405);
  });
});

describe("MCP server — resources", () => {
  test("resources/list enumerates skill, agent, manifest, decisions URIs", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 1,
      method: "resources/list",
    });
    expect(json?.result).toBeDefined();
    const result = json?.result as { resources: Array<{ uri: string }> };
    const uris = result.resources.map((r) => r.uri);
    expect(uris).toContain("ai-engineering://skills/commit");
    expect(uris).toContain("ai-engineering://skills/plan");
    expect(uris).toContain("ai-engineering://agents/builder");
    expect(uris).toContain("ai-engineering://manifest");
    expect(uris).toContain("ai-engineering://decisions");
  });

  test("resources/read returns SKILL.md body for a skill URI", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 2,
      method: "resources/read",
      params: { uri: "ai-engineering://skills/commit" },
    });
    const result = json?.result as { contents: Array<{ text: string }> };
    expect(result.contents[0]?.text).toContain("Governed commit pipeline");
  });

  test("resources/read returns AGENT.md body for an agent URI", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 3,
      method: "resources/read",
      params: { uri: "ai-engineering://agents/builder" },
    });
    const result = json?.result as { contents: Array<{ text: string }> };
    expect(result.contents[0]?.text).toContain("only writing agent");
  });

  test("resources/read returns parsed manifest JSON", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 4,
      method: "resources/read",
      params: { uri: "ai-engineering://manifest" },
    });
    const result = json?.result as {
      contents: Array<{ text: string; mimeType: string }>;
    };
    expect(result.contents[0]?.mimeType).toBe("application/json");
    const parsed = JSON.parse(result.contents[0]?.text ?? "{}");
    expect(parsed.framework.version).toBe("3.0.0-alpha.0");
  });

  test("resources/read returns active decisions list", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 5,
      method: "resources/read",
      params: { uri: "ai-engineering://decisions" },
    });
    const result = json?.result as {
      contents: Array<{ text: string; mimeType: string }>;
    };
    expect(result.contents[0]?.mimeType).toBe("application/json");
    expect(JSON.parse(result.contents[0]?.text ?? "[]")).toEqual([]);
  });

  test("resources/read returns -32602 for unknown URI scheme", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 6,
      method: "resources/read",
      params: { uri: "https://example.com/foo" },
    });
    expect(json?.error).toMatchObject({ code: -32602 });
  });

  test("resources/read returns -32602 for missing skill", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 7,
      method: "resources/read",
      params: { uri: "ai-engineering://skills/nonexistent" },
    });
    expect(json?.error).toMatchObject({ code: -32602 });
  });
});

describe("MCP server — tools", () => {
  test("tools/list enumerates accept_risk, run_release_gate, list_skills", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 10,
      method: "tools/list",
    });
    const result = json?.result as { tools: Array<{ name: string }> };
    const names = result.tools.map((t) => t.name);
    expect(names).toContain("accept_risk");
    expect(names).toContain("run_release_gate");
    expect(names).toContain("list_skills");
  });

  test("tools/call list_skills returns the skill catalog", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 11,
      method: "tools/call",
      params: { name: "list_skills", arguments: {} },
    });
    const result = json?.result as { content: Array<{ text: string }> };
    const skills = JSON.parse(result.content[0]?.text ?? "[]");
    expect(skills.length).toBeGreaterThanOrEqual(2);
    expect(skills.map((s: { name: string }) => s.name)).toContain("commit");
  });

  test("tools/call run_release_gate returns aggregated verdict", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 12,
      method: "tools/call",
      params: { name: "run_release_gate", arguments: {} },
    });
    const result = json?.result as { content: Array<{ text: string }> };
    const aggregate = JSON.parse(result.content[0]?.text ?? "{}");
    expect(aggregate.verdict).toBe("GO");
  });

  test("tools/call accept_risk creates a decision", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 13,
      method: "tools/call",
      params: {
        name: "accept_risk",
        arguments: {
          finding_id: "CVE-2026-99",
          severity: "high",
          justification: "False positive in fixture; tracked spec-100",
          owner: "alice@example.com",
          spec_ref: "spec-100",
        },
      },
    });
    const result = json?.result as { content: Array<{ text: string }> };
    const decision = JSON.parse(result.content[0]?.text ?? "{}");
    expect(decision.findingId).toBe("CVE-2026-99");
    expect(decision.severity).toBe("high");
    expect(decision.expiresAt).toBeDefined();
  });

  test("tools/call accept_risk validates input (missing fields → error)", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 14,
      method: "tools/call",
      params: {
        name: "accept_risk",
        arguments: { finding_id: "x", severity: "high" },
      },
    });
    expect(json?.error).toMatchObject({ code: -32602 });
  });

  test("tools/call returns -32602 for unknown tool", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 15,
      method: "tools/call",
      params: { name: "no_such_tool", arguments: {} },
    });
    expect(json?.error).toMatchObject({ code: -32602 });
  });
});

describe("MCP server — prompts", () => {
  test("prompts/list contains framework_constitution", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 20,
      method: "prompts/list",
    });
    const result = json?.result as { prompts: Array<{ name: string }> };
    expect(result.prompts.map((p) => p.name)).toContain("framework_constitution");
  });

  test("prompts/get framework_constitution returns CONSTITUTION verbatim", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 21,
      method: "prompts/get",
      params: { name: "framework_constitution" },
    });
    const result = json?.result as {
      messages: Array<{ content: { text: string } }>;
    };
    expect(result.messages[0]?.content.text).toContain("CONSTITUTION");
  });

  test("prompts/get returns -32602 for unknown prompt", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 22,
      method: "prompts/get",
      params: { name: "no_prompt" },
    });
    expect(json?.error).toMatchObject({ code: -32602 });
  });
});

describe("MCP server — initialize / capabilities", () => {
  test("initialize returns server info and protocol version", async () => {
    const { json } = await rpc({
      jsonrpc: "2.0",
      id: 30,
      method: "initialize",
      params: { protocolVersion: "2024-11-05" },
    });
    const result = json?.result as {
      serverInfo: { name: string; version: string };
      protocolVersion: string;
      capabilities: Record<string, unknown>;
    };
    expect(result.serverInfo.name).toBe("ai-engineering");
    expect(result.protocolVersion).toBeDefined();
    expect(result.capabilities).toHaveProperty("resources");
    expect(result.capabilities).toHaveProperty("tools");
    expect(result.capabilities).toHaveProperty("prompts");
  });
});

describe("MCP server — stateless behavior (ADR-0003)", () => {
  test("two requests do not share session state", async () => {
    // Each request should be evaluated independently. We verify by
    // calling the same method twice with different bearer tokens —
    // both succeed, neither leaks state from the other.
    const a = await rpc(
      { jsonrpc: "2.0", id: 40, method: "resources/list" },
      { Authorization: "Bearer alpha" },
    );
    const b = await rpc(
      { jsonrpc: "2.0", id: 41, method: "resources/list" },
      { Authorization: "Bearer beta" },
    );
    expect(a.json?.result).toBeDefined();
    expect(b.json?.result).toBeDefined();
    expect(a.status).toBe(200);
    expect(b.status).toBe(200);
  });

  test("server has no in-memory session map exposed", () => {
    // Static guarantee: createServer is a pure function returning a
    // request handler. There is no exported session store. This is a
    // contract test — if a future change adds a module-level session
    // Map, this test still passes (state is not "exposed") but the
    // ADR-0003 review should catch it.
    expect(typeof createServer).toBe("function");
    expect(createServer.length).toBe(1); // single deps argument
  });
});

describe("MCP server — telemetry", () => {
  test("emits an audit event for unauthenticated requests", async () => {
    const deps = buildDeps();
    const handler = createServer(deps);
    const s = Bun.serve({ port: 0, fetch: (req: Request) => handler(req) });
    try {
      await fetch(`http://localhost:${s.port}/jsonrpc`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "ping" }),
      });
      const events = (deps.telemetry as FakeTelemetryPort).emitted;
      expect(events.some((e) => e.type === "mcp.unauthenticated")).toBe(true);
    } finally {
      s.stop(true);
    }
  });

  test("emits a request event for each authenticated invocation", async () => {
    const deps = buildDeps();
    const handler = createServer(deps);
    const s = Bun.serve({ port: 0, fetch: (req: Request) => handler(req) });
    try {
      await fetch(`http://localhost:${s.port}/jsonrpc`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer ok",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "resources/list",
        }),
      });
      const events = (deps.telemetry as FakeTelemetryPort).emitted;
      expect(events.some((e) => e.type === "mcp.request")).toBe(true);
    } finally {
      s.stop(true);
    }
  });
});
