---
id: "040"
slug: "observe-enrichment-phase-2"
status: "in-progress"
size: "M"
pipeline: "standard"
branch: "feat/040-observe-enrichment-phase-2"
decisions: []
---

# Spec 040 — Observe Enrichment Phase 2: SonarCloud + Test Confidence + Emitter Wiring

## Problem

After spec-039, observe dashboards are at ~65% of the observe agent spec. Key gaps:
1. **SonarCloud data underutilized** — only quality gate status + `new_coverage` used; `/api/measures/component` provides coverage %, complexity, duplication, vulnerabilities, security hotspots, and ratings
2. **Token resolution bug** — `query_sonar_quality_gate()` checks `tools.json.sonar.configured` but never retrieves the stored token from OS keyring; users who ran `ai-eng setup sonar` get no SonarCloud data
3. **No Test Confidence metric** — observe agent spec requires "% capabilities tested, untested critical paths"; infrastructure exists (pytest-cov, test_scope.py, SonarCloud coverage) but no aggregation
4. **No Security Posture section** — observe agent spec requires "open vulns, secrets, dep vulns"; SonarCloud has this data
5. **3 emitters dead** — `emit_scan_event`, `emit_build_event`, `emit_session_event` defined but never called

## Solution

1. Fix SonarCloud token resolution: `SONAR_TOKEN` env → OS keyring → None (fail-open)
2. Add `query_sonar_measures()` for detailed metrics (coverage, complexity, duplication, security)
3. Add Test Confidence metric with fallback: SonarCloud → local coverage.json → test_scope mapping
4. Add Security Posture metric with fallback: SonarCloud → pip-audit → "No data"
5. Wire session emitter in checkpoint save
6. Update scan/build agent instructions to emit events via `ai-eng signals emit`
7. Expand engineer + health dashboards with new sections

## Scope

### In Scope
- Fix SonarCloud token resolution bug in `sonar.py`
- New `query_sonar_measures()` API function
- 3 new signal aggregators: `sonar_detailed_metrics`, `test_confidence_metrics`, `security_posture_metrics`
- Engineer dashboard: Security Posture, Test Confidence, enriched SonarCloud sections
- Health dashboard: 2 new score components (sonar, test confidence)
- Session emitter wired in checkpoint save
- Scan/build agent instruction updates

### Out of Scope
- Skill invocation tracking (needs `skill_invoked` event type — Phase 3)
- Agent dispatch tracking (needs `agent_dispatch` event type — Phase 3)
- MTTR (needs issue tracker integration — Phase 4)
- 4-week trend history (needs accumulated data — Phase 3)

## Acceptance Criteria

1. `_resolve_sonar_token()` resolves from env var, then OS keyring, then returns None
2. `query_sonar_measures()` returns coverage, complexity, duplication, vulns when configured
3. Both SonarCloud functions fail-open when unconfigured
4. Test Confidence shows coverage from best available source with source indicator
5. Security Posture shows vulns from SonarCloud with pip-audit fallback
6. `ai-eng observe engineer` shows Security Posture, Test Confidence, enriched SonarCloud
7. `ai-eng observe health` includes sonar_score and test_confidence_score components
8. `checkpoint save` emits `session_metric` event
9. `agents/scan.md` includes emission step
10. `agents/build.md` includes emission step
11. All tests pass, ruff clean, ty clean

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SonarCloud API rate-limited | LOW | LOW | Cache per-session, single call per observe |
| SONAR_TOKEN not set locally | MEDIUM | LOW | Fallback chain, show "run ai-eng setup sonar" |
| pip-audit slow or missing | LOW | LOW | Subprocess timeout, fail-open |
| pytest-cov not in addopts | LOW | LOW | Read cached coverage.json, don't force run |

## Decisions

- D040-001: Reuse existing `CredentialService` for token resolution (no new credential infrastructure)
- D040-002: Fallback chain per metric (SonarCloud → local → structural → "No data")
- D040-003: Module-level cache for SonarCloud measures (avoid repeat API calls per session)
