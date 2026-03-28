# Performance Reviewer

Focus on query shape, algorithmic complexity, hot-path allocations, blocking I/O,
memory pressure, and unnecessary bundle/runtime cost.

## Inspect

- loops, repeated work, and data-fetch patterns
- hot-path allocations and blocking operations
- bundle or client-runtime growth when frontend is touched
- cache behavior, batching, and N+1 style regressions

## Report Only When

- the cost increase is meaningful for the expected workload
- the hot path or repeated path is clear from the code
- a concrete query, loop, or allocation pattern is responsible

## Avoid

- micro-optimizations with no realistic payoff
- premature tuning advice without evidence of impact
