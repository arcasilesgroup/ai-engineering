# Checkpoint 15 review

## Goal

Each pull request runs one mutation campaign, Sonar reuses check coverage, and the 3-OS platforms matrix remains green.

## Acceptance

- One mutation campaign per PR.
- Sonar reuses the check run's coverage instead of running the suite again.
- The Ubuntu/macOS/Windows matrix remains unchanged and green.

## changed_files

- `.github/workflows/mutation.yml`
- `.github/workflows/check.yml`

## Verify

- `grep -qF "os: [ubuntu-latest, macos-latest, windows-latest]" .github/workflows/platforms.yml`

## Debate review — round 1

**Verdict:** PASS for workflow configuration. No findings; no blocker or major remains.

The PR mutation trigger has one campaign job; check runs the suite once and uploads only its LCOV file; Sonar waits for `tokens` and `check`, then downloads that run's artifact without rerunning tests. Both workflows use `contents: read`; artifact paths are scoped. `platforms.yml` is unchanged and retains the exact Ubuntu/macOS/Windows matrix.

**Gate 1:** C36 only greps the matrix string; it does not run actionlint. Not a correctness finding: `check.yml` runs actionlint over the workflow set and template, and a malformed check workflow cannot silently pass.

**CI evidence:** No matching CP15 CI log was found in the checkpoint history or for `feat/floating-core`; the matrix's green runtime status is therefore not independently confirmed.
