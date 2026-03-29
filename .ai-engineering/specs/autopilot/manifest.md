# Autopilot Manifest: spec-088

## Split Strategy
by-concern: each sub-spec is an independent functional concern. Hooks (sub-002) is the largest; instincts (sub-004) depends on it.

## Sub-Specs

| # | Title | Status | Depends On | Files (best guess) |
|---|-------|--------|------------|---------------------|
| sub-001 | Manifest Dedup | planning | None | `manifest.yml` x2 |
| sub-002 | Cross-IDE Hook Compatibility | planning | None | 8 hook scripts + settings files |
| sub-003 | Test Strategy: Directory-Based | planning | None | `stack_runner.py` + ~80 test files |
| sub-004 | Instincts Pipeline Fix | planning | sub-002 | 3 hook/lib files |
| sub-005 | Runbook: Work Item Consolidation | planning | None | 1 new runbook |

## Totals
- Sub-specs: 5
- Dependency chain depth: 2 (sub-002 -> sub-004)

## Traceability

| Spec Goal | Sub-Spec(s) |
|-----------|-------------|
| G1: Manifest dedup | sub-001 |
| G2: Hooks cross-IDE | sub-002 |
| G3: Tests by directory | sub-003 |
| G4: Instincts pipeline | sub-004 |
| G5: Consolidation runbook | sub-005 |
