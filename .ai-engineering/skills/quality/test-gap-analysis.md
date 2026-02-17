# Test Gap Analysis

## Purpose

Maps each product capability to its test evidence, classifies coverage confidence per domain, identifies untested critical paths, and recommends minimum test additions for release confidence. Bridges the gap between code coverage metrics and capability-level assurance.

## Trigger

- Command: agent invokes test-gap-analysis skill or user requests test coverage review.
- Context: pre-release confidence assessment, post-refactoring test validation, quality audit.

## Procedure

### Phase 1: Capability Inventory

1. **List product capabilities** — extract from `product-contract.md` and `framework-contract.md`.
   - CLI commands: install, doctor, version, validate, gate, maintenance.
   - Governance features: hooks, enforcement, risk lifecycle, decision persistence.
   - Content features: skills, agents, standards, templates, mirrors.
   - Infrastructure: CI/CD, cross-OS support, packaging.

2. **Classify by criticality** — assign risk tier to each capability.
   - **Governance-critical** (≥90% coverage required): hooks, enforcement, risk lifecycle, decision store, ownership boundaries.
   - **Core** (≥80% coverage required): CLI commands, install flow, template mirroring.
   - **Supporting** (≥70% acceptable): maintenance utilities, reporting, doctor checks.

### Phase 2: Test Evidence Mapping

3. **Map capabilities to test files** — for each capability, identify covering tests.
   - Search `tests/` for test functions/classes that exercise the capability.
   - Match by module import, function name, fixture usage, and test docstrings.
   - Record: capability → test file(s) → test function(s) → coverage type (unit/integration/e2e).

4. **Assess coverage type** — classify the kind of testing per capability.
   - **Unit**: isolated function/method tests.
   - **Integration**: multi-module interaction tests.
   - **E2E**: full command/workflow tests.
   - **None**: no test evidence found.

### Phase 3: Confidence Classification

5. **Rate confidence per capability** — combine coverage data with test type.
   - **High**: unit + integration tests, governance-critical paths fully exercised.
   - **Medium**: unit tests exist but integration gaps, or only happy-path coverage.
   - **Low**: minimal or no test coverage, critical paths untested.

6. **Identify untested critical paths** — find governance-critical capabilities with low/no coverage.
   - Error handling paths in governance flows.
   - Edge cases in risk lifecycle (expiry, renewal limits, concurrent modifications).
   - Cross-OS behavior differences.
   - Hook bypass scenarios.

### Phase 4: Report

7. **Produce gap matrix** — structured output mapping capabilities to test evidence.
   - One row per capability with test files, confidence level, and gap description.
   - Summary statistics by criticality tier.
   - Prioritized list of recommended test additions.

## Output Contract

```
## Test Gap Analysis Report

### Summary
- Capabilities audited: N
- High confidence: N | Medium: N | Low: N | None: N
- Governance-critical gaps: N

### Gap Matrix
| Capability | Criticality | Test Files | Coverage Type | Confidence | Gap |
|------------|-------------|------------|---------------|------------|-----|
| ... | gov-critical/core/supporting | path(s) | unit/integ/e2e/none | high/med/low | ... |

### Untested Critical Paths
- [Prioritized list of governance-critical paths without test evidence]

### Recommended Additions
| Priority | Capability | Recommended Test | Type | Rationale |
|----------|------------|------------------|------|-----------|
| P0 | ... | ... | unit/integ | ... |
```

## Governance Notes

- Code coverage percentage alone is insufficient — this skill provides capability-level confidence.
- Governance-critical capabilities require ≥90% coverage per quality contract.
- Untested critical paths are release blockers unless risk-accepted.
- Run before each release milestone and after significant refactoring.
- Test recommendations should be implemented before the next release gate.

## References

- `skills/quality/audit-code.md` — code-level quality assessment (complementary).
- `skills/dev/test-strategy.md` — test design methodology.
- `skills/quality/release-gate.md` — release readiness aggregation.
- `agents/platform-auditor.md` — orchestrator that invokes this skill.
- `context/product/product-contract.md` — capability source.
- `context/product/framework-contract.md` — framework capability source.
- `standards/framework/quality/core.md` — coverage thresholds.
