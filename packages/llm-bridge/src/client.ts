import { type Result, err, ok } from "@ai-engineering/runtime";
import {
  type LLMCapability,
  LLMError,
  type LLMPort,
  type LLMRequest,
  type LLMResponse,
} from "@ai-engineering/runtime";

/**
 * LiteLLMBridgeClient — TypeScript LLMPort impl over HTTP loopback.
 *
 * Talks to the Python bridge at `http://127.0.0.1:<port>` (Docker-isolated;
 * see ADR-0008). Subscription Piggyback (ADR-0005, Article IV): this client
 * is **Layer 3 only** — Layer 2 default flows delegate to the IDE host and
 * never construct this object.
 *
 * Key properties:
 *   - Bearer-token auth from `AI_ENGINEERING_BRIDGE_TOKEN`. The token is
 *     read at construction; the env var is NOT re-read mid-session.
 *   - Heartbeat: a 30s interval pings `/health`. Three consecutive misses
 *     mark the adapter unhealthy; `invoke()` returns a retryable LLMError
 *     until a heartbeat succeeds again.
 *   - JSON-RPC-style error mapping: server errors include `{error,
 *     message, retryable}` — turned into `LLMError` for callers.
 *   - No background tasks unless the caller calls `start()`. Tests can
 *     skip heartbeat entirely by leaving the client unstarted.
 */
export interface LiteLLMBridgeClientOptions {
  /** Base URL. Defaults to `http://127.0.0.1:4848`. ALWAYS loopback. */
  readonly baseUrl?: string;
  /** Bearer token. Defaults to `process.env.AI_ENGINEERING_BRIDGE_TOKEN`. */
  readonly token?: string;
  /** `fetch` override for tests. Defaults to global `fetch`. */
  readonly fetcher?: typeof fetch;
  /** Heartbeat interval in ms. Defaults to 30_000. */
  readonly heartbeatIntervalMs?: number;
  /** Number of consecutive misses before going unhealthy. Defaults to 3. */
  readonly heartbeatMissThreshold?: number;
  /** Per-request timeout in ms. Defaults to 30_000. */
  readonly requestTimeoutMs?: number;
}

interface CapabilitiesPayload {
  readonly [model: string]: ReadonlyArray<string>;
}

interface BridgeErrorBody {
  readonly error?: string;
  readonly message?: string;
  readonly retryable?: boolean;
  readonly detail?: string;
}

const DEFAULT_BASE_URL = "http://127.0.0.1:4848";
const DEFAULT_INTERVAL = 30_000;
const DEFAULT_MISS_THRESHOLD = 3;
const DEFAULT_TIMEOUT_MS = 30_000;

export class LiteLLMBridgeClient implements LLMPort {
  readonly #baseUrl: string;
  readonly #token: string;
  readonly #fetch: typeof fetch;
  readonly #heartbeatIntervalMs: number;
  readonly #heartbeatMissThreshold: number;
  readonly #requestTimeoutMs: number;

  #consecutiveMisses = 0;
  #healthy = true;
  #heartbeatTimer: ReturnType<typeof setInterval> | undefined;
  // Cached capability matrix. Lazily populated on first `supports()` call.
  #capabilityMatrix: CapabilitiesPayload | undefined;

  constructor(opts: LiteLLMBridgeClientOptions = {}) {
    this.#baseUrl = (opts.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.#token = opts.token ?? process.env.AI_ENGINEERING_BRIDGE_TOKEN ?? "";
    this.#fetch = opts.fetcher ?? globalThis.fetch.bind(globalThis);
    this.#heartbeatIntervalMs = opts.heartbeatIntervalMs ?? DEFAULT_INTERVAL;
    this.#heartbeatMissThreshold = opts.heartbeatMissThreshold ?? DEFAULT_MISS_THRESHOLD;
    this.#requestTimeoutMs = opts.requestTimeoutMs ?? DEFAULT_TIMEOUT_MS;
  }

  // ------------------------------------------------------------------
  // LLMPort
  // ------------------------------------------------------------------

  async invoke(request: LLMRequest): Promise<Result<LLMResponse, LLMError>> {
    if (!this.#healthy) {
      return err(
        new LLMError("bridge unhealthy: heartbeat misses exceeded threshold", /*retryable=*/ true),
      );
    }
    const body = JSON.stringify({
      skill: request.skill,
      prompt: request.prompt,
      capabilities: [...request.capabilities],
      privacy_tier: request.privacyTier,
    });
    const res = await this.#postJson("/llm/invoke", body);
    if (!res.ok) return res;
    const json = res.value as {
      readonly text: string;
      readonly tokens_used: number;
      readonly cost_usd: number;
      readonly provider_id: string;
      readonly model_id: string;
      readonly latency_ms: number;
    };
    return ok({
      text: json.text,
      tokensUsed: json.tokens_used,
      costUsd: json.cost_usd,
      providerId: json.provider_id,
      modelId: json.model_id,
      latencyMs: json.latency_ms,
    } satisfies LLMResponse);
  }

  async supports(capabilities: ReadonlyArray<LLMCapability>): Promise<boolean> {
    if (capabilities.length === 0) return true;
    const matrix = await this.#fetchCapabilities();
    if (matrix === undefined) return false;
    // Fail-open at the matrix level: as long as ANY model in the matrix
    // covers every requested capability, we report `true`. The router
    // does the actual model selection.
    const requested = new Set<string>(capabilities);
    for (const caps of Object.values(matrix)) {
      const offered = new Set(caps);
      let ok = true;
      for (const c of requested) {
        if (!offered.has(c)) {
          ok = false;
          break;
        }
      }
      if (ok) return true;
    }
    return false;
  }

  // ------------------------------------------------------------------
  // Lifecycle
  // ------------------------------------------------------------------

  /** Starts the background heartbeat. Idempotent. */
  start(): void {
    if (this.#heartbeatTimer !== undefined) return;
    this.#heartbeatTimer = setInterval(() => {
      void this.#heartbeat();
    }, this.#heartbeatIntervalMs);
    // Run a heartbeat immediately so callers don't wait for the first tick.
    void this.#heartbeat();
  }

  /** Stops the heartbeat. Idempotent. Safe to call from finalizers. */
  stop(): void {
    if (this.#heartbeatTimer !== undefined) {
      clearInterval(this.#heartbeatTimer);
      this.#heartbeatTimer = undefined;
    }
  }

  /** Test seam: returns true while the adapter is considered healthy. */
  isHealthy(): boolean {
    return this.#healthy;
  }

  /** Test seam: runs a single heartbeat round. Returns true on success. */
  async heartbeatOnce(): Promise<boolean> {
    return this.#heartbeat();
  }

  // ------------------------------------------------------------------
  // Internals
  // ------------------------------------------------------------------

  async #heartbeat(): Promise<boolean> {
    try {
      const ctrl = new AbortController();
      const timeout = setTimeout(() => ctrl.abort(), this.#requestTimeoutMs);
      let res: Response;
      try {
        res = await this.#fetch(`${this.#baseUrl}/health`, {
          method: "GET",
          signal: ctrl.signal,
        });
      } finally {
        clearTimeout(timeout);
      }
      if (res.status === 200) {
        this.#consecutiveMisses = 0;
        this.#healthy = true;
        return true;
      }
      this.#registerMiss();
      return false;
    } catch {
      this.#registerMiss();
      return false;
    }
  }

  #registerMiss(): void {
    this.#consecutiveMisses += 1;
    if (this.#consecutiveMisses >= this.#heartbeatMissThreshold) {
      this.#healthy = false;
    }
  }

  async #fetchCapabilities(): Promise<CapabilitiesPayload | undefined> {
    if (this.#capabilityMatrix !== undefined) return this.#capabilityMatrix;
    const res = await this.#getJson("/llm/capabilities");
    if (!res.ok) return undefined;
    this.#capabilityMatrix = res.value as CapabilitiesPayload;
    return this.#capabilityMatrix;
  }

  async #postJson(path: string, body: string): Promise<Result<unknown, LLMError>> {
    return this.#request(path, "POST", body);
  }

  async #getJson(path: string): Promise<Result<unknown, LLMError>> {
    return this.#request(path, "GET", undefined);
  }

  async #request(
    path: string,
    method: "GET" | "POST",
    body: string | undefined,
  ): Promise<Result<unknown, LLMError>> {
    const sent = await this.#sendRequest(path, method, body);
    if (!sent.ok) return sent;
    const res = sent.value;
    if (res.status >= 200 && res.status < 300) {
      return this.#parseSuccess(res);
    }
    return err(await this.#parseFailure(res));
  }

  async #sendRequest(
    path: string,
    method: "GET" | "POST",
    body: string | undefined,
  ): Promise<Result<Response, LLMError>> {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.#requestTimeoutMs);
    try {
      const init: RequestInit = {
        method,
        headers: this.#buildHeaders(),
        signal: ctrl.signal,
      };
      if (body !== undefined) (init as { body: string }).body = body;
      return ok(await this.#fetch(`${this.#baseUrl}${path}`, init));
    } catch (e) {
      return err(
        new LLMError(
          `bridge transport error: ${e instanceof Error ? e.message : String(e)}`,
          /*retryable=*/ true,
        ),
      );
    } finally {
      clearTimeout(timer);
    }
  }

  #buildHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "content-type": "application/json",
      accept: "application/json",
    };
    if (this.#token.length > 0) {
      headers.authorization = `Bearer ${this.#token}`;
    }
    return headers;
  }

  async #parseSuccess(res: Response): Promise<Result<unknown, LLMError>> {
    try {
      return ok((await res.json()) as unknown);
    } catch (e) {
      return err(
        new LLMError(
          `bridge returned malformed JSON: ${e instanceof Error ? e.message : String(e)}`,
          /*retryable=*/ false,
        ),
      );
    }
  }

  async #parseFailure(res: Response): Promise<LLMError> {
    // Map HTTP status -> LLMError. 429/5xx are retryable; 4xx are not.
    let parsed: BridgeErrorBody = {};
    try {
      parsed = (await res.json()) as BridgeErrorBody;
    } catch {
      // Body was not JSON; fall through with empty parsed.
    }
    const message =
      parsed.message ?? parsed.detail ?? `bridge HTTP ${res.status} ${res.statusText}`;
    const retryable = parsed.retryable ?? (res.status === 429 || res.status >= 500);
    return new LLMError(message, retryable);
  }
}
