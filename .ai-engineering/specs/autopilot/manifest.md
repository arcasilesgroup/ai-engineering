# Autopilot Manifest: spec-090

## Split Strategy
Hybrid (by-domain + by-dependency): separated by domain concept (lessons consolidation, instinct schema, skill behavior, improvement funnel) with a final cross-cutting sub-spec for mirrors and tests.

## Sub-Specs

| # | Title | Status | Depends On | Tasks |
|---|-------|--------|------------|-------|
| sub-001 | LESSONS.md Consolidation | planned | None | 6 |
| sub-002 | Instincts v2 Schema + Extraction | planned | None | 8 |
| sub-003 | Instinct Skill Rewrite - Listening + Review | planned | sub-002 | 5 |
| sub-004 | Improvement Funnel - Proposals + Work Items | planned | sub-002, sub-003 | 4 |
| sub-005 | Reference Updates, Mirrors + Tests | planned | sub-001, sub-002, sub-003, sub-004 | 6 |

## Execution DAG

```
Wave 1: sub-001 (6 tasks) + sub-002 (8 tasks)     [parallel, independent]
Wave 2: sub-003 (5 tasks)                           [depends on sub-002]
Wave 3: sub-004 (4 tasks)                           [depends on sub-002 + sub-003]
Wave 4: sub-005 (6 tasks)                           [depends on all]
```

## Deep Plan Summary
- Planned: 5 of 5 sub-specs
- Failed: 0
- Confidence distribution: 4 high, 1 medium (sub-004: work item CLI dependency)
- Total tasks: 29

## Coverage Validation

| Spec Decision | Sub-Spec(s) |
|---------------|-------------|
| D-090-01: LESSONS.md path | sub-001, sub-005 |
| D-090-02: Eliminate learnings/ | sub-001, sub-005 |
| D-090-03: /ai-learn refactor | sub-001 |
| D-090-04: New pattern families | sub-002 |
| D-090-05: Confidence scoring | sub-002 |
| D-090-06: instincts.yml v2 schema | sub-002 |
| D-090-07: Three-leg observation | sub-003 |
| D-090-08: Eliminate context.md | sub-002, sub-005 |
| D-090-09: Ownership rule | sub-001, sub-004 |
| D-090-10: Observation format | sub-002 |
| D-090-11: Improvement funnel | sub-004 |
| D-090-12: File structure + call points | sub-003, sub-004 |

All 12 decisions covered. No orphans.

## Orchestrate Summary
- File overlaps: 3 pairs (all safe — either parallel-safe or already serialized by DAG)
- Import chains: 7 edges (all satisfied by wave ordering)
- Merges: 0 (no unresolvable conflicts)
- Cycles: 0
- DAG validated: PASSED

## Totals
- Sub-specs: 5
- Total tasks: 29
- Dependency chain depth: 4 waves
