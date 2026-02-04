---
description: Runs the test suite and reports results with coverage
tools: [Bash, Read, Glob]
---

## Objective

Execute all tests and report results with coverage metrics.

## Process

1. Detect test framework from project files.
2. Run tests with coverage enabled:
   - .NET: `dotnet test --collect:"XPlat Code Coverage"`
   - TypeScript: `npm test -- --coverage`
   - Python: `pytest --cov --cov-report=term-missing`
3. Parse results: total tests, passed, failed, skipped.
4. Parse coverage: overall percentage, files below 80% threshold.
5. Report summary with actionable details for any failures.

## Success Criteria

- Test results parsed and reported accurately
- Coverage data included when available
- Failed test details include file, test name, and error message

## Constraints

- Do NOT modify tests or source code
- Do NOT skip or ignore failing tests
- Only run tests and report results
