/**
 * JSON-RPC 2.0 primitives + MCP envelope shapes.
 *
 * Pure data + helpers only — no transport, no Bun, no HTTP. Keeps the
 * dispatch layer fully testable in isolation.
 */

export const PARSE_ERROR = -32700;
export const INVALID_REQUEST = -32600;
export const METHOD_NOT_FOUND = -32601;
export const INVALID_PARAMS = -32602;
export const INTERNAL_ERROR = -32603;

export type JsonRpcId = number | string | null;

export interface JsonRpcRequest {
  readonly jsonrpc: "2.0";
  readonly id?: JsonRpcId;
  readonly method: string;
  readonly params?: Record<string, unknown>;
}

export interface JsonRpcSuccess<T> {
  readonly jsonrpc: "2.0";
  readonly id: JsonRpcId;
  readonly result: T;
}

export interface JsonRpcError {
  readonly jsonrpc: "2.0";
  readonly id: JsonRpcId;
  readonly error: { readonly code: number; readonly message: string };
}

export type JsonRpcResponse<T = unknown> = JsonRpcSuccess<T> | JsonRpcError;

export const success = <T>(id: JsonRpcId, result: T): JsonRpcSuccess<T> => ({
  jsonrpc: "2.0",
  id,
  result,
});

export const failure = (id: JsonRpcId, code: number, message: string): JsonRpcError => ({
  jsonrpc: "2.0",
  id,
  error: { code, message },
});

/** MCP resource descriptor returned by `resources/list`. */
export interface Resource {
  readonly uri: string;
  readonly name: string;
  readonly description?: string;
  readonly mimeType?: string;
}

/** MCP resource content returned by `resources/read`. */
export interface ResourceContent {
  readonly uri: string;
  readonly mimeType: string;
  readonly text: string;
}

/** MCP tool descriptor returned by `tools/list`. */
export interface Tool {
  readonly name: string;
  readonly description: string;
  readonly inputSchema: Record<string, unknown>;
}

/** MCP tool-call result returned by `tools/call`. */
export interface ToolResult {
  readonly content: ReadonlyArray<{
    readonly type: "text";
    readonly text: string;
  }>;
  readonly isError?: boolean;
}

/** MCP prompt descriptor returned by `prompts/list`. */
export interface Prompt {
  readonly name: string;
  readonly description: string;
  readonly arguments?: ReadonlyArray<{
    readonly name: string;
    readonly required?: boolean;
  }>;
}

/** MCP prompt result returned by `prompts/get`. */
export interface PromptResult {
  readonly description: string;
  readonly messages: ReadonlyArray<{
    readonly role: "user" | "assistant" | "system";
    readonly content: { readonly type: "text"; readonly text: string };
  }>;
}

/**
 * Parse a JSON-RPC envelope from a raw request body. Returns null when
 * the body cannot be parsed (caller emits PARSE_ERROR).
 */
export const parseEnvelope = (raw: string): JsonRpcRequest | null => {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      return null;
    }
    const obj = parsed as Record<string, unknown>;
    if (typeof obj.method !== "string") return null;
    const result: JsonRpcRequest = {
      jsonrpc: (obj.jsonrpc as "2.0") ?? "2.0",
      method: obj.method,
      ...(obj.id !== undefined ? { id: obj.id as JsonRpcId } : {}),
      ...(obj.params !== undefined && typeof obj.params === "object"
        ? { params: obj.params as Record<string, unknown> }
        : {}),
    };
    return result;
  } catch {
    return null;
  }
};
