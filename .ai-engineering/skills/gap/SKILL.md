---
name: gap
description: "Detect spec-vs-code gaps and wiring gaps (implemented but disconnected code): unimplemented features, dead specs, acceptance criteria coverage, disconnected implementations."
metadata:
  version: 1.1.0
  tags: [scanning, gap-analysis, specs, verification, features, wiring, dead-code-functional]
  ai-engineering:
    scope: read-only
    token_estimate: 800
---

# Feature Gap

## Purpose

Detect gaps between specifications and implementation, AND between implementation and integration. Identifies unimplemented features, dead specs, missing acceptance criteria coverage, undocumented dependencies, and disconnected implementations (code built but not wired).

## Trigger

- Command: `/ai:scan feature`
- Context: pre-release verification, post-implementation alignment check, spec audit.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"feature-gap"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## Procedure

1. **Read spec hierarchy** -- load `_active.md` -> `spec.md`, `plan.md`, `tasks.md`. Extract all requirements, features, milestones, acceptance criteria.

2. **Read codebase** -- map modules, packages, APIs, entities, test files. Build implementation inventory.

3. **Cross-reference** -- for each spec requirement, search codebase for implementation:
   - **Implemented**: matching code found with evidence
   - **Partially implemented**: code exists but incomplete
   - **Missing**: no corresponding implementation found

4. **Map test coverage** -- for each acceptance criterion, find corresponding tests:
   - **Covered**: test directly validates the criterion
   - **Partial**: test exists but incomplete coverage
   - **Uncovered**: no test found

5. **Detect dead specs** -- specs referencing artifacts no longer in codebase.

5.5. **Detect wiring gaps** -- code implemented but not connected:
   - Functions/classes exported but never imported by any consumer
   - Endpoints defined but not registered in router
   - Handlers/listeners defined but not subscribed to events
   - Modules complete but with zero importers
   - CLI commands defined but not registered in command registry
   - Category: **Disconnected** (implemented, not wired)

6. **Report** -- uniform scan output contract with score 0-100 and findings.

## Output

```markdown
# Scan Report: feature-gap

## Score: N/100
## Verdict: PASS | WARN | FAIL

## Findings
| # | Severity | Category | Description | Location | Remediation |

## Traceability Matrix
| Requirement | Implementation | Tests | Status |

## Wiring Matrix
| Implementation | Type | Expected Consumer | Connected | Status |
```

## When NOT to Use

- **Code quality metrics** (coverage, complexity) — use `quality` instead.
- **Security vulnerability scanning** — use `security` instead.
- **Architecture analysis** (coupling, cohesion) — use `architecture` instead.
- **Bug investigation** — use `debug` instead.

## Examples

### Example 1: Pre-release feature verification

User says: "Verify all spec-050 requirements are implemented before release."
Actions:

1. Load spec-050 requirements, cross-reference with codebase, and map test coverage per acceptance criterion.
2. Detect any wiring gaps: code built but not registered in CLI or router.
   Result: Traceability matrix showing implemented/missing/partial status for every requirement.

### Example 2: Dead spec detection after refactor

User says: "We removed the old auth module. Check for dead specs."
Actions:

1. Scan specs referencing auth module artifacts and verify they still exist in codebase.
2. Flag specs with broken references as dead.
   Result: List of specs that need updating or archiving.

## Governance Notes

- Feature-gap is read-only — produces reports, does not modify code.
- Wiring gaps (implemented but disconnected) are distinct from missing features.
- Critical wiring gaps (CLI commands defined but unregistered) are blocking for release.
- Dead specs should be flagged for archive via cleanup skill.

### Iteration Limits

- Max 3 attempts to resolve ambiguous cross-references before escalating.

## References

- `agents/scan.md` — agent that invokes this skill as part of 7-mode assessment.
- `skills/architecture/SKILL.md` — complementary architecture analysis.
- `skills/cleanup/SKILL.md` — handles dead spec archival.
