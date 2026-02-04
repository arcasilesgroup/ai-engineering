---
description: Perform a structured code review against project standards
---

## Context

Performs a comprehensive code review focusing on correctness, security, performance, and standards compliance. Uses the project's standards and learnings as the review baseline.

## Inputs

$ARGUMENTS - File paths, PR number, or "staged" for staged changes

## Steps

### 1. Gather Context

- Read CLAUDE.md to understand project critical rules
- Identify the stack being reviewed (.cs = dotnet, .ts/.tsx = typescript, .py = python, .tf = terraform)
- Read the relevant `standards/*.md` file for the stack
- Read the relevant `learnings/*.md` file for known patterns and pitfalls
- Identify the files to review from $ARGUMENTS

### 2. Analyze Each File

For each file, check against these dimensions:

**Correctness:**
- Logic errors, edge cases, null handling
- Result pattern compliance (IsError check before Value access)
- Error types registered in error mapping

**Security (reference standards/security.md):**
- No hardcoded secrets or credentials
- Input validation at system boundaries
- Authentication/authorization on endpoints
- No data exposure in logs or responses
- SQL injection, XSS, CSRF protection

**Performance:**
- N+1 query patterns
- Multiple enumeration of IEnumerable
- Missing cancellation token propagation
- Unnecessary allocations

**Standards Compliance:**
- Naming conventions match the stack standard
- Code structure follows project patterns
- Explicit types (no ambiguous `var` in .NET)
- Async suffix on async methods
- Guard clauses / early returns (not deep nesting)

**Testing:**
- Tests exist for new/changed code
- Test naming follows `MethodName_Scenario_ExpectedResult`
- Assertions use `EnterMultipleScope()` for grouped checks
- Dynamic dates (not hardcoded)

**Maintainability:**
- Single responsibility
- Comments explain "why" not "what"
- No dead code
- No TODO without issue reference

### 3. Generate Review Report

Output in this format:

```markdown
## Code Review: [Files/PR]

### Summary
[Brief assessment: 2-3 sentences]

**Verdict:** APPROVE | REQUEST CHANGES | REJECT

### Critical Issues (must fix)
- [ ] **[file:line]** [Description] - [Fix suggestion]

### High Priority
- [ ] **[file:line]** [Description]

### Suggestions (nice to have)
- [ ] **[file:line]** [Description]

### Positive Observations
- [What was done well]
```

## Verification

- All critical rules from CLAUDE.md were checked
- No false positives from Result pattern checks
- Review references specific lines and files
- Fix suggestions are actionable
