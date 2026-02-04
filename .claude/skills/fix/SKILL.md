---
name: fix
description: Fix failing tests, lint errors, or build issues
---

## Context

Diagnoses and fixes failing tests, lint errors, or build issues. Reads the error output and applies targeted fixes.

## Inputs

$ARGUMENTS - Optional: "tests", "lint", "build", or specific error message. Defaults to detecting the issue.

## Steps

### 1. Identify the Problem

If $ARGUMENTS specifies the type:
- `tests` → Run the test suite and capture failures
- `lint` → Run the linter and capture errors
- `build` → Run the build and capture errors

If no argument, detect the most likely issue:
- Run build first (build errors block everything)
- Then run tests
- Then run linter

### 2. Analyze Errors

For each error:
- Read the error message and stack trace
- Identify the file and line number
- Read the surrounding code to understand context
- Check `learnings/*.md` for known patterns that might apply

### 3. Apply Fixes

Fix errors one at a time, starting with the most fundamental:

**Build errors:**
- Missing imports/usings
- Type mismatches
- Missing method implementations
- Dependency issues

**Test failures:**
- Incorrect assertions
- Missing mock setup
- Changed API contracts
- Stale test data

**Lint errors:**
- Formatting issues
- Naming convention violations
- Unused imports
- Style violations

### 4. Verify Fixes

After each fix:
- Re-run the specific failing command
- Confirm the error is resolved
- Check that no new errors were introduced

### 5. Report

    ## Fix Report

    **Issues found:** X
    **Issues fixed:** Y

    ### Fixes Applied
    1. **[file:line]** [What was wrong] → [What was fixed]
    2. ...

    ### Remaining Issues (if any)
    - [Issue that could not be auto-fixed and why]

## Verification

- All originally failing tests/lint/build now pass
- No new errors introduced by the fixes
- Fixes follow project standards
