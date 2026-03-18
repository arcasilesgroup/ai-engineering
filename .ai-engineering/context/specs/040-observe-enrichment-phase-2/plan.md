---
spec: "040"
phases: 8
agents: [build, scan]
---

# Plan — Observe Enrichment Phase 2

## Architecture

### Token Resolution (shared helper)
```
SONAR_TOKEN env var → CredentialService.retrieve("sonar", "token") → None
```

### Fallback Chains
```
Coverage:   SonarCloud /measures → coverage.json (local) → test_scope mapping → ∅
Security:   SonarCloud /measures → pip-audit (local) → ∅
Complexity: SonarCloud /measures → ∅
Duplication: SonarCloud /measures → ∅
Quality Gate: SonarCloud /qualitygates → ∅
```

### Data Flow
```
sonar.py:_resolve_sonar_token()     ← shared by all Sonar functions
sonar.py:query_sonar_quality_gate() ← existing (fix token resolution)
sonar.py:query_sonar_measures()     ← NEW (coverage, complexity, vulns)
    ↓
signals.py:sonar_detailed_metrics()    ← cache + structure
signals.py:test_confidence_metrics()   ← SonarCloud → local → scope → ∅
signals.py:security_posture_metrics()  ← SonarCloud → pip-audit → ∅
    ↓
observe.py:observe_engineer()  ← Security Posture, Test Confidence, enriched SonarCloud
observe.py:observe_health()    ← +sonar_score, +test_confidence_score
```

## Session Map

| Phase | Agent | Tasks | Gate |
|-------|-------|-------|------|
| 0 | execute | Scaffold spec, create branch | Branch ready |
| 1 | build | Fix SonarCloud token resolution | Token test passes |
| 2 | build | SonarCloud measures expansion | Measures test passes |
| 3 | build | Test confidence with fallback | Fallback chain tests pass |
| 4 | build | Security posture with fallback | Fallback chain tests pass |
| 5 | build | Wire session emitter | Emission test passes |
| 6 | build | Scan/build agent instructions | N/A (governance) |
| 7 | build | Dashboard expansion | Dashboard tests pass |
| 8 | scan | Verification | ruff + ty + pytest all green |

## Execution Order

- Phase 1 → Phase 2 (measures needs fixed token resolution)
- Phase 3, 4, 5, 6 can run in parallel (independent)
- Phase 7 depends on 2, 3, 4 (dashboard needs new signal functions)
- Phase 8 runs last (verification)

## Files (14)

| # | File | Action |
|---|------|--------|
| 1 | `src/ai_engineering/policy/checks/sonar.py` | Edit — `_resolve_sonar_token()`, fix `query_sonar_quality_gate()`, add `query_sonar_measures()` |
| 2 | `src/ai_engineering/lib/signals.py` | Edit — 3 new functions |
| 3 | `src/ai_engineering/cli_commands/observe.py` | Edit — Security Posture, Test Confidence, enriched SonarCloud, health expansion |
| 4 | `src/ai_engineering/cli_commands/checkpoint.py` | Edit — wire session emitter |
| 5 | `.ai-engineering/agents/verify.md` | Edit — emission step |
| 6 | `.ai-engineering/agents/build.md` | Edit — emission step |
| 7 | `tests/unit/test_sonar_measures.py` | Create |
| 8 | `tests/unit/test_test_confidence.py` | Create |
| 9 | `tests/unit/test_security_posture.py` | Create |
| 10 | `tests/unit/test_cli_observe.py` | Edit |
| 11 | `tests/unit/test_observe_dashboards.py` | Edit |
| 12 | `tests/unit/test_checkpoint_cmd.py` | Edit |
| 13 | `tests/unit/test_sonar_gate.py` | Edit — verify token resolution fix |
| 14 | `tests/unit/test_signal_aggregators.py` | Edit |
