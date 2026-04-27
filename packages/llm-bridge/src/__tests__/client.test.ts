import { afterEach, beforeEach, describe, expect, test } from "bun:test";

import { isErr, isOk } from "@ai-engineering/runtime";

import { LiteLLMBridgeClient } from "../client.ts";

// ---------------------------------------------------------------------------
// Fake bridge — a Bun.serve() instance that mirrors the Python bridge's wire
// shape just enough to drive the client through every code path. Each test
// instantiates its own fake so port allocation never collides.
// ---------------------------------------------------------------------------

interface FakeBridge {
  readonly url: string;
  readonly hits: ReadonlyArray<{
    path: string;
    method: string;
    auth: string | null;
  }>;
  readonly stop: () => void;
}

interface FakeBridgeOptions {
  readonly invokeStatus?: number;
  readonly invokeBody?: unknown;
  readonly capabilitiesBody?: unknown;
  readonly healthStatus?: number;
  readonly malformedJson?: boolean;
  readonly requireBearer?: boolean;
}

const TEST_TOKEN = "fake-bridge-test-bearer";

const JSON_HEADERS = { "content-type": "application/json" } as const;

function _jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), { status, headers: JSON_HEADERS });
}

function _healthHandler(opts: FakeBridgeOptions): Response {
  return _jsonResponse({ status: "ok", version: "test" }, opts.healthStatus ?? 200);
}

function _unauthorizedResponse(): Response {
  return _jsonResponse({ error: "unauth", message: "no token", retryable: false }, 401);
}

function _capabilitiesHandler(opts: FakeBridgeOptions): Response {
  const body = opts.capabilitiesBody ?? {
    "claude-opus-4-7": ["tool_use", "vision", "structured_output", "long_context"],
    "gpt-5": ["tool_use", "structured_output", "long_context"],
  };
  return _jsonResponse(body, 200);
}

function _invokeHandler(opts: FakeBridgeOptions): Response {
  const status = opts.invokeStatus ?? 200;
  if (opts.malformedJson === true) {
    return new Response("not-json", { status, headers: JSON_HEADERS });
  }
  const body = opts.invokeBody ?? {
    text: "hello",
    tokens_used: 50,
    cost_usd: 0.001,
    provider_id: "anthropic",
    model_id: "claude-opus-4-7",
    latency_ms: 12,
  };
  return _jsonResponse(body, status);
}

function _routeFakeRequest(
  req: Request,
  url: URL,
  opts: FakeBridgeOptions,
  authOk: boolean,
): Response {
  if (url.pathname === "/health") return _healthHandler(opts);
  if (!authOk) return _unauthorizedResponse();
  if (url.pathname === "/llm/capabilities") return _capabilitiesHandler(opts);
  if (url.pathname === "/llm/invoke" && req.method === "POST") {
    return _invokeHandler(opts);
  }
  return new Response("not-found", { status: 404 });
}

function startFakeBridge(opts: FakeBridgeOptions = {}): FakeBridge {
  const hits: Array<{ path: string; method: string; auth: string | null }> = [];
  const requireBearer = opts.requireBearer ?? true;
  const server = Bun.serve({
    port: 0, // ephemeral
    hostname: "127.0.0.1",
    fetch(req) {
      const url = new URL(req.url);
      const auth = req.headers.get("authorization");
      hits.push({ path: url.pathname, method: req.method, auth });
      const authOk = !requireBearer || auth === `Bearer ${TEST_TOKEN}`;
      return _routeFakeRequest(req, url, opts, authOk);
    },
  });
  return {
    url: `http://127.0.0.1:${server.port}`,
    hits,
    stop: () => {
      server.stop(true);
    },
  };
}

let bridge: FakeBridge | undefined;

afterEach(() => {
  bridge?.stop();
  bridge = undefined;
});

// ---------------------------------------------------------------------------
// invoke()
// ---------------------------------------------------------------------------

describe("LiteLLMBridgeClient — invoke", () => {
  test("happy path returns LLMResponse", async () => {
    bridge = startFakeBridge();
    const client = new LiteLLMBridgeClient({
      baseUrl: bridge.url,
      token: TEST_TOKEN,
    });
    const res = await client.invoke({
      skill: "specify",
      prompt: "Hi",
      capabilities: [],
      privacyTier: "standard",
    });
    expect(isOk(res)).toBe(true);
    if (isOk(res)) {
      expect(res.value.text).toBe("hello");
      expect(res.value.tokensUsed).toBe(50);
      expect(res.value.modelId).toBe("claude-opus-4-7");
      expect(res.value.providerId).toBe("anthropic");
      expect(res.value.latencyMs).toBe(12);
      expect(res.value.costUsd).toBe(0.001);
    }
    // The client must have sent the bearer header.
    const invokeHit = bridge.hits.find((h) => h.path === "/llm/invoke");
    expect(invokeHit).toBeDefined();
    expect(invokeHit?.auth).toBe(`Bearer ${TEST_TOKEN}`);
  });

  test("missing token causes server 401 -> non-retryable LLMError", async () => {
    bridge = startFakeBridge();
    const client = new LiteLLMBridgeClient({ baseUrl: bridge.url, token: "" });
    const res = await client.invoke({
      skill: "specify",
      prompt: "Hi",
      capabilities: [],
      privacyTier: "standard",
    });
    expect(isErr(res)).toBe(true);
    if (isErr(res)) {
      expect(res.error.retryable).toBe(false);
    }
  });

  test("server 429 maps to retryable LLMError", async () => {
    bridge = startFakeBridge({
      invokeStatus: 429,
      invokeBody: { error: "rate", message: "slow down", retryable: true },
    });
    const client = new LiteLLMBridgeClient({
      baseUrl: bridge.url,
      token: TEST_TOKEN,
    });
    const res = await client.invoke({
      skill: "specify",
      prompt: "Hi",
      capabilities: [],
      privacyTier: "standard",
    });
    expect(isErr(res)).toBe(true);
    if (isErr(res)) {
      expect(res.error.retryable).toBe(true);
      expect(res.error.message).toContain("slow down");
    }
  });

  test("server 400 (privacy violation) maps to non-retryable LLMError", async () => {
    bridge = startFakeBridge({
      invokeStatus: 400,
      invokeBody: {
        error: "PrivacyTierViolation",
        message: "primary route not permitted",
        retryable: false,
      },
    });
    const client = new LiteLLMBridgeClient({
      baseUrl: bridge.url,
      token: TEST_TOKEN,
    });
    const res = await client.invoke({
      skill: "specify",
      prompt: "Hi",
      capabilities: [],
      privacyTier: "strict",
    });
    expect(isErr(res)).toBe(true);
    if (isErr(res)) {
      expect(res.error.retryable).toBe(false);
      expect(res.error.message).toContain("not permitted");
    }
  });

  test("malformed JSON body yields non-retryable LLMError", async () => {
    bridge = startFakeBridge({ malformedJson: true });
    const client = new LiteLLMBridgeClient({
      baseUrl: bridge.url,
      token: TEST_TOKEN,
    });
    const res = await client.invoke({
      skill: "specify",
      prompt: "Hi",
      capabilities: [],
      privacyTier: "standard",
    });
    expect(isErr(res)).toBe(true);
    if (isErr(res)) expect(res.error.retryable).toBe(false);
  });

  test("transport error (unreachable host) yields retryable LLMError", async () => {
    // Use a port that is *almost certainly* not bound. We don't start a fake.
    const client = new LiteLLMBridgeClient({
      baseUrl: "http://127.0.0.1:1",
      token: TEST_TOKEN,
      requestTimeoutMs: 100,
    });
    const res = await client.invoke({
      skill: "specify",
      prompt: "Hi",
      capabilities: [],
      privacyTier: "standard",
    });
    expect(isErr(res)).toBe(true);
    if (isErr(res)) expect(res.error.retryable).toBe(true);
  });

  test("returns retryable error after heartbeat marks adapter unhealthy", async () => {
    bridge = startFakeBridge({ healthStatus: 503 });
    const client = new LiteLLMBridgeClient({
      baseUrl: bridge.url,
      token: TEST_TOKEN,
      heartbeatMissThreshold: 2,
    });
    // Two failed heartbeats trip the threshold.
    await client.heartbeatOnce();
    await client.heartbeatOnce();
    expect(client.isHealthy()).toBe(false);
    const res = await client.invoke({
      skill: "specify",
      prompt: "Hi",
      capabilities: [],
      privacyTier: "standard",
    });
    expect(isErr(res)).toBe(true);
    if (isErr(res)) expect(res.error.retryable).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// supports()
// ---------------------------------------------------------------------------

describe("LiteLLMBridgeClient — supports", () => {
  test("empty capabilities always returns true", async () => {
    bridge = startFakeBridge();
    const client = new LiteLLMBridgeClient({
      baseUrl: bridge.url,
      token: TEST_TOKEN,
    });
    expect(await client.supports([])).toBe(true);
  });

  test("returns true when at least one model offers the requested caps", async () => {
    bridge = startFakeBridge();
    const client = new LiteLLMBridgeClient({
      baseUrl: bridge.url,
      token: TEST_TOKEN,
    });
    expect(await client.supports(["tool_use", "vision"])).toBe(true);
  });

  test("returns false when no model offers the requested caps", async () => {
    bridge = startFakeBridge({
      capabilitiesBody: {
        "claude-opus-4-7": ["tool_use"],
        "gpt-5": ["streaming"],
      },
    });
    const client = new LiteLLMBridgeClient({
      baseUrl: bridge.url,
      token: TEST_TOKEN,
    });
    expect(await client.supports(["tool_use", "vision"])).toBe(false);
  });

  test("caches the matrix between calls", async () => {
    bridge = startFakeBridge();
    const client = new LiteLLMBridgeClient({
      baseUrl: bridge.url,
      token: TEST_TOKEN,
    });
    await client.supports(["tool_use"]);
    await client.supports(["vision"]);
    const capabilityHits = bridge.hits.filter((h) => h.path === "/llm/capabilities");
    expect(capabilityHits.length).toBe(1);
  });

  test("returns false when capabilities endpoint is unreachable", async () => {
    const client = new LiteLLMBridgeClient({
      baseUrl: "http://127.0.0.1:1",
      token: TEST_TOKEN,
      requestTimeoutMs: 100,
    });
    expect(await client.supports(["tool_use"])).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Heartbeat lifecycle
// ---------------------------------------------------------------------------

describe("LiteLLMBridgeClient — heartbeat lifecycle", () => {
  test("starts healthy", () => {
    const client = new LiteLLMBridgeClient({
      baseUrl: "http://127.0.0.1:1",
      token: TEST_TOKEN,
    });
    expect(client.isHealthy()).toBe(true);
  });

  test("single successful heartbeat keeps adapter healthy", async () => {
    bridge = startFakeBridge();
    const client = new LiteLLMBridgeClient({
      baseUrl: bridge.url,
      token: TEST_TOKEN,
    });
    expect(await client.heartbeatOnce()).toBe(true);
    expect(client.isHealthy()).toBe(true);
  });

  test("three consecutive misses mark the adapter unhealthy", async () => {
    bridge = startFakeBridge({ healthStatus: 500 });
    const client = new LiteLLMBridgeClient({
      baseUrl: bridge.url,
      token: TEST_TOKEN,
    });
    expect(await client.heartbeatOnce()).toBe(false);
    expect(client.isHealthy()).toBe(true);
    expect(await client.heartbeatOnce()).toBe(false);
    expect(client.isHealthy()).toBe(true);
    expect(await client.heartbeatOnce()).toBe(false);
    expect(client.isHealthy()).toBe(false);
  });

  test("a successful heartbeat resets the miss counter", async () => {
    let healthStatus = 500;
    let bodyOk = false;
    const server = Bun.serve({
      port: 0,
      hostname: "127.0.0.1",
      fetch(req) {
        const u = new URL(req.url);
        if (u.pathname === "/health") {
          return new Response("ok", { status: bodyOk ? 200 : healthStatus });
        }
        return new Response("nf", { status: 404 });
      },
    });
    try {
      const client = new LiteLLMBridgeClient({
        baseUrl: `http://127.0.0.1:${server.port}`,
        token: TEST_TOKEN,
        heartbeatMissThreshold: 3,
      });
      await client.heartbeatOnce();
      await client.heartbeatOnce();
      // Now flip to healthy mid-sequence.
      bodyOk = true;
      expect(await client.heartbeatOnce()).toBe(true);
      expect(client.isHealthy()).toBe(true);
      // Flip back to failing — threshold counts from 0 again.
      bodyOk = false;
      healthStatus = 500;
      await client.heartbeatOnce();
      expect(client.isHealthy()).toBe(true); // only 1 miss after reset
    } finally {
      server.stop(true);
    }
  });

  test("start() is idempotent and stop() clears the timer", async () => {
    bridge = startFakeBridge();
    const client = new LiteLLMBridgeClient({
      baseUrl: bridge.url,
      token: TEST_TOKEN,
      heartbeatIntervalMs: 1000,
    });
    client.start();
    client.start(); // second call is a no-op
    client.stop();
    client.stop(); // second stop is a no-op
    // After stop(), the timer is gone — we can't easily observe that
    // directly, but we can confirm subsequent heartbeats still work.
    expect(await client.heartbeatOnce()).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Wire-shape sanity checks
// ---------------------------------------------------------------------------

describe("LiteLLMBridgeClient — wire shape", () => {
  test("invoke posts JSON with snake_case keys mapping camelCase", async () => {
    let capturedBody = "";
    const server = Bun.serve({
      port: 0,
      hostname: "127.0.0.1",
      async fetch(req) {
        if (req.method === "POST" && req.url.endsWith("/llm/invoke")) {
          capturedBody = await req.text();
          return new Response(
            JSON.stringify({
              text: "ok",
              tokens_used: 1,
              cost_usd: 0,
              provider_id: "anthropic",
              model_id: "claude-opus-4-7",
              latency_ms: 0,
            }),
            { status: 200, headers: { "content-type": "application/json" } },
          );
        }
        return new Response("nf", { status: 404 });
      },
    });
    try {
      const client = new LiteLLMBridgeClient({
        baseUrl: `http://127.0.0.1:${server.port}`,
        token: TEST_TOKEN,
      });
      await client.invoke({
        skill: "specify",
        prompt: "hello",
        capabilities: ["tool_use"],
        privacyTier: "strict",
      });
    } finally {
      server.stop(true);
    }
    const parsed = JSON.parse(capturedBody) as {
      skill: string;
      prompt: string;
      capabilities: string[];
      privacy_tier: string;
    };
    expect(parsed.skill).toBe("specify");
    expect(parsed.prompt).toBe("hello");
    expect(parsed.capabilities).toEqual(["tool_use"]);
    expect(parsed.privacy_tier).toBe("strict");
  });
});

beforeEach(() => {
  // Reset env so per-test `token` overrides aren't shadowed by the default.
  process.env.AI_ENGINEERING_BRIDGE_TOKEN = undefined;
});
