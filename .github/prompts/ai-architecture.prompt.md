---
description: "Analyze software architecture: drift detection, coupling, cohesion,"
mode: "agent"
---


# Architecture

## Purpose

Analyze software architecture for drift from spec, coupling issues, cohesion problems, boundary violations, and technical debt. Part of the verify agent's 7-mode assessment.

## Trigger

- Command: `/ai:verify architecture` or `/ai:architecture`
- Context: architecture review, drift detection, design decision assessment, dependency analysis.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"architecture"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## When NOT to Use

- **Code quality metrics** (coverage, complexity, duplication) — use `quality` instead.
- **Security vulnerabilities** — use `security` instead.
- **API contract design** — use `api` instead.
- **Performance bottlenecks** — use `perf` instead.
- **Bug investigation** — use `debug` instead.

## Procedure

1. **Read architecture docs** — load specs, ADRs, documented decisions, product contract Section 3 (Technical Design), and framework contract Section 2 (agentic model).

2. **Map actual structure** — analyze the codebase:
   - Module hierarchy and package boundaries.
   - Import graph: who imports whom, circular dependency detection.
   - Call graph: entry points, hot paths, integration points.
   - Data flow: how data moves between layers/modules.

3. **Detect drift** — compare documented architecture vs actual implementation:
   - Modules described in spec but missing in code.
   - Modules in code with no spec backing.
   - Boundary violations: module A importing module B's internals.
   - Naming mismatches: spec calls it X, code calls it Y.

4. **Assess coupling** — identify tight coupling:
   - Afferent coupling (Ca): how many modules depend on this one.
   - Efferent coupling (Ce): how many modules this one depends on.
   - Instability: Ce / (Ca + Ce) — unstable modules change frequently.
   - Circular dependencies: A→B→C→A chains.
   - God Objects: classes/modules with >10 direct dependencies.

5. **Evaluate cohesion** — modules should do one thing well:
   - Modules with mixed responsibilities (data access + business logic + presentation).
   - Files exceeding 500 lines (potential decomposition candidate).
   - Functions exceeding 50 lines or cyclomatic complexity >10.

6. **Score tech debt** — classify findings by severity and effort:
   - **Critical**: circular dependencies, boundary violations affecting >3 modules.
   - **High**: God Objects, modules with instability >0.8.
   - **Medium**: cohesion issues, naming drift.
   - **Low**: minor coupling, documentation gaps.

7. **Check backwards compatibility** (compatibility mode) — analyze changes for breaking impacts:
   - Public API surface: detect removed/renamed functions, changed signatures, narrowed types.
   - Database schema: verify migrations are additive (new columns nullable or with defaults, no dropped columns without deprecation).
   - Configuration formats: check that existing config keys still work, new keys have defaults.
   - Exports: flag removed or renamed exports that downstream code depends on.
   - Protocols/interfaces: verify existing contracts are not narrowed.
   - Category: **Breaking** (removes capability) or **Compatible** (additive change).

8. **Report** — produce uniform scan output:

```markdown
# Scan Report: architecture

## Score: N/100
## Verdict: PASS (≥80) | WARN (60-79) | FAIL (<60)

## Findings
| # | Severity | Category | Description | Location | Remediation |

## Dependency Map
- Module graph summary with coupling metrics

## Drift Items
| Spec Reference | Expected | Actual | Status |

## Tech Debt Register
| Item | Severity | Effort | Impact | Priority |

## Compatibility Assessment
| Surface | Change | Breaking | Migration Path | Status |
```

## Examples

### Example 1: Pre-release architecture review

User says: "Run architecture scan before the release."
Actions:

1. Map current module structure, detect drift from active spec, and assess coupling/cohesion.
2. Produce scan report with score, findings, and tech debt register for release decision.
   Result: Architecture scan report enables informed release gate decision.

### Example 2: Post-refactor validation

User says: "We just refactored the CLI module. Check architecture health."
Actions:

1. Focus analysis on CLI module and its dependents — verify boundaries, coupling, and naming after refactor.
2. Report drift from spec (if refactor changed module structure) and coupling changes.
   Result: Confirmation that refactor maintained or improved architectural health.

## Governance Notes

- Architecture is read-only — produces reports, does not modify code.
- Findings feed into verify agent's aggregated quality gate assessment.
- Critical findings (circular deps, boundary violations) are blocking for release gate.
- Tech debt items should be tracked in decision-store if accepted as risk.

### Iteration Limits

- Max 3 attempts to resolve ambiguous findings before escalating with evidence.

## References

- `standards/framework/core.md` — governance structure and ownership model.
- `standards/framework/quality/core.md` — quality thresholds (complexity, coverage).
- `.github/agents/verify.agent.md` — agent that invokes this skill as part of 7-mode assessment.
- `context/product/product-contract.md` §3 — Technical Design (reference architecture).
