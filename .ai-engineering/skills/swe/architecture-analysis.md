# Architecture Analysis

## Purpose

Analyze software architecture: dependencies, coupling, cohesion, boundaries, and technical debt. Provides structured assessment to guide design decisions and identify improvement opportunities.

## Trigger

- Command: agent invokes architecture-analysis skill or user asks about system design.
- Context: new feature planning, tech debt assessment, brownfield analysis, dependency review.

## Procedure

1. **Map dependencies** — identify module relationships.
   - Internal dependencies: which modules import which.
   - External dependencies: third-party packages and their versions.
   - Circular dependencies: identify and flag.
   - Dependency depth: count transitive dependency chains.

2. **Assess coupling** — evaluate how tightly modules are connected.
   - Data coupling (good): modules share data through parameters.
   - Stamp coupling (acceptable): modules share structured data.
   - Control coupling (concerning): modules control each other's flow.
   - Content coupling (bad): modules access each other's internals.

3. **Assess cohesion** — evaluate internal module focus.
   - Functional cohesion (best): module does one thing well.
   - Sequential cohesion (good): output of one part feeds next.
   - Logical cohesion (poor): module groups unrelated things by category.

4. **Identify boundaries** — evaluate separation of concerns.
   - Layer boundaries: CLI → service → state → I/O.
   - Domain boundaries: installer, hooks, doctor, updater as separate domains.
   - API contracts: are module interfaces well-defined?

5. **Assess tech debt** — catalog known issues.
   - Code smells: long functions, god classes, feature envy.
   - Missing abstractions: duplicated patterns that need extraction.
   - Outdated patterns: deprecated APIs, legacy approaches.
   - Test gaps: untested critical paths.

6. **Recommend** — prioritized improvement list.
   - Impact vs. effort matrix.
   - Quick wins vs. structural changes.
   - Risk of not addressing.

## Output Contract

- Dependency graph (text or diagram).
- Coupling/cohesion assessment per module.
- Boundary analysis with recommendations.
- Tech debt catalog with prioritization.
- Actionable improvement plan.

## Governance Notes

- Architecture changes should be proposed as spec tasks, not ad-hoc changes.
- Follow layered architecture: CLI → service → state → I/O.
- Respect ownership boundaries (framework/team/project/system).
- Cross-cutting concerns (logging, error handling) follow framework patterns.

## References

- `standards/framework/stacks/python.md` — code patterns and project layout.
- `agents/architect.md` — agent that performs architecture analysis.
- `agents/codebase-mapper.md` — agent for brownfield codebase mapping.
- `skills/swe/explain.md` — explain architectural patterns and decisions.
