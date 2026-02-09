# Tasks

## Document Metadata

- Doc ID: BL-TASKS
- Owner: project-managed (backlog)
- Status: active
- Last reviewed: 2026-02-09
- Source of truth: `.ai-engineering/context/backlog/tasks.md`

## Update Metadata

- Rationale: keep backlog tasks focused on active executable work and move historical execution logs to delivery evidence.
- Expected gain: lower planning noise and faster backlog-to-delivery navigation for humans and AI agents.
- Potential impact: phase history is no longer maintained in this file.

## P0 Task Catalog

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

## P1 Task Catalog

- T-013 implement weekly maintenance-agent local reports.
- T-014 implement report-to-PR workflow after approval.
- T-015 implement context compaction checks and redundancy metrics.

## Active Execution Queue (Now)

- [ ] T-016 close carry-over item B-007: richer doctor/install readiness and ownership-safe update hook extensions.
- [ ] T-017 close carry-over item F-007: execute charter workstreams W1-W5 end-to-end.
- [ ] T-018 close carry-over item H-005: advanced merge strategy and migration hooks in updater.
- [ ] T-019 close carry-over item K-006: Windows-safe hook launcher hardening.

## Definition of Done

- all P0 tasks merged with tests.
- cross-OS verification green on Windows, macOS, and Linux.
- quality and security gates green: `unit`, `integration`, `e2e`, `ruff`, `ty`, `gitleaks`, `semgrep`, `pip-audit`.

## Delivery and History References

- phase execution history: `.ai-engineering/context/delivery/evidence/execution-history.md`
- implementation decision log: `.ai-engineering/context/delivery/implementation.md`
- traceability mapping: `.ai-engineering/context/backlog/traceability-matrix.md`

## Backlog Maintenance Log

- [x] P-001 split active backlog tasks from historical phase execution logs.
- [x] P-002 add active status board and backlog index entrypoint.
- [x] P-003 re-point historical execution tracking to delivery evidence archive.
- [x] Q-001 normalize document metadata headers across backlog and delivery artifacts.
- [x] Q-002 add pre-merge backlog/delivery documentation checklist to review gates.
- [x] R-001 add automated docs contract check to governance pre-commit gates.
- [x] R-002 add CLI command to run docs contract check directly (`ai gate docs`).
- [x] R-003 add unit tests for docs contract gate behavior.
