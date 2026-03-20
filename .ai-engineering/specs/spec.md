---
id: "060"
title: "CI & Install Smoke Audit — Eliminate False Positives"
status: draft
created: 2026-03-20
branch: feat/ci-smoke-audit-fixes
refs:
  features: []
  tasks: []
  issues: []
---

# Spec 060: CI & Install Smoke Audit — Eliminate False Positives

## Problem

An audit of the last 5 CI runs and 5 Install Smoke runs on GitHub Actions revealed 13 issues where workflows report green without actually validating correctness. "Green" must mean "validated and passed", not "skipped or ignored". Currently:

- Dependabot PRs skip ALL code quality gates and pass CI green.
- Snyk reports "success" without running any scans (vacuous success).
- Gate Trailer verification only checks the HEAD commit, not all PR commits.
- SonarCloud accepts zero coverage reports without failing.
- Semgrep silently skips 43% of files.
- `ai-eng doctor` passes with 8 warnings (6 missing tools) and exit code 0.
- `ai-eng install` always exits 0, even on errors.
- `ai-eng version` output is never validated.
- Install Smoke runs only on Ubuntu, not cross-platform.

## Solution

Fix all 13 findings across three groups: CI workflow YAML, Install Smoke workflow + CLI code, and cross-platform matrix. Every green check must prove it ran and validated something.

## Scope

### In Scope

#### Group 1: CI Workflow Fixes (ci.yml)

**C1 — Paths-filter must include workflow files (CRITICAL)**
Add `.github/workflows/**` and `**/*.yml` to the `code` paths-filter. Dependabot PRs that change workflows will trigger the full CI pipeline (lint, tests, type check, security, etc.).

**C2 — Snyk job must report `skipped` when token is absent (CRITICAL)**
Move the token check from step-level `if` to job-level `if`. When `SNYK_TOKEN` is empty, the job conclusion will be `skipped` (not `success`). The `ci-result` gate already handles `skipped` correctly in the `optional` category.

**C3 — Gate Trailers must validate ALL PR commits (HIGH)**
Change `fetch-depth: 1` to `fetch-depth: 0`. Replace `git log -1` with a loop that iterates every non-merge commit in the PR range (`git log --no-merges --format=%H base..head`). Every non-merge commit must have the `Ai-Eng-Gate: passed` trailer. Merge commits are excluded (`--no-merges`) because they are not created by the developer's pre-commit hook.

**C4 — SonarCloud must fail when zero coverage reports exist (HIGH)**
Add `exit 1` to the "Verify coverage reports" step when `count == 0` and code was changed. SonarCloud must not run with zero coverage data.

**C5 — Semgrep skip count must be bounded (MEDIUM)**
Modify the semgrep step to use JSON output (`semgrep --config .semgrep.yml --json .`), then add a follow-up step that parses `.paths.skipped | length` from the JSON and fails if the skip ratio exceeds 50% of total targets. This prevents implicit exclusions (built-in rules, binary files, lockfiles) from silently exempting too much of the codebase. Note: there is no `.semgrepignore` file — semgrep skips files based on its built-in rules.

#### Group 2: Install Smoke Workflow + CLI Code

**S1 — Doctor exit codes must distinguish ok/fail/warn (CRITICAL)**
Modify `doctor_cmd` in CLI to use three exit codes:
- Exit 0: all checks ok (no fails, no warns)
- Exit 1: at least one check failed
- Exit 2: no fails, but at least one warning

Add a `has_warnings` property to `DoctorReport` in `doctor/models.py` (True if any check has status `WARN` and none have `FAIL`). The `passed` property is not changed (it stays boolean for the API). The exit code logic in `doctor_cmd` uses `has_warnings` to decide between exit 0 and exit 2.

**S2 — Smoke must validate `ai-eng version` output (HIGH)**
The workflow must capture `ai-eng version` output and assert it matches a pattern (e.g., `ai-engineering X.Y.Z`). If the output is empty, "unknown", or doesn't match, the step fails.

**S3 — Install must support `--non-interactive` flag (HIGH)**
Add `--non-interactive` flag to `install_cmd`. When set, all 5 interactive prompts use defaults without waiting for input:
1. `_resolve_vcs_provider()` — defaults to `github` (already handled by `is_json_mode()`)
2. `_prompt_external_cicd_docs()` — defaults to empty (already handled by `is_json_mode()`)
3. `_resolve_ai_providers()` — defaults to `claude` (already handled by `is_json_mode()`)
4. `_offer_platform_onboarding()` SonarCloud confirm — defaults to No (NOT currently handled, must add check)
5. `_offer_platform_onboarding()` credentials confirm — defaults to No (NOT currently handled, must add check)

Implementation: set an env var or context flag that `--non-interactive` activates, check it in all 5 prompt sites. The workflow passes `--non-interactive` explicitly.

**S4 — Smoke must parse and assert doctor JSON output (HIGH)**
The workflow must pipe `ai-eng doctor --json` through validation:
- Parse JSON (fail if invalid)
- Assert no checks have `status: "fail"`
- Log warning count for visibility
- Use the exit code from S1 to gate the step (exit 1 = fail the smoke, exit 2 = acceptable in smoke context)

**S5 — Install must exit 1 on errors (HIGH)**
Verify that `_cli_error_boundary` in `cli_factory.py` covers install failure modes. It already catches `FileNotFoundError`, `NotADirectoryError`, and `PermissionError` (exit 1). Add any missing exception types that represent genuine failures (e.g., `yaml.YAMLError` from manifest writes, `shutil.Error` from template copies). The `contextlib.suppress(FileNotFoundError)` in `service.py` for hook installation in non-git repos is correct and must NOT be changed.

**S6 — Smoke must configure `init.defaultBranch main` (MEDIUM)**
Add `git config --global init.defaultBranch main` before `git init smoke-target`. This ensures the smoke repo uses `main`, matching the project convention, and exercises the branch-policy doctor check.

#### Group 3: Cross-Platform Matrix

**S7 — Install Smoke must run on ubuntu + windows + macos (MEDIUM)**
Add a matrix strategy to install-smoke.yml matching the CI framework-smoke pattern:
```yaml
strategy:
  fail-fast: false
  matrix:
    include:
      - { os: ubuntu-latest }
      - { os: windows-latest }
      - { os: macos-latest }
```
Adjust shell and path handling for Windows compatibility.

### Out of Scope

- LOW findings (C7, S8, S9) — descoped by decision.
- Changes to the CI Result gate logic beyond what C2 requires.
- Snyk `pull_request_target` for Dependabot secret access.
- Adding new doctor checks beyond exit code changes.
- Changes to the Release workflow.
- Changes to non-CI workflows (ai-eng-pr-review, maintenance, etc.).

## Files

### Group 1: CI Workflow

1. `.github/workflows/ci.yml` — paths-filter, Snyk job-level if, gate trailers fetch-depth + loop, SonarCloud verification exit, semgrep skip threshold

### Group 2: Install Smoke + CLI

2. `.github/workflows/install-smoke.yml` — version validation, `--non-interactive`, doctor JSON parsing, git config, cross-platform matrix
3. `src/ai_engineering/cli_commands/core.py` — doctor exit codes (0/1/2), install `--non-interactive` flag, `_offer_platform_onboarding` non-interactive check
4. `src/ai_engineering/doctor/models.py` — add `has_warnings` property to `DoctorReport`
5. `src/ai_engineering/cli_factory.py` — verify/extend `_cli_error_boundary` exception coverage for install errors

## Acceptance Criteria

### Group 1: CI

- [ ] Paths-filter `code` includes `.github/workflows/**` and `**/*.yml`.
- [ ] Snyk job has job-level `if` that skips entirely when token is absent; step-level token checks removed.
- [ ] Gate Trailers uses `fetch-depth: 0` and iterates all commits in PR range.
- [ ] Gate Trailers fails if ANY non-merge commit in the range is missing the trailer (merge commits excluded via `--no-merges`).
- [ ] SonarCloud "Verify coverage reports" exits 1 when count is 0 and code was changed.
- [ ] Semgrep step followed by skip-ratio check that fails if >50% of targets are skipped.

### Group 2: Install Smoke + CLI

- [ ] `ai-eng doctor` exits 0 (all ok), 1 (any fail), or 2 (warns only).
- [ ] `ai-eng version` output is captured and asserted against pattern `ai-engineering \d+\.\d+\.\d+`.
- [ ] `ai-eng install --non-interactive` runs without prompts, uses defaults.
- [ ] `ai-eng install` exits 1 on template/write/path errors.
- [ ] Smoke workflow parses doctor JSON, asserts no `"status": "fail"` checks.
- [ ] Smoke workflow sets `git config --global init.defaultBranch main`.

### Group 3: Cross-Platform

- [ ] Install Smoke runs on ubuntu-latest, windows-latest, macos-latest.
- [ ] All 3 OS variants pass green.

## Behavioral Negatives (Must NOT)

- Must NOT weaken any existing quality gate threshold.
- Must NOT change the `DoctorReport.passed` property semantics (it stays boolean, fail-only).
- Must NOT add suppression comments to bypass linting or analysis.
- Must NOT remove any existing CI job or step.
- Must NOT change Snyk from optional to required.

## Assumptions

- ASSUMPTION: For fork PRs, `secrets.SNYK_TOKEN` evaluates to empty string, causing the Snyk job to skip — which is the desired behavior. For same-repo PRs and push events, the token is available and the job runs. The `ci-result` gate's optional category handles `skipped` correctly (only fails on `failure`).
- ASSUMPTION: `git log --no-merges` with range `base..head` correctly enumerates all developer-authored commits in a PR, excluding merge commits created by GitHub or manual branch merges.
- ASSUMPTION: The 50% semgrep skip threshold is reasonable for the current codebase composition (43% skipped today = near the limit).
- ASSUMPTION: `typer.Exit(code=2)` produces `SystemExit(2)`. GitHub Actions treats any non-zero exit as failure. The smoke workflow must explicitly accept exit code 2 (e.g., `|| [ $? -eq 2 ]`).

## Risks

- **C1 paths-filter broadening may cause unnecessary CI runs**: YAML-only changes (docs, configs) would trigger Python tests. Mitigated: the existing `test-config` filter already handles this pattern; tests would run but pass quickly if no Python changed.
- **C3 all-commits check may block legitimate workflows**: Developers who cherry-pick or rebase may lose trailers. Mitigated: the pre-commit hook adds the trailer automatically; only bypassed commits (`--no-verify`) would fail.
- **S1 exit code 2 may confuse existing scripts**: Any script checking `$? -ne 0` would treat warnings as errors. Mitigated: only the smoke workflow and CLI consume this; documented in `--help`.
- **S7 cross-platform may surface new failures**: Windows path handling or shell differences could cause spurious failures. Mitigated: use `shell: bash` on all platforms (GitHub Actions provides Git Bash on Windows).

## Dependencies

- `src/ai_engineering/cli_commands/core.py` must have `doctor_cmd` and `install_cmd` functions.
- `src/ai_engineering/doctor/models.py` must have `DoctorReport` and `CheckStatus`.
- `src/ai_engineering/cli_factory.py` must have `_cli_error_boundary` wrapping CLI commands.
- `.github/workflows/ci.yml` must match the current structure (13 jobs with ci-result gate).
- Tests must exist for doctor and install CLI commands to validate exit code changes.
