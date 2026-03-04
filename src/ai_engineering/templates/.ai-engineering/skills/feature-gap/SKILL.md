---
name: feature-gap
description: "Detect spec-vs-code gaps: unimplemented features, dead specs, acceptance criteria coverage."
metadata:
  version: 1.0.0
  tags: [scanning, gap-analysis, specs, verification, features]
  ai-engineering:
    scope: read-only
    token_estimate: 800
---

# Feature Gap

## Purpose

Detect gaps between specifications and implementation. Identifies unimplemented features, dead specs, missing acceptance criteria coverage, and undocumented dependencies.

## Trigger

- Command: `/ai:scan feature`
- Context: pre-release verification, post-implementation alignment check, spec audit.

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
```
