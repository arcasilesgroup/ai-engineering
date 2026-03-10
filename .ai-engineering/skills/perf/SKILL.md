---
name: perf
description: "Multi-stack performance scanning: N+1 queries, O(n^2) patterns, memory leaks, bundle size, I/O bottlenecks."
metadata:
  version: 2.0.0
  tags: [performance, profiling, optimization, bottlenecks, n-plus-one]
  ai-engineering:
    scope: read-only
    token_estimate: 1000
---

# Performance

## Purpose

Multi-stack performance scanner that detects issues via static analysis + heuristics. Identifies N+1 queries, O(n^2) algorithms, memory leaks, I/O inefficiency, and bundle size problems. Part of the scan agent's 7-mode assessment. Renamed from perf-review.

## Trigger

- Command: `/ai:scan performance`
- Context: performance audit, pre-release performance check, bottleneck investigation.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"perf"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## What it Detects (by stack)

| Category | Python | .NET | TypeScript/React | Rust | SQL |
|----------|--------|------|------------------|------|-----|
| N+1 Queries | SQLAlchemy lazy loads in loops | EF Core missing .Include() | Prisma nested queries in loops | Diesel lazy associations | Correlated subqueries |
| Memory Leaks | Unclosed handles, growing lists | Undisposed IDisposable | Detached DOM refs, closures | Unbounded Vec growth | Connection pool exhaustion |
| CPU Bottlenecks | O(n^2) loops, sync I/O in async | LINQ .ToList() mid-chain | Missing useMemo/useCallback | Unnecessary clones | Full table scans |
| I/O Inefficiency | Sequential HTTP (not gather) | Sequential await (not WhenAll) | Sequential fetch (not Promise.all) | Blocking I/O in async | No connection pooling |
| Bundle/Build | -- | -- | Bundle size, tree-shaking gaps | Binary size | -- |

## Procedure

1. **Detect stacks** -- determine applicable performance checks.
2. **Static analysis** -- run ruff perf rules, AST pattern matching, clippy perf lints.
3. **Heuristic scan** -- LLM analyzes code for anti-patterns above.
4. **Score** -- rate by impact (critical path vs cold path).
5. **Report** -- uniform scan output contract with hot spots ranked by impact.

## Output

Follows uniform scan output contract (see scan agent).
