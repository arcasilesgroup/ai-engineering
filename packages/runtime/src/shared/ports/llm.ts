import type { Result } from "../kernel/result.ts";

/**
 * LLMPort — driven port for LLM inference.
 *
 * In subscription-piggyback mode, this port DELEGATES to the IDE host
 * (claude -p, cursor-agent, codex exec, gemini -p, cline -y). In BYOK
 * mode (CI), it talks to the local LiteLLM bridge over JSON-RPC.
 *
 * Skills declare required `capabilities` in their frontmatter. The port
 * implementation negotiates with the provider before calling — fails fast
 * if capability is unsupported.
 */
export interface LLMRequest {
  readonly skill: string;
  readonly prompt: string;
  readonly capabilities: ReadonlyArray<LLMCapability>;
  readonly privacyTier: PrivacyTier;
}

export interface LLMResponse {
  readonly text: string;
  readonly tokensUsed: number;
  readonly costUsd: number;
  readonly providerId: string;
  readonly modelId: string;
  readonly latencyMs: number;
}

export type LLMCapability =
  | "tool_use"
  | "structured_output"
  | "prompt_caching"
  | "long_context"
  | "vision"
  | "streaming";

export type PrivacyTier = "standard" | "strict" | "airgapped";

export class LLMError extends Error {
  constructor(
    message: string,
    public readonly retryable: boolean,
    public readonly providerId?: string,
  ) {
    super(message);
    this.name = "LLMError";
  }
}

export interface LLMPort {
  invoke(request: LLMRequest): Promise<Result<LLMResponse, LLMError>>;

  /**
   * Capability negotiation — fail fast before invocation if the routed
   * provider doesn't support what the skill needs. Triggers fallback chain.
   */
  supports(capabilities: ReadonlyArray<LLMCapability>): Promise<boolean>;
}
