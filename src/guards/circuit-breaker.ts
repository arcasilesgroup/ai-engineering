// Circuit breaker for external service calls. Prevents latency death spiral
// when a classifier (Jev) or MCP server is down: after N consecutive failures,
// the circuit opens and rejects immediately for M milliseconds, then tries once.
// Inspired by Pyro's gateway circuit breaker (DelvisorLabs/Pyro).

export type CircuitState = "closed" | "open" | "half-open";

export interface CircuitBreakerOptions {
  /** Consecutive failures before the circuit opens. Default: 5. */
  failureThreshold?: number;
  /** Milliseconds the circuit stays open before attempting recovery. Default: 30000. */
  resetMs?: number;
}

export class CircuitBreaker {
  private consecutiveFailures = 0;
  private openUntil = 0;
  private options: CircuitBreakerOptions;

  constructor(options: CircuitBreakerOptions = {}) {
    this.options = options;
  }

  /** Update thresholds without creating a new instance. */
  configure(options: CircuitBreakerOptions): void {
    if (options.failureThreshold !== undefined) this.options.failureThreshold = options.failureThreshold;
    if (options.resetMs !== undefined) this.options.resetMs = options.resetMs;
  }

  get state(): CircuitState {
    if (this.openUntil === 0) return "closed";
    if (Date.now() >= this.openUntil) return "half-open";
    return "open";
  }

  /** Can we attempt a call right now? */
  get allowRequest(): boolean {
    const s = this.state;
    return s === "closed" || s === "half-open";
  }

  /** Record a successful call. Resets failure count and closes the circuit. */
  recordSuccess(): void {
    this.consecutiveFailures = 0;
    this.openUntil = 0;
  }

  /** Record a failed call. Opens the circuit when threshold is reached. */
  recordFailure(): void {
    this.consecutiveFailures += 1;
    const threshold = this.options.failureThreshold ?? 5;
    if (this.consecutiveFailures >= threshold) {
      this.openUntil = Date.now() + (this.options.resetMs ?? 30_000);
    }
  }

  /** Snapshot for diagnostics. */
  snapshot(): { state: CircuitState; consecutiveFailures: number; openUntil: number } {
    return { state: this.state, consecutiveFailures: this.consecutiveFailures, openUntil: this.openUntil };
  }
}
