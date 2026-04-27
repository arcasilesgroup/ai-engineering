// Public surface of @ai-engineering/llm-bridge.
//
// Layer 3 only (ADR-0005). Default flows delegate to the IDE host; this
// package is reserved for CI / BYOK and talks ONLY to the loopback Python
// bridge running in Docker isolation (ADR-0008).

export { LiteLLMBridgeClient } from "./client.ts";
export type { LiteLLMBridgeClientOptions } from "./client.ts";

// Re-export the LLMPort surface so consumers don't need a separate runtime
// import just to type-check their bridge calls.
export type {
  LLMCapability,
  LLMPort,
  LLMRequest,
  LLMResponse,
  PrivacyTier,
} from "@ai-engineering/runtime";
export { LLMError } from "@ai-engineering/runtime";
