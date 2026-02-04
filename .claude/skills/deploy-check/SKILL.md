---
name: deploy-check
description: Pre-deployment verification checklist
disable-model-invocation: true
---

## Context

Runs a comprehensive pre-deployment checklist to verify the code is ready for deployment. Checks build, tests, security, quality gates, and configuration.

## Inputs

$ARGUMENTS - Optional: environment name (dev, staging, production)

## Steps

### 1. Build Verification

- Run build for all detected stacks.
- Verify no compilation errors or warnings.

### 2. Test Verification

- Run full test suite.
- Verify all tests pass.
- Check coverage meets threshold (>= 80%).

### 3. Security Checks

- Run `gitleaks detect --source . --no-git` for secret scanning.
- Run dependency audit (`npm audit`, `dotnet list --vulnerable`, `pip audit`).
- Verify no critical or high vulnerabilities.

### 4. Quality Gate

- Run linter and verify no violations.
- Check for TODO/FIXME/HACK comments without issue references.
- Verify no debug/console.log statements in production code.

### 5. Configuration Check

- Verify no hardcoded environment-specific values.
- Check that all `{{PLACEHOLDER}}` values are replaced.
- Verify environment variables are documented.

### 6. Git Status

- Verify all changes are committed.
- Verify branch is up to date with base branch.
- Check for merge conflicts.

### 7. Report

    ## Deploy Check: {environment}

    **Verdict:** READY | NOT READY

    ### Checklist
    - [x] Build passes
    - [x] All tests pass (X passed, Y failed)
    - [x] Coverage >= 80% (actual: Z%)
    - [x] No secrets detected
    - [x] No critical dependency vulnerabilities
    - [x] Linter clean
    - [x] No debug statements
    - [x] Configuration valid
    - [x] Git state clean

    ### Blockers (if any)
    - [Issue preventing deployment]

## Verification

- All checks executed
- No false passes on security checks
- Report is accurate and actionable
