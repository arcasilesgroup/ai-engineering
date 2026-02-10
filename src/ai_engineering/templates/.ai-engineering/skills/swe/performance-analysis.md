# Performance Analysis

## Purpose

Identify and resolve performance bottlenecks through systematic profiling, measurement, and targeted optimization. Focuses on evidence-based improvements, not premature optimization.

## Trigger

- Command: agent invokes performance-analysis skill or user reports slow behavior.
- Context: slow CLI commands, high memory usage, long test execution, I/O bottlenecks.

## Procedure

1. **Measure first** — establish baseline metrics.
   - Wall clock time for target operation.
   - CPU profiling: `python -m cProfile` or `py-spy`.
   - Memory profiling: `tracemalloc` or `memray`.
   - I/O profiling: count file reads/writes, network calls.

2. **Identify bottlenecks** — find the hot path.
   - Sort profiler output by cumulative time.
   - Look for: unnecessary I/O in loops, repeated computations, large memory allocations.
   - Check for O(n²) or worse algorithmic complexity.

3. **Analyze root cause** — understand why it's slow.
   - Is it CPU-bound? → optimize algorithm, use generators, consider caching.
   - Is it I/O-bound? → batch operations, reduce file system calls, use async I/O.
   - Is it memory-bound? → use generators instead of lists, process in chunks.

4. **Optimize** — apply targeted fixes.
   - Caching: memoize expensive computations (`functools.lru_cache`).
   - Generators: use `yield` for large data processing.
   - Batch I/O: combine multiple reads/writes.
   - Algorithm improvement: use appropriate data structures (dict/set for lookups).
   - Lazy evaluation: defer computations until needed.

5. **Validate** — measure improvement.
   - Re-run baseline measurements.
   - Quantify improvement: before vs. after (time, memory, I/O count).
   - Ensure no regressions in correctness (full test suite passes).

## Output Contract

- Baseline measurements (before optimization).
- Bottleneck identification with evidence.
- Optimization applied with rationale.
- Improvement measurements (after optimization).
- Test results confirming no regressions.

## Governance Notes

- Never optimize without measurement. "Premature optimization is the root of all evil."
- Performance changes must not compromise code readability without significant gain (>2x improvement).
- Caching must consider invalidation strategy.
- Async patterns must not introduce concurrency bugs.

## References

- `standards/framework/stacks/python.md` — code patterns.
- `standards/framework/quality/python.md` — complexity thresholds.
- `skills/swe/python-mastery.md` — performance optimization domain.
