# Framework Core Standards

## Update Metadata

- Rationale: define immutable governance baseline.
- Expected gain: consistent enforcement across installations.
- Potential impact: team overrides are constrained by non-negotiables.

## Purpose

Framework-owned baseline standards for every installed instance.

## Non-Negotiables

- Mandatory local enforcement through git hooks.
- Required security checks: `gitleaks`, `semgrep`, dependency vulnerability checks.
- No direct commits to `main` or `master`.
- Protected branches are blocked for direct push flows.
- Remote skills are content-only; no remote execution.

## Enforcement Rules

- All mandatory checks run locally before commit/push operations.
- Failing mandatory checks block the operation.
- Team or project layers may add stricter rules, but cannot weaken this file.

## Command Governance

- `/commit` and `/acho` push only current branch.
- `/pr --only` warns if branch is not pushed, proposes auto-push, and continues with user-selected mode if declined.

## Risk Acceptance

- Weakening attempts must produce warning + remediation suggestion.
- Auto-apply is never allowed.
- Explicit accepted risk must be recorded in machine-readable decision store and audit log.

## Update Contract

This file is framework-managed and can be updated by framework migrations.
