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

## Phase C Execution Log

- Rationale: activate governance and security checks in real git workflows.
- Expected gain: local enforcement catches violations before remote integration.
- Potential impact: direct commit/push attempts on protected branches are blocked.

- [x] C-001 replace placeholder hooks with managed hook scripts.
- [x] C-002 add hook integrity verification in doctor readiness checks.
- [x] C-003 implement gate engine for `pre-commit`, `commit-msg`, and `pre-push` stages.
- [x] C-004 enforce protected branch blocking for `main` and `master` commit/push operations.
- [x] C-005 integrate mandatory tools: `ruff`, `gitleaks`, `semgrep`, `pip-audit`, `pytest`, `ty`.
- [x] C-006 add policy and integration tests for hook/gate behavior.
- [x] C-007 improve failed-check remediation output and branch-policy discovery.

## Phase D Execution Log

- Rationale: operationalize user-facing command contract with governance guardrails.
- Expected gain: predictable command behavior for commit/push/PR workflows.
- Potential impact: CLI now orchestrates git/gh operations directly and can fail on governance checks.

- [x] D-001 implement `commit` workflow (`stage + commit` and optional push).
- [x] D-002 implement `pr` workflow (`stage + commit + push + create PR`).
- [x] D-003 implement `acho` and `acho pr` command flows.
- [x] D-004 implement `/pr --only` continuation modes with warning on unpushed branches.
- [x] D-005 integrate decision-store reuse and persistence for PR-only unpushed-branch behavior.
- [x] D-006 add unit tests for command workflow policy paths.
- [x] D-007 add deeper E2E command tests with real git branch/remote scenarios.

## Phase E Execution Log

- Rationale: make remote skills and maintenance workflow operational for sustained governance quality.
- Expected gain: predictable source lock behavior and recurring context health visibility.
- Potential impact: extra state outputs and new CLI command surfaces (`skill`, `maintenance`).

- [x] E-001 implement remote skills sync/list service with cache and lock updates.
- [x] E-002 add CLI commands for `skill list`, `skill sync` with offline mode.
- [x] E-003 implement maintenance local report generation and optional PR payload draft.
- [x] E-004 add integration and unit tests for skills and maintenance behavior.
- [x] E-005 enforce allowlist/pinning validation hard-fail logic in sync path.
- [x] E-006 wire approved maintenance reports to optional automated PR command flow.

## Phase F Execution Log

- Rationale: establish a single canonical product contract and adoption strategy for the content-first rebuild.
- Expected gain: removes ambiguity on scope, migration decisions, and rollout sequence.
- Potential impact: legacy implementation assumptions are superseded by contract-first guidance.

- [x] F-001 add `context/product/framework-contract.md` with finalized non-negotiable product contract.
- [x] F-002 add `context/product/framework-adoption-map.md` mapping legacy assets (keep/adapt/drop).
- [x] F-003 add `context/product/rebuild-rollout-charter.md` with milestones, validation plan, and readiness gates.
- [x] F-004 fix CLI `Literal` compatibility regression and restore JSON command behavior.
- [x] F-005 pin `click` compatibility for Typer 0.12 runtime stability.
- [x] F-006 run full local quality gate validation (`ruff`, `pytest`, `ty`, `pip-audit`).
- [ ] F-007 execute full implementation of charter workstreams W1-W5.
