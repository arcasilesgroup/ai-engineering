// tests/circuit-breaker.spec.ts — the circuit breaker for external service calls.
//
// Tests state transitions (closed → open → half-open → closed), failure
// threshold behavior, reset timing, and the snapshot diagnostic.

import { describe, expect, test } from "bun:test";
import { CircuitBreaker } from "../src/guards/circuit-breaker.ts";

describe("CircuitBreaker — state machine", () => {
  test("starts closed with zero failures", () => {
    const cb = new CircuitBreaker();
    expect(cb.state).toBe("closed");
    expect(cb.allowRequest).toBe(true);
    expect(cb.snapshot().consecutiveFailures).toBe(0);
  });

  test("stays closed below failure threshold", () => {
    const cb = new CircuitBreaker({ failureThreshold: 3 });
    cb.recordFailure();
    cb.recordFailure();
    expect(cb.state).toBe("closed");
    expect(cb.allowRequest).toBe(true);
    expect(cb.snapshot().consecutiveFailures).toBe(2);
  });

  test("opens after reaching failure threshold", () => {
    const cb = new CircuitBreaker({ failureThreshold: 3, resetMs: 1000 });
    cb.recordFailure();
    cb.recordFailure();
    cb.recordFailure();
    expect(cb.state).toBe("open");
    expect(cb.allowRequest).toBe(false);
  });

  test("rejects immediately while open", () => {
    const cb = new CircuitBreaker({ failureThreshold: 2, resetMs: 60_000 });
    cb.recordFailure();
    cb.recordFailure();
    expect(cb.allowRequest).toBe(false);
    expect(cb.allowRequest).toBe(false); // still open
  });

  test("transitions to half-open after reset period", () => {
    const cb = new CircuitBreaker({ failureThreshold: 2, resetMs: 1 });
    cb.recordFailure();
    cb.recordFailure();
    expect(cb.state).toBe("open");
    // Wait for reset period to elapse
    const start = Date.now();
    while (Date.now() - start < 5) { /* spin */ }
    expect(cb.state).toBe("half-open");
    expect(cb.allowRequest).toBe(true);
  });

  test("closes on success after half-open", () => {
    const cb = new CircuitBreaker({ failureThreshold: 2, resetMs: 1 });
    cb.recordFailure();
    cb.recordFailure();
    // Wait for half-open
    const start = Date.now();
    while (Date.now() - start < 5) { /* spin */ }
    expect(cb.state).toBe("half-open");
    cb.recordSuccess();
    expect(cb.state).toBe("closed");
    expect(cb.allowRequest).toBe(true);
    expect(cb.snapshot().consecutiveFailures).toBe(0);
  });

  test("re-opens on failure during half-open", () => {
    const cb = new CircuitBreaker({ failureThreshold: 2, resetMs: 1 });
    cb.recordFailure();
    cb.recordFailure();
    const start = Date.now();
    while (Date.now() - start < 5) { /* spin */ }
    expect(cb.state).toBe("half-open");
    cb.recordFailure(); // fail during half-open
    expect(cb.state).toBe("open");
    expect(cb.allowRequest).toBe(false);
  });

  test("success resets failure count", () => {
    const cb = new CircuitBreaker({ failureThreshold: 5 });
    cb.recordFailure();
    cb.recordFailure();
    cb.recordSuccess();
    expect(cb.snapshot().consecutiveFailures).toBe(0);
    cb.recordFailure();
    expect(cb.snapshot().consecutiveFailures).toBe(1);
  });

  test("snapshot reports consistent state", () => {
    const cb = new CircuitBreaker({ failureThreshold: 3, resetMs: 100 });
    const s1 = cb.snapshot();
    expect(s1.state).toBe("closed");
    expect(s1.consecutiveFailures).toBe(0);
    expect(s1.openUntil).toBe(0);

    cb.recordFailure();
    cb.recordFailure();
    cb.recordFailure();
    const s2 = cb.snapshot();
    expect(s2.state).toBe("open");
    expect(s2.consecutiveFailures).toBe(3);
    expect(s2.openUntil).toBeGreaterThan(0);
  });

  test("default options: threshold=5, resetMs=30000", () => {
    const cb = new CircuitBreaker();
    for (let i = 0; i < 4; i++) cb.recordFailure();
    expect(cb.state).toBe("closed");
    cb.recordFailure(); // 5th failure
    expect(cb.state).toBe("open");
  });
});
