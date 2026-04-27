/**
 * Base error classes for the framework.
 *
 * Domain errors describe invariant violations and use cases failing.
 * Adapter errors describe infrastructure problems (network, FS, API).
 *
 * SOLID: every error type is final and self-descriptive.
 * KISS: no exception hierarchies more than two levels deep.
 */

export abstract class DomainError extends Error {
  abstract readonly code: string;
  abstract readonly category: "validation" | "policy" | "state" | "not-found";

  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = this.constructor.name;
  }

  toJSON(): Record<string, unknown> {
    return {
      name: this.name,
      code: this.code,
      category: this.category,
      message: this.message,
    };
  }
}

export class ValidationError extends DomainError {
  readonly code = "VALIDATION_FAILED";
  readonly category = "validation" as const;

  constructor(
    message: string,
    public readonly field?: string,
  ) {
    super(message);
  }
}

export class PolicyViolation extends DomainError {
  readonly code = "POLICY_VIOLATION";
  readonly category = "policy" as const;

  constructor(
    message: string,
    public readonly policyId: string,
  ) {
    super(message);
  }
}

export class IllegalStateTransition extends DomainError {
  readonly code = "ILLEGAL_STATE_TRANSITION";
  readonly category = "state" as const;

  constructor(
    message: string,
    public readonly from: string,
    public readonly to: string,
  ) {
    super(message);
  }
}

export class NotFoundError extends DomainError {
  readonly code = "NOT_FOUND";
  readonly category = "not-found" as const;

  constructor(
    public readonly resource: string,
    public readonly id: string,
  ) {
    super(`${resource} not found: ${id}`);
  }
}

export abstract class AdapterError extends Error {
  abstract readonly adapter: string;
  abstract readonly retryable: boolean;

  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = this.constructor.name;
  }
}

export class IOError extends AdapterError {
  readonly adapter = "filesystem";
  readonly retryable = false;
}

export class NetworkError extends AdapterError {
  readonly adapter = "network";
  readonly retryable = true;
}
