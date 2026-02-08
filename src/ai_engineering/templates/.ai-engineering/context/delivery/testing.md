# Testing Strategy

## Update Metadata

- Rationale: make tests reflect mandatory enforcement and new command flows.
- Expected gain: earlier detection of governance regressions.
- Potential impact: test suites must include cross-OS and policy persistence cases.

## Scope

Testing covers policy correctness, command behavior, ownership safety, and cross-OS reliability.

## Required Test Layers

- unit tests for policy evaluation, standards layering, decision reuse.
- integration tests for installer/updater/hook wiring.
- E2E tests for `/commit`, `/pr`, `/acho` behaviors.
- security tests for mandatory checks and restricted actions.

## MVP Mandatory Checks in Test Pipelines

- `ruff` formatting and lint checks.
- `ty` type checks.
- `gitleaks` and `semgrep` scans.
- `pip-audit` for dependency vulnerabilities.

## Cross-OS Matrix

Must run on:

- Windows.
- macOS.
- Linux.

## Coverage and Quality Targets

- overall test coverage >= 80 percent.
- governance-critical modules targeted above baseline.
- no flaky tests in command and policy flows.

## Regression Targets

- `/pr --only` unpushed branch warning path and continuation modes.
- ownership-preserving updates.
- risk decision expiration and material-change re-prompt behavior.
