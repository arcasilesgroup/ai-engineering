---
spec: "040"
total: 27
completed: 0
last_session: "2026-03-09"
next_session: "2026-03-09"
---

# Tasks — Observe Enrichment Phase 2

### Phase 0: Scaffold + Branch [S]
- [x] 0.1 Create spec-040 directory and files
- [x] 0.2 Update `_active.md` to point to spec-040
- [x] 0.3 Create branch `feat/040-observe-enrichment-phase-2`
- [x] 0.4 Commit scaffold

### Phase 1: Fix SonarCloud Token Resolution [S]
- [ ] 1.1 Add `_resolve_sonar_token(project_root) -> str | None` to `policy/checks/sonar.py` — env var → OS keyring → None
- [ ] 1.2 Refactor `query_sonar_quality_gate()` to use `_resolve_sonar_token()`
- [ ] 1.3 Add token resolution tests in `tests/unit/test_sonar_measures.py`

### Phase 2: SonarCloud Measures Expansion [M]
- [ ] 2.1 Add `query_sonar_measures(project_root, metrics) -> dict | None` to `policy/checks/sonar.py`
- [ ] 2.2 Add `sonar_detailed_metrics(project_root) -> dict` to `lib/signals.py` — cached, structured
- [ ] 2.3 Add measures API tests in `tests/unit/test_sonar_measures.py`

### Phase 3: Test Confidence with Fallback [M]
- [ ] 3.1 Add `test_confidence_metrics(project_root) -> dict` to `lib/signals.py` — SonarCloud → coverage.json → test_scope → ∅
- [ ] 3.2 Create `tests/unit/test_test_confidence.py`

### Phase 4: Security Posture with Fallback [S]
- [ ] 4.1 Add `security_posture_metrics(project_root) -> dict` to `lib/signals.py` — SonarCloud → pip-audit → ∅
- [ ] 4.2 Create `tests/unit/test_security_posture.py`

### Phase 5: Wire Session Emitter [S]
- [ ] 5.1 Edit `cli_commands/checkpoint.py` — call `emit_session_event()` after checkpoint save
- [ ] 5.2 Add session emission test in `tests/unit/test_checkpoint_cmd.py`

### Phase 6: Scan/Build Agent Instructions [S]
- [ ] 6.1 Edit `agents/scan.md` — add post-scan emission step
- [ ] 6.2 Edit `agents/build.md` — add post-build emission step

### Phase 7: Dashboard Expansion [M]
- [ ] 7.1 Expand `observe_engineer()` — add Security Posture section
- [ ] 7.2 Expand `observe_engineer()` — add Test Confidence section
- [ ] 7.3 Expand `observe_engineer()` — enrich SonarCloud section (complexity, duplication, issues)
- [ ] 7.4 Expand `observe_health()` — add sonar_score and test_confidence_score components
- [ ] 7.5 Update `tests/unit/test_cli_observe.py` — new section assertions
- [ ] 7.6 Update `tests/unit/test_observe_dashboards.py` — new section assertions

### Phase 8: Verification [S]
- [ ] 8.1 `ruff check` + `ruff format` — zero errors
- [ ] 8.2 `ty` — no new errors
- [ ] 8.3 `pytest` — all tests pass
- [ ] 8.4 `ai-eng observe engineer` — shows Security Posture, Test Confidence, enriched SonarCloud
- [ ] 8.5 `ai-eng observe health` — shows 7 components
