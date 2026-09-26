---
name: ai-stress-test
description: >-
  Test system behavior under extreme load to find breaking points, capacity limits,
  and failure modes. Covers stress, spike, and breakpoint testing with k6 (primary),
  JMeter, or Locust. Refuses unbounded concurrency and production saturation without
  explicit approval. Trigger for "stress test", "load test until it breaks", "find the
  breaking point", "capacity test", "spike test", "how much traffic can we handle",
  "system limits", "what's our max load". Not for frontend performance or Core Web
  Vitals — use /ai-audit-design. Not for general load testing to validate expected
  traffic — use /ai-verify with existing benchmarks. Not for diagnosing a performance
  failure — use /ai-debug.
license: Apache-2.0
---

# ai-stress-test — find where it breaks, not just whether it works

## What it produces

A named breaking point with the load that caused it, the metric that failed first, and
the safe capacity ceiling. Every claim backed by a number from a real run.

## Safety

1. Never run against production without explicit written approval and a defined abort
   threshold.
2. Never generate unbounded concurrency or duration. Every run has a ceiling.
3. Refuse requests that look like denial-of-service: "flood this", "hammer it until it
   dies", "DDoS it" get a hard no, followed by a controlled alternative.
4. Default to `plan-only` mode when the target environment is unclear. Ask before
   executing.
5. Stop immediately if error rate exceeds 5% during a run, or if the target system
   reports health-check failures.

## Steps

### 1. Collect inputs

Gather or ask for:

- **target**: base URL, host, or service under test.
- **environment**: `local`, `staging`, or `production`. If `production`, require explicit
  approval and abort thresholds before doing anything.
- **endpoints**: which flows to test. If unknown, ask for the top 5 most critical user
  journeys (from access logs, SLOs, or product judgment).
- **baseline load**: normal traffic level (requests/second or concurrent users).
- **expected peak**: what the system should handle without degradation.
- **thresholds**: acceptable latency (p95, p99), max error rate, minimum throughput. If
  not provided, use conservative defaults: p95 < 500ms, error rate < 1%, throughput
  matching baseline.
- **auth**: how to authenticate requests (API key, bearer, session, none).

### 2. Select the tool

Use the installed tool. Do not install anything without asking.

| Tool | When | Command shape |
|------|------|---------------|
| **k6** | Default for HTTP APIs, CI-friendly, threshold-native | `k6 run script.js` |
| **JMeter** | Existing `.jmx` plans, team already uses it | `jmeter -n -t plan.jmx` |
| **Locust** | Python shops, complex user behavior modeling | `locust -f locustfile.py --headless` |

If multiple tools are installed, prefer k6. If the user has existing test scripts
(JMeter `.jmx`, Locust `locustfile.py`), use what they have.

### 3. Design scenarios

Design from lightest to heaviest. Each scenario is a separate run.

**a. Baseline** (always first)
Short run at expected normal load. Confirms connectivity, auth works, and metrics
collect correctly. Abort if this fails.

**b. Stress test**
Ramp from normal load to beyond expected peak in stages. Goal: find the knee where
latency degrades or errors appear.

Typical shape:
```
Normal load    2m    50 VUs
Ramp up        3m    200 VUs
Peak hold      5m    200 VUs
Push beyond    3m    500 VUs
Ramp down      1m    0 VUs
```

**c. Spike test**
Sudden burst from zero (or baseline) to extreme load. Goal: test recovery behavior.

Typical shape:
```
Baseline       1m    50 VUs
Spike          10s   1000 VUs
Spike hold     2m    1000 VUs
Recovery       3m    50 VUs
```

**d. Breakpoint** (optional, the nuclear option)
Continuously increase load until the system fails. Goal: find the absolute ceiling.

Use k6 `ramping-arrival-rate` with a high target and `abortOnFail` threshold. Stop
manually or let thresholds kill the run.

### 4. Define thresholds

Every scenario except baseline must have abort thresholds:

```
http_req_duration: ['p(95)<500']
http_req_failed: ['rate<0.01']
```

For breakpoint tests, thresholds ARE the measurement: the point they trigger IS the
breaking point.

### 5. Execute

1. Run baseline first. Confirm it passes.
2. Run stress. Record results.
3. Run spike. Record results.
4. Optionally run breakpoint. Record the load level where thresholds breach.

Each run: save raw output (JSON or JTL), save summary metrics, note the environment
state (CPU, memory if visible).

### 6. Analyze

For each scenario, extract:

- **p50, p90, p95, p99 latency** (never averages alone)
- **Throughput** (requests/second at peak)
- **Error rate** (percentage and types: timeouts, 5xx, connection resets)
- **Breaking point**: the load level where thresholds were breached
- **Safe capacity**: 70-80% of the breaking point (leave headroom)
- **Bottleneck signal**: which metric degraded first (latency, errors, throughput)

### 7. Report

Produce a concise report with:

1. What was tested (endpoints, environment, tool).
2. Results per scenario (table of metrics vs thresholds).
3. The breaking point with evidence (the exact load level and the metric that failed).
4. Safe capacity recommendation.
5. Bottleneck hypothesis (what to investigate next).
6. What was NOT tested (blind spots).

## Anti-patterns

- Running stress tests without baseline first. If baseline is broken, every other
  number is meaningless.
- Using averages instead of percentiles. Average latency hides the long tail.
- Testing with tiny data sets. Cached or warm-cache results are fiction.
- Claiming a bottleneck without metric evidence. "Probably the database" is not analysis.
- Running from the same machine as the target. The load generator becomes the bottleneck.
- Ignoring the ramp. Jumping straight to peak load skips the knee, which is the most
  useful data point.
- Testing production without abort thresholds. One runaway test can take down the system.

## Done when

- A breaking point is named with the load level and metric that failed first.
- Safe capacity is stated as a number, not a feeling.
- Every claim is backed by output from a real run.
- The user knows what to investigate next.

## What this is not

- "Run k6 and tell me if it's fast" — stress testing finds limits, not general
  performance opinions.
- "DDoS my production" — hard no, always.
- Load testing for expected traffic — that is /ai-verify with existing benchmarks.
- Frontend performance or Core Web Vitals — that is /ai-audit-design.
- Diagnosing why something is slow — that is /ai-debug. This skill finds WHERE it breaks,
  not WHY.

## Routing

In scope:

- "stress test this API", "find the breaking point", "how much traffic can we handle"
- "capacity test", "spike test", "what's our max load"
- "test system limits", "validate scaling assumptions"

Not for:

- Frontend performance, Core Web Vitals, page load metrics — use /ai-audit-design.
- Diagnosing a performance regression — use /ai-debug.
- General load testing to validate expected traffic works — use /ai-verify.
- Deciding what to build — use /ai-orchestrator.
- DoS or unauthorized traffic generation — refused.

## Lifecycle

Lane: standard
Writes: performance-report.md
Read by: ai-verify
Dies: ai-eng spec close
Next: ai-verify, ai-debug (if bottleneck found)
