# Tasks

## Update Metadata

- Rationale: sequence tasks according to architecture dependencies.
- Expected gain: faster MVP execution with fewer blockers.
- Potential impact: task IDs and ordering changed from previous drafts.

## P0 Tasks

- T-001 implement installer creation of required ownership/state files.
- T-002 implement ownership map enforcement in updater.
- T-003 implement standards resolver for framework/team precedence.
- T-004 implement mandatory hook setup and tamper detection.
- T-005 integrate `gitleaks` and `semgrep` local checks.
- T-006 integrate `pip-audit`, `ruff`, `ty`, and tests in gate flows.
- T-007 implement command runtime for `/commit`, `/pr`, `/acho`.
- T-008 implement `/pr --only` warning + continuation modes.
- T-009 implement decision-store read/write and reuse rules.
- T-010 implement append-only audit logging in ndjson format.
- T-011 implement readiness validator for `gh`, `az`, hooks, and stack tooling.
- T-012 implement sources lock/cache handling with checksum + signature metadata fields.

## P1 Tasks

- T-013 implement weekly maintenance-agent local reports.
- T-014 implement report-to-PR workflow after approval.
- T-015 implement context compaction checks and redundancy metrics.

## Definition of Done

- all P0 tasks merged with tests.
- cross-OS verification green on Windows, macOS, and Linux.

## Phase A Execution Log

- [x] A-001 create root `AGENTS.md` aligned with governance contract.
- [x] A-002 align `CLAUDE.md` with command/security/ownership contract.
- [x] A-003 align root `README.md` with current product contract.
- [x] A-004 harden `.claude/settings.local.json` by removing wildcard permissions.
- [x] A-005 align `pyproject.toml` to Astral-first baseline metadata.
- [x] A-006 run Phase A validations and record outputs.
- [x] A-007 publish Phase A completion note in implementation log.

## Phase B Execution Log

- Rationale: move from contract alignment to executable framework baseline.
- Expected gain: enforceable state contracts and runnable CLI bootstrap commands.
- Potential impact: introduces new module boundaries and runtime entrypoints.

- [x] B-001 scaffold core packages (`cli`, `state`, `installer`, `doctor`, `detector`, `hooks`, `policy`, `standards`, `skills`, `updater`).
- [x] B-002 implement state schemas and JSON/ndjson I/O helpers.
- [x] B-003 implement default state payload generators for installer bootstrap.
- [x] B-004 implement minimal `ai install` and `ai doctor` commands.
- [x] B-005 add unit and integration tests for schema and CLI baseline.
- [x] B-006 run quality checks (`ruff`, `pytest`, `ty`, `pip-audit`) in project virtualenv.
- [ ] B-007 extend doctor/install behavior for richer readiness and ownership-safe update hooks.
