import type { Result } from "../kernel/result.ts";

/**
 * IdentityPort — Dual-Plane Architecture identity broker.
 *
 * Manages "On-Behalf-Of" tokens for agents: ensures the agent only has
 * the scopes it strictly needs (e.g. `read:email`, NOT `admin:all`).
 *
 * Inspired by OAuth on-behalf-of flow + AWS STS scoped tokens.
 * Tokens are short-lived and bound to a specific spec/plan execution.
 */
export interface IdentityToken {
  readonly tokenId: string;
  readonly scopes: ReadonlyArray<string>;
  readonly expiresAt: string;
  readonly boundTo: { readonly specId?: string; readonly planId?: string };
}

export class IdentityError extends Error {
  constructor(
    message: string,
    public readonly retryable: boolean,
  ) {
    super(message);
    this.name = "IdentityError";
  }
}

export interface IdentityPort {
  issueToken(
    agentId: string,
    scopes: ReadonlyArray<string>,
    boundTo: IdentityToken["boundTo"],
  ): Promise<Result<IdentityToken, IdentityError>>;
  revoke(tokenId: string): Promise<Result<void, IdentityError>>;
  validate(tokenId: string): Promise<Result<IdentityToken, IdentityError>>;
}
