# Execution Safety Rules

Non-negotiable safety constraints for stress testing.

## Before any run

1. Confirm the target environment. If it is production, confirm explicit written
   approval exists and abort thresholds are defined.
2. Confirm authentication works with a single request before ramping up.
3. Confirm the load generator machine has sufficient CPU, memory, and network
   bandwidth. The generator must not be on the same host as the target.
4. Confirm monitoring is active (logs, dashboards, health checks).

## During every run

1. Monitor error rate continuously. If it exceeds 5%, abort immediately.
2. Watch for target health-check failures. If health checks fail, abort.
3. Never exceed the defined abort thresholds.
4. Never run longer than the defined duration.
5. Never exceed the defined VU count.

## Production-specific rules

1. Require explicit written approval before any production test.
2. Set abort thresholds tighter than staging (error rate < 0.5%, p95 < 200ms).
3. Run during low-traffic windows only.
4. Notify the team before starting.
5. Have a rollback plan.
6. Cap VUs at a fraction of expected real traffic (start at 10%, not 100%).
7. Never run breakpoint tests in production.

## Refusal conditions

Refuse and explain why:

- "Flood this" or "DDoS this" or "hammer it until it dies" with no abort conditions.
- Production stress testing without approval.
- Unbounded duration or concurrency ("run it until it stops").
- Testing third-party services without their authorization.
- Stress testing a system you do not own or operate.

## What to do instead

When a request triggers a refusal, offer the controlled alternative:

- "Flood this" becomes "Let's design a staged stress test with abort thresholds."
- "DDoS it" becomes "Let's run a spike test to see recovery behavior."
- "Until it dies" becomes "Let's set a breakpoint test with a 5% error-rate abort."
