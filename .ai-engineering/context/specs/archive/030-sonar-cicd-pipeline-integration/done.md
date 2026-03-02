---
spec: "030"
status: "complete"
completed: "2026-03-02"
branch: "spec/030-sonar-cicd-pipeline-integration"
---

# Done — Sonar CI/CD Pipeline Integration

## Summary

Added Sonar-aware CI/CD pipeline generation for GitHub Actions and Azure Pipelines, extended `ai-eng setup sonar` with organization resolution, added `sonar-project.properties` create-only generation, compliance/injector Sonar detection, and advisory pre-push Sonar gate execution — all preserving silent-skip behavior for non-Sonar teams.

## Deliverables

### Models & Setup

- `SonarConfig.organization` field with `tools.json` persistence.
- `--organization` CLI option with precedence: CLI > `sonar-project.properties` > empty.
- `SonarCicdConfig` state model and `CicdStatus.sonar` wiring.

### Pipeline Generation

- GitHub `ci.yml` Sonar step: `fetch-depth: 0`, Cloud/Qube action split, fork secret guard.
- Azure `ci.yml` Sonar tasks: Prepare/Analyze/Publish, Cloud/Qube family split, service connection fallback.
- Sonar config passthrough in install and regenerate flows with manifest status persistence.

### Compliance & Templates

- Informational `sonar-analysis-present` compliance check for primary `ci.yml` (never blocking).
- Sonar snippet generators and `type="sonar"` injection suggestions.
- Pipeline templates: `github-sonar-step.yml`, `azure-sonar-task.yml`, `sonar-project.properties`.

### Advisory Gate

- Advisory `_check_sonar_gate()` in `policy/gates.py` — surfaces failures, never blocks push.
- Integrated in `_run_pre_push_checks()` ordering.

### Tests

- `test_cicd_sonar.py`: CI Sonar renderer coverage (enabled/disabled, Cloud/Qube, both providers).
- Extended: credentials, setup, state, compliance, injector, gates, and installer test suites.

## Quality Gate

| Check | Result |
|-------|--------|
| Tasks | 28/28 completed |
| PR | #71 merged |
| Commit | `4792e08` |
| Gates | all pass |

## Key Decisions

| ID | Decision |
|----|----------|
| D030-001 | Organization precedence: `--organization` > `sonar-project.properties` > empty. |
| D030-002 | Azure service connection: config first, `$(SONAR_SERVICE_CONNECTION)` fallback. |
| D030-003 | Pre-push Sonar gate is advisory — never blocks push. |
| D030-004 | SonarCloud detection via normalized `urlparse(host_url).hostname`. |

## Phases Completed

1. Phase 0: Scaffold + decisions
2. Phase 1: Models + setup extension
3. Phase 2: Pipeline generation + wiring
4. Phase 3: Compliance + injector + templates + docs
5. Phase 4: Advisory pre-push gate
6. Phase 5: Tests + verification

## Learnings

- Silent-skip pattern (from D024-002) works well as a cross-cutting concern — Sonar integration touches 9+ modules without impacting non-Sonar teams.
- Normalized URL parsing via `urlparse` is more robust than substring matching for platform detection (mixed-case, trailing slashes, ports).
- Create-only semantics for generated files prevents overwriting user customizations while still providing useful defaults.
