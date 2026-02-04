---
name: quality-gate
description: Run quality gate checks (linting, coverage, duplication, dependencies)
disable-model-invocation: true
---

## Context

Runs the full quality gate validation against the current codebase or changed files. Checks code quality metrics against thresholds defined in `standards/quality-gates.md`.

## Inputs

$ARGUMENTS - Optional: "changed" for only changed files, or specific file paths. Defaults to full project.

## Steps

### 1. Read Quality Gate Thresholds

Read `standards/quality-gates.md` for current threshold values:
- Coverage on new code: >= 80%
- Duplicated lines on new code: <= 3%
- Maintainability rating: A
- Reliability rating: A
- Security rating: A
- Security hotspots reviewed: 100%

### 2. Run Linter

Execute stack-appropriate linter:
- .NET: `dotnet format --verify-no-changes`
- TypeScript: `npx eslint . --ext .ts,.tsx`
- Python: `ruff check .`

### 3. Check Test Coverage

Run tests with coverage:
- .NET: `dotnet test --collect:"XPlat Code Coverage"`
- TypeScript: `npm test -- --coverage`
- Python: `pytest --cov --cov-report=term-missing`

### 4. Dependency Vulnerability Scan

Run dependency audit:
- .NET: `dotnet list package --vulnerable`
- TypeScript: `npm audit`
- Python: `pip audit`

### 5. Code Duplication Check

Scan for duplicated code blocks (> 10 identical lines).

### 6. Report

    ## Quality Gate Report

    **Verdict:** PASS | FAIL

    ### Metrics
    | Metric | Threshold | Actual | Status |
    |--------|-----------|--------|--------|
    | Coverage (new code) | >= 80% | X% | PASS/FAIL |
    | Duplication (new code) | <= 3% | X% | PASS/FAIL |
    | Linter issues | 0 | X | PASS/FAIL |
    | Critical vulnerabilities | 0 | X | PASS/FAIL |
    | High vulnerabilities | 0 | X | PASS/FAIL |

    ### Issues Found
    1. **[file:line]** [Issue description]
    2. ...

    ### Dependency Vulnerabilities
    - [package@version] - [severity] - [description]

## Verification

- All quality gate checks executed
- Thresholds match `standards/quality-gates.md`
- Report includes actionable details for failures
