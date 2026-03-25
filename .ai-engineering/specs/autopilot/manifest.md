# Autopilot Manifest: spec-074

## Split Strategy
By-domain: schema/migration (sub-001), release behavior (sub-002), verify implementation (sub-003). All independent with zero file overlap.

## Sub-Specs

| # | Title | Status | Depends On | Files |
|---|-------|--------|------------|-------|
| sub-001 | Provider/IDE Field Separation | planned | None | `config/manifest.py`, `config/loader.py`, `cli_commands/provider.py`, `installer/operations.py`, `installer/phases/ide_config.py`, `doctor/phases/ide_config.py`, `installer/service.py`, `lib/signals.py`, tests x4, `manifest.yml` x2 |
| sub-002 | Release Flow Fix | planned | None | `release/orchestrator.py`, `tests/unit/test_release_orchestrator.py` |
| sub-003 | Verify Governance Direct Import | planned | None | `verify/service.py`, `tests/unit/test_verify_service.py` |

## Totals
- Sub-specs: 3
- Dependency chain depth: 0 (all independent)

## Coverage Traceability

```
Spec Group 1 (Provider/IDE Separation) -> sub-001
Spec Group 2 (Release Flow Fix)        -> sub-002
Spec Group 3 (Verify Governance)       -> sub-003
AC1-AC8 (provider/ide verification)    -> sub-001
AC9-AC10 (release verification)        -> sub-002
AC11-AC12 (verify verification)        -> sub-003
AC13-AC14 (cross-cutting quality)      -> Phase 5 quality loop
```
