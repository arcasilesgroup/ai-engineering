---
spec: "038"
status: "complete"
completed: "2026-03-09"
branch: "feat/038-sonarcloud-quality-gate-integration"
---

# Done — SonarCloud Quality Gate Integration

## Summary

Completed end-to-end SonarCloud Quality Gate integration: migrated deprecated GitHub Action, added `sonar.qualitygate.wait=true` as universal gate mechanism in `sonar-project.properties`, wired coverage XML export to CI, added SonarCloud job to the repo's real CI, extended pre-push gate with API consultation, and added Sonar metrics to the engineer observe dashboard. All preserving silent-skip for non-Sonar teams.

## Deliverables

### Properties Template (D038-001, D038-002)

- `sonar-project.properties` template expanded with `sonar.qualitygate.wait=true`, `sonar.qualitygate.timeout=300`, stack-aware coverage paths (Python/dotnet/nextjs), sources, tests, and exclusions.
- Template variable `{tests}` added to installer service for stack-aware test path resolution.

### Action Migration (D038-003)

- `_render_github_sonar_steps`: migrated from deprecated `SonarSource/sonarcloud-github-action@v3` to unified `SonarSource/sonarqube-scan-action@v4` for both SonarCloud and SonarQube.
- Single code path for both platforms — only args differ (organization for Cloud, host.url for Server).

### Coverage Export (D038-004)

- GitHub CI templates: coverage report generation per stack (Python `--cov-report=xml`, dotnet `XPlat Code Coverage`, nextjs `c8 --reporter=lcov`).
- Azure CI templates: same coverage steps with displayName.
- Real CI (`ci.yml`): coverage job now exports `coverage.xml` alongside `.coverage`.

### CI Real Wiring

- `sonar-project.properties` at repo root for `arcasilesgroup/ai-engineering`.
- SonarCloud job in `.github/workflows/ci.yml`: depends on coverage, fork guard, `sonarqube-scan-action@v4`, reads properties automatically.
- `SONAR_TOKEN` required as GitHub secret (manual setup).

### Release Gate + Observe

- `check_sonar_gate` extended: when scanner unavailable, falls back to SonarCloud Web API (`/api/qualitygates/project_status`).
- `query_sonar_quality_gate()` public function for API consultation with full silent-skip chain.
- `_parse_properties()` utility for reading `sonar-project.properties`.
- Engineer observe dashboard shows SonarCloud Quality Gate status, new code coverage, and condition count — silent-skip when unconfigured.

### Tests

- `test_cicd_sonar.py`: 11 tests — unified action, coverage per stack (Python/dotnet/nextjs), no-sonar baseline.
- `test_sonar_gate.py`: 13 tests — properties parsing, API query skip logic, observe metrics.
- Full suite: 1158 tests, all passed.

## Quality Gate

| Check | Result |
|-------|--------|
| Tasks | 17/17 completed |
| Unit tests | 1158 passed |
| Lint | All checks passed |
| Format | All files formatted |

## Key Decisions

| ID | Decision |
|----|----------|
| D038-001 | `sonar.qualitygate.wait=true` in `sonar-project.properties` — universal, all platforms |
| D038-002 | `sonar.qualitygate.timeout=300` — 5 min polling |
| D038-003 | Migrated `sonarcloud-github-action@v3` (deprecated) → `sonarqube-scan-action@v4` (unified) |
| D038-004 | Coverage format: Cobertura XML (universal) |
| D038-005 | Release gate Sonar check: advisory (never blocks) |
| D038-006 | Fork guard on all CI Sonar steps |

## Manual Step Required

- Configure `SONAR_TOKEN` as GitHub secret in the `arcasilesgroup/ai-engineering` repository settings.
