---
spec: "030"
total: 28
completed: 28
last_session: "2026-03-02"
next_session: "Done - verification + commit + PR"
---

# Tasks - Sonar CI/CD Pipeline Integration

## Phase 0: Scaffold + decisions [M]

- [x] 0.1 Create spec-030 scaffold (`spec.md`, `plan.md`, `tasks.md`)
- [x] 0.2 Activate spec-030 in `_active.md`
- [x] 0.3 Align product-contract Active Spec pointer
- [x] 0.4 Persist D030-001..D030-004 in decision-store

## Phase 1: Models + setup extension [M]

- [x] 1.1 Add `organization` field to `SonarConfig`
- [x] 1.2 Add `--organization` option to `setup sonar` command
- [x] 1.3 Implement `_read_sonar_organization()` property reader
- [x] 1.4 Persist resolved organization in `tools.json`
- [x] 1.5 Add `SonarCicdConfig` and wire `CicdStatus.sonar`

## Phase 2: Pipeline generation + wiring [L]

- [x] 2.1 Extend `generate_pipelines()` signature with optional `sonar_config`
- [x] 2.2 Render GitHub Sonar analysis (Cloud/Qube split, fetch-depth, fork guard)
- [x] 2.3 Render Azure Sonar analysis (Cloud/Qube split, service connection fallback)
- [x] 2.4 Wire Sonar config resolution in `cicd_regenerate`
- [x] 2.5 Wire Sonar config resolution in installer operational phase
- [x] 2.6 Generate create-only `sonar-project.properties` during install when configured

## Phase 3: Compliance + injector + templates + docs [M]

- [x] 3.1 Add informational Sonar pattern check in compliance scanner (`ci.yml` only)
- [x] 3.2 Add Sonar snippet generators and `type="sonar"` injection suggestions
- [x] 3.3 Add pipeline templates (`github-sonar-step.yml`, `azure-sonar-task.yml`)
- [x] 3.4 Add `sonar-project.properties` template
- [x] 3.5 Update `cicd-generate` skill docs and template mirror

## Phase 4: Advisory pre-push gate [M]

- [x] 4.1 Implement advisory `_check_sonar_gate()` wrapper in `policy/gates.py`
- [x] 4.2 Wire Sonar check ordering in `_run_pre_push_checks()`

## Phase 5: Tests + verification [L]

- [x] 5.1 Add CI Sonar renderer tests (`test_cicd_sonar.py`)
- [x] 5.2 Extend state/setup/credentials tests for new Sonar fields and parsing
- [x] 5.3 Extend compliance/injector tests for informational Sonar checks and snippets
- [x] 5.4 Extend gates tests for advisory skip/fail/pass scenarios
- [x] 5.5 Extend installer tests for sonar passthrough
- [x] 5.6 Run targeted sonar tests and full suite with coverage threshold
