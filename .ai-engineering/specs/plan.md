# Plan: spec-060 CI & Install Smoke Audit — Eliminate False Positives

## Pipeline: standard
## Phases: 4
## Tasks: 15 (build: 11, verify: 4)

### Phase 1: CI Workflow Fixes
**Gate**: All 5 CI fixes applied to `ci.yml`. Workflow passes `actionlint`.

- [x] T-1.1: Fix paths-filter to include workflow files (agent: build)
- [x] T-1.2: Fix Snyk to use change-scope output for token check (agent: build)
- [x] T-1.3: Fix gate trailers to validate all non-merge PR commits (agent: build)
- [x] T-1.4: Fix SonarCloud coverage verification (agent: build)
- [x] T-1.5: Fix semgrep skip ratio check (agent: build)

### Phase 2: CLI Code Changes (TDD)
**Gate**: All tests pass. `ruff check` and `ruff format --check` clean.

- [x] T-2.1: Write failing tests for doctor exit codes and has_warnings (agent: build) [RED]
- [x] T-2.2: Implement doctor exit codes and has_warnings (agent: build) [GREEN]
- [x] T-2.3: Write failing tests for --non-interactive install (agent: build) [RED]
- [x] T-2.4: Implement --non-interactive flag (agent: build) [GREEN]
- [x] T-2.5: Verify _cli_error_boundary coverage for install (agent: build)
- [x] T-2.6: Run full test suite to verify no regressions (agent: verify)

### Phase 3: Install Smoke Workflow
**Gate**: `install-smoke.yml` updated with all fixes. Passes `actionlint`.

- [x] T-3.1: Update install-smoke.yml with all fixes (agent: build)
- [x] T-3.2: Validate workflow YAML with actionlint (agent: verify)

### Phase 4: Final Verification
**Gate**: All acceptance criteria from spec-060 verified with evidence.

- [x] T-4.1: Verify all spec-060 acceptance criteria (agent: verify)
- [x] T-4.2: Run workflow policy checks (agent: verify)
