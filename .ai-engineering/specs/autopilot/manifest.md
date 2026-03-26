# Autopilot Manifest: spec-079

## Split Strategy
By-concern: each sub-spec maps 1:1 to a spec-079 sub-spec (B, C, A, D, E, F) re-numbered sequentially. Dependencies driven by shared files (governance.py, CLAUDE.md, copilot-instructions.md).

## Sub-Specs

| # | Title | Status | Depends On | Tasks | Confidence |
|---|-------|--------|------------|-------|------------|
| sub-001 | Hooks Cleanup | planned | None | 7 | HIGH 95% |
| sub-002 | Eliminate contexts/orgs | planned | None | 7 | HIGH |
| sub-003 | Project Identity — replace contracts | planned | sub-002 | 27 | 8/10 |
| sub-004 | Context Loading Enforcement + Language Cleanup | planned | sub-003 | 12 | 95% |
| sub-005 | Install Fixes — team/ and specs/ | planned | sub-003 | 7 | HIGH |
| sub-006 | README.md Overhaul | planned | sub-003, sub-004, sub-005 | 4 | 95% |

## Totals
- Sub-specs: 6
- Total tasks: 64
- Dependency chain depth: 4 (Wave 1 → Wave 2 → Wave 3 → Wave 4)

## Coverage Traceability

| Spec Section | Sub-Spec(s) |
|--------------|-------------|
| Sub-spec A: Project Identity | sub-003 |
| Sub-spec B: Hooks Cleanup | sub-001 |
| Sub-spec C: Eliminate contexts/orgs | sub-002 |
| Sub-spec D: Context Loading Enforcement | sub-004 |
| Sub-spec E: Install Fixes | sub-005 |
| Sub-spec F: README Overhaul | sub-006 |
| Migration Path (existing installations) | sub-003 |
| Acceptance Criteria | all sub-specs |

## Execution DAG

Wave 1 (parallel): sub-001, sub-002
Wave 2 (serial, after Wave 1): sub-003
Wave 3 (parallel, after Wave 2): sub-004, sub-005
Wave 4 (serial, after Wave 3): sub-006

### Dependency Edges
- sub-002 -> sub-003 (file overlap: defaults.py)
- sub-003 -> sub-004 (imports: CLAUDE.md project-identity instruction; file overlap: CLAUDE.md, copilot-instructions.md)
- sub-003 -> sub-005 (file overlap: governance.py, test_install_clean.py)
- sub-003 -> sub-006 (imports: final skill count, project-identity existence)
- sub-004 -> sub-006 (imports: final language count = 14, lang-generic.md)
- sub-005 -> sub-006 (imports: team seed files = 2, specs/ directory)

### Corrections from Deep Plan
- Language count: 14 (not 13) — rust.md stays. Sub-006 must use 14 in README.
- sub-003 depends on sub-002 (both touch defaults.py) — added dependency edge.

## Deep Plan Summary
- Planned: 6 of 6 sub-specs
- Failed: 0 sub-specs
- Confidence distribution: 4 high, 2 medium-high (sub-003 8/10, all others 95%+)
