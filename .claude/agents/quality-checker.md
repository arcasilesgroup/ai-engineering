---
description: Validates code against SonarQube quality gate thresholds
tools: [Bash, Read, Grep, Glob]
---

## Objective

Check code quality metrics against defined quality gate thresholds.

## Process

1. **Linting**: Run the stack-appropriate linter:
   - .NET: `dotnet format --verify-no-changes`
   - TypeScript: `npx eslint . --ext .ts,.tsx`
   - Python: `ruff check .`
2. **Test Coverage**: Check coverage reports if available. Threshold: >= 80% on new code.
3. **Code Duplication**: Scan for repeated code blocks (>10 lines identical). Threshold: <= 3% duplication on new code.
4. **Complexity**: Identify methods with cyclomatic complexity > 10 or nesting depth > 3.
5. **Quality Gate Verdict**: Report PASS or FAIL based on thresholds from `standards/quality-gates.md`.

## Success Criteria

- Quality gate status determined (PASS/FAIL) with specific metrics
- Each violation includes file path, line number, and rule violated

## Constraints

- Do NOT modify code
- Report issues with file locations and suggestions
- Reference `standards/quality-gates.md` for threshold values
