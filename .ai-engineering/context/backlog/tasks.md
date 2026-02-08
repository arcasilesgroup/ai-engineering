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
