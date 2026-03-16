# Performance Review Dimension

## Scope Priority
1. **Database queries** — N+1, missing indexes, full table scans, unnecessary joins
2. **Algorithm complexity** — O(n^2) or worse, unnecessary nested loops
3. **Memory management** — leaks, unbounded growth, excessive allocations
4. **Async & concurrency** — blocking I/O, missing parallelization, thread pool exhaustion
5. **Network & I/O** — missing batching, redundant API calls, large payloads
6. **Frontend** — bundle size, lazy loading, unnecessary re-renders

## Key Rule
Recommend fixes, not observability. When finding N+1, eliminate it (batch, select_related, prefetch_related) — never just add logging.

## Self-Challenge
- Is this actually a hot path, or is it called once at startup?
- Does the optimization trade readability for negligible performance gain?
