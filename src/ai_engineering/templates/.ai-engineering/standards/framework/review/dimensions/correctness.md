# Correctness Review Dimension

## Scope Priority
1. **Intent-implementation alignment** — does the code do what the PR/commit claims?
2. **Integration boundary correctness** — producer-consumer format matches, serialization compat
3. **Basic logic** — off-by-one, wrong operators, boundary conditions
4. **Cross-function correctness** — unsafe optimizations, implicit contracts between functions
5. **State and data flow** — variable shadowing, mutations affecting shared state

## Approach
Trace data flows from source to sink. Verify contract adherence at every boundary.

## Self-Challenge
- Did you verify the implementation matches the stated intent, not your assumed intent?
- Is the boundary condition actually reachable, or is it guarded elsewhere?
