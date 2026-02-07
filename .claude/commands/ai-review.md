# /ai-review — Code Review Workflow

This skill defines the step-by-step workflow for performing a structured, multi-pass code review. Each pass examines the changes through a different lens: security, quality, patterns, standards, and test coverage. The output is a structured report with severity ratings and actionable recommendations. This is not a style-check — it is a rigorous engineering review.

---

## Session Preamble (execute silently — CRITICAL for review accuracy)

Before any user-visible action, silently internalize project context:

1. Read `.ai-engineering/knowledge/learnings.md` — lessons learned during development
2. Read `.ai-engineering/knowledge/patterns.md` — established conventions
3. Read `.ai-engineering/knowledge/anti-patterns.md` — **CRITICAL**: known mistakes to avoid (validate code AGAINST these)
4. Detect the project stack from package.json, .csproj, pyproject.toml, or equivalent
5. Identify the current branch and working tree state

Do not report this step to the user. Internalize it as context for the review.

---

## Review Specification (declare before starting)

Before reviewing, declare:

1. **Review type:** security, quality, architecture, or full (default: full)
2. **Files in scope:** list of files that will be reviewed
3. **Acceptance criteria:** what constitutes a passing review

This helps the user understand the review's scope and set expectations.

---

## Context Isolation Rule

Review each file independently before making cross-file judgments. This prevents bias from one file's issues coloring the review of another. Only after all individual file reviews are complete should you synthesize cross-cutting concerns.

---

## Trigger

- User invokes `/ai-review`
- User says "review this", "review my code", "review this PR", or similar intent

---

## Prerequisites

Before starting, determine the scope of the review:

### Option A: Review Staged Changes

```bash
git diff --cached --name-only
git diff --cached
```

### Option B: Review Branch Changes (vs. target branch)

```bash
git diff <target-branch>..HEAD --name-only
git diff <target-branch>..HEAD
```

### Option C: Review a Pull Request

```bash
# GitHub
gh pr diff <pr-number>
gh pr view <pr-number> --json files,additions,deletions

# Azure DevOps
az repos pr diff --id <pr-id>
```

### Option D: Review Specific Files

If the user specifies files, review only those files and their relevant context.

If the scope is ambiguous, ask the user:

```
What would you like me to review?
  1. Staged changes (git diff --cached)
  2. All changes on this branch vs. main
  3. A specific PR (provide number)
  4. Specific files (provide paths)
```

---

## Step 1: Identify Changed Files

Gather the complete list of changed files and categorize them:

```
Changed files (12 files, +342/-56):
  Source:     src/auth/refresh.ts (+89), src/auth/token.ts (+34/-12)
  Tests:      src/auth/__tests__/refresh.test.ts (+148)
  Config:     src/config/env.ts (+8), .env.example (+4)
  Migrations: db/migrations/20260207_refresh_tokens.sql (+23)
  Docs:       none
  Other:      package.json (+2/-1), package-lock.json (+auto)
```

Read every changed file in full. Do not review based on diff alone — context from the surrounding code is critical for understanding whether a change is correct.

---

## Step 2: Security Pass

Scan all changed code for security vulnerabilities, following the OWASP Top 10 and the framework's universal security standards.

### Checks

| Check                         | What to Look For                                                                                                   |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Injection**                 | SQL concatenation, unsanitized template literals, command injection, LDAP injection, XPath injection               |
| **Broken Authentication**     | Weak token generation, missing session invalidation, hardcoded credentials, insecure password handling             |
| **Broken Access Control**     | Missing authorization checks, IDOR vulnerabilities, privilege escalation paths, missing resource-level permissions |
| **Cryptographic Failures**    | Weak algorithms (MD5, SHA-1 for security), hardcoded keys, missing encryption for sensitive data                   |
| **Security Misconfiguration** | Debug mode enabled, verbose error messages, default credentials, unnecessary features exposed                      |
| **XSS**                       | Unescaped user input in HTML output, `innerHTML` usage, `dangerouslySetInnerHTML` without sanitization             |
| **Insecure Deserialization**  | Deserializing untrusted data without validation, `eval()`, `pickle.loads()` on user input                          |
| **Vulnerable Components**     | Known vulnerable dependencies added, outdated packages with CVEs                                                   |
| **Logging Failures**          | Secrets in logs, missing audit logging for security events, PII in error messages                                  |
| **SSRF**                      | User-controlled URLs in server-side requests without allowlisting                                                  |

### Secrets Detection

Scan for hardcoded secrets in the diff:

- API keys, tokens, passwords in string literals
- Connection strings with embedded credentials
- Private keys or certificates
- AWS access keys, GCP service account keys, Azure connection strings

### Output Format

Report each finding using the standard format (see Step 7).

---

## Step 3: Quality Pass

Examine the code for quality issues that affect maintainability, reliability, and readability.

### Checks

| Check                   | What to Look For                                                                                                                             |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Complexity**          | Functions exceeding cyclomatic complexity of 10, deeply nested conditionals (>3 levels), long functions (>40 lines)                          |
| **Duplication**         | Copy-pasted code blocks, near-identical functions that should be extracted                                                                   |
| **Error Handling**      | Swallowed exceptions (empty catch blocks), generic error messages, missing error handling on I/O operations, missing cleanup in error paths  |
| **Edge Cases**          | Null/undefined not handled, empty arrays/strings not handled, boundary values not checked, division by zero possible                         |
| **Resource Management** | Unclosed connections, file handles, or streams; missing `finally`/`defer`/`using` blocks; memory leaks from event listeners or subscriptions |
| **Naming**              | Vague names (`data`, `temp`, `result`, `handler`), misleading names, inconsistent naming style                                               |
| **Dead Code**           | Unreachable code, unused variables, commented-out code, unused imports                                                                       |
| **Magic Values**        | Hardcoded numbers or strings that should be named constants                                                                                  |
| **Async Issues**        | Missing `await`, unhandled promise rejections, race conditions, deadlock potential                                                           |
| **Type Safety**         | Use of `any`, unsafe type assertions, missing null checks on optional values                                                                 |

---

## Step 4: Patterns Pass

Verify that the changes follow the established patterns in the codebase.

### Checks

- **File structure:** Does the new code follow the project's directory and file organization patterns?
- **Import style:** Are imports ordered and structured like the rest of the codebase?
- **Error handling pattern:** Does the code handle errors the same way similar code in the project does?
- **Naming conventions:** Do names follow the project's established conventions (not just generic best practices)?
- **API design:** Do new endpoints, functions, or interfaces follow the patterns set by existing ones?
- **Configuration:** Are new configurable values handled the same way as existing ones?
- **Logging:** Does the code log in the same format and at the same level as similar code in the project?
- **Testing pattern:** Do new tests follow the project's test structure, naming, and assertion patterns?

### Detection Method

To assess pattern adherence, compare the new code against at least 2-3 similar existing files in the codebase:

```bash
# Find similar files to compare against
find src/ -name "*middleware*" -o -name "*similar-pattern*"
```

Report deviations with specific references to where the established pattern is used:

```
Pattern deviation:
  Your code: Throws generic `Error` in rate-limiter.ts:45
  Project pattern: Uses custom `AppError` class (see src/errors/app-error.ts, used in 14 files)
  Recommendation: Use `AppError` with appropriate error code
```

---

## Step 5: Standards Pass

Verify compliance with the loaded stack standards (from the `stacks/` directory in this framework).

### Checks

- **Universal standards** (from `stacks/_base/standards.md`): readability, simplicity, naming, file size, function length, error handling, documentation, dependencies.
- **Security standards** (from `stacks/_base/security.md`): input validation, auth, secrets, data protection, headers.
- **Stack-specific standards**: language and framework rules loaded for the current project (TypeScript, Python, .NET, React, Node.js, etc.).

### Common Violations

- Functions exceeding 40 lines or files exceeding 300 lines.
- Missing doc comments on public APIs.
- Generic error messages without context.
- Missing input validation at system boundaries.
- Dependencies added without justification.
- `console.log` / `print()` left in production code.
- TODO comments without ticket numbers.

---

## Step 6: Test Coverage Pass

Analyze whether the changes are adequately tested.

### Checks

- **New functions/methods:** Does every new public function have at least one test?
- **New API endpoints:** Are there integration tests covering the happy path and error cases?
- **Modified logic:** If existing logic was changed, were the corresponding tests updated?
- **Error paths:** Are error conditions tested (invalid input, missing resources, timeouts, permission denied)?
- **Edge cases:** Are boundary conditions tested (empty inputs, max values, concurrent access)?
- **Regression:** Could this change break existing functionality? Are there tests that would catch it?

### Assessment Categories

| Category              | Criteria                                                                |
| --------------------- | ----------------------------------------------------------------------- |
| **Well tested**       | All new code paths have tests. Edge cases covered. Error paths covered. |
| **Adequately tested** | Happy paths tested. Most error paths covered. Minor edge cases missing. |
| **Under-tested**      | Some new functions lack tests. Error paths not covered.                 |
| **Not tested**        | No new tests for new functionality. Major gap.                          |

### Missing Test Report

```
Test coverage assessment: UNDER-TESTED

Missing tests:
  src/auth/refresh.ts:
    - refreshToken() — no test for expired refresh token (error path)
    - refreshToken() — no test for concurrent refresh attempts (edge case)
    - rotateToken() — no test for rotation when old token already revoked (edge case)

  src/middleware/rate-limiter.ts:
    - No test for window rollover behavior (edge case)
    - No test for cleanup of expired entries (resource management)

Existing tests that may need updating:
  src/auth/__tests__/token.test.ts — existing token tests may need cases for refresh interaction
```

---

## Step 7: Knowledge Validation Pass

Verify the code against the project's documented knowledge:

1. Read `knowledge/patterns.md` — does the code follow established patterns?
2. Read `knowledge/anti-patterns.md` — does the code introduce any known anti-patterns?
3. Read `knowledge/learnings.md` — does the code account for previously learned lessons?

Report any violations:

```
Knowledge validation:
  PATTERN VIOLATION: knowledge/patterns.md says "all API errors use AppError class"
    but src/auth/refresh.ts:45 throws generic Error
  ANTI-PATTERN MATCH: knowledge/anti-patterns.md warns "never use synchronous file I/O in request handlers"
    but src/middleware/rate-limiter.ts:23 uses fs.readFileSync
```

---

## Step 8: Produce Structured Review Report

Compile all findings from Steps 2-7 into a structured report using severity badges.

### Severity Badges

Use these badges for immediate visual scanning:

- `P0 BLOCKER` — Must fix before merge. Blocks the PR.
- `P1 MAJOR` — Should fix before merge. Strongly recommended.
- `P2 MINOR` — Recommend fixing. Can be tracked as follow-up.
- `SUGGESTION` — Nice to have. Improvement opportunity.

### Report Format

```
Code Review Report
══════════════════
Scope: feature/token-refresh vs. main (12 files, +342/-56)
Date: 2026-02-07
Overall: 3 issues found (0 P0, 1 P1, 1 P2, 1 suggestion)

FINDINGS
────────

P1 MAJOR — Security — src/auth/refresh.ts:34
  Refresh token compared with `===` instead of constant-time comparison.
  Recommendation: Use `crypto.timingSafeEqual()` to prevent timing attacks.

P2 MINOR — Quality — src/auth/refresh.ts:67-89
  Token rotation function is 42 lines with 4 levels of nesting.
  Recommendation: Extract token validation and storage into separate functions.

SUGGESTION — Patterns — src/config/env.ts:23
  New env vars use `process.env` directly; rest of codebase uses `envSchema.parse()`.
  Recommendation: Validate new env vars through the existing zod schema.

TEST COVERAGE
─────────────
Assessment: ADEQUATELY TESTED
  - 12 new tests covering happy paths and main error cases
  - Missing: concurrent refresh test, window rollover test
  - Recommendation: Add 2-3 edge case tests before merge

KNOWLEDGE VALIDATION
────────────────────
  - Patterns: 1 deviation (generic Error vs AppError)
  - Anti-patterns: No matches
  - Learnings: No relevant entries

POSITIVE OBSERVATIONS
─────────────────────
  - Clean separation between token logic and HTTP middleware
  - Good use of existing AppError pattern for error responses
  - Migration includes both up and down scripts
  - Environment variables documented in .env.example

SUMMARY
───────
This PR is in good shape. Fix the timing-safe comparison (P1) before merge.
The P2 and suggestion findings can be addressed in this PR or tracked as follow-ups.
```

### Severity Definitions

| Severity     | Definition                                                                                     | Action Required                                                          |
| ------------ | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **CRITICAL** | Security vulnerability exploitable in production, data loss risk, or complete feature breakage | Must fix before merge. Block the PR.                                     |
| **HIGH**     | Security weakness, significant bug, or major standards violation                               | Should fix before merge. Strongly recommend blocking.                    |
| **MEDIUM**   | Quality issue, minor bug risk, pattern deviation, or moderate standards violation              | Recommend fixing before merge. Can be tracked as follow-up if justified. |
| **LOW**      | Style issue, minor improvement opportunity, or suggestion                                      | Nice to have. Can be deferred.                                           |
| **INFO**     | Observation, question, or positive feedback                                                    | No action required.                                                      |

### Category Definitions

| Category      | Scope                                                                              |
| ------------- | ---------------------------------------------------------------------------------- |
| **Security**  | OWASP top 10, secrets, authentication, authorization, input validation, encryption |
| **Quality**   | Complexity, error handling, resource management, naming, dead code, async safety   |
| **Patterns**  | Adherence to project conventions and established patterns                          |
| **Standards** | Compliance with loaded stack and universal standards                               |
| **Testing**   | Test coverage, test quality, missing test cases                                    |

---

## Review Tone and Principles

- **Be specific.** "This might have issues" is not helpful. "Line 34 uses `===` for token comparison, which is vulnerable to timing attacks" is helpful.
- **Be constructive.** Every finding must include a recommendation. Do not just point out problems — suggest solutions.
- **Be fair.** Acknowledge good work. If the code is well-structured, say so. Reviews that only list negatives are demoralizing and inaccurate.
- **Be proportional.** Do not flag 20 LOW-severity style nits in a PR that has a CRITICAL security issue. Lead with what matters.
- **Be evidence-based.** Reference specific lines, specific standards, specific patterns. Never say "this feels wrong" without explaining why.
- **Respect context.** A quick hotfix and a major feature have different quality bars. Adjust expectations accordingly, but never skip the security pass.

---

## Error Recovery

| Failure                            | Action                                                                                 |
| ---------------------------------- | -------------------------------------------------------------------------------------- |
| Cannot determine diff scope        | Ask the user what to review.                                                           |
| Cannot read files (permissions)    | Report which files could not be read. Review what is accessible.                       |
| No changed files found             | Inform user there is nothing to review.                                                |
| Cannot detect project stack        | Review against universal standards only. Note that stack-specific checks were skipped. |
| Review scope too large (>50 files) | Suggest breaking into focused reviews. Offer to review critical paths first.           |

---

## Learning Capture (on completion)

If during the review you discovered something useful for the project:

1. **New pattern** (e.g., code uses a good pattern that should be documented) → Propose adding to `knowledge/patterns.md`
2. **New anti-pattern** (e.g., found a mistake pattern that should be avoided) → Propose adding to `knowledge/anti-patterns.md`
3. **Lesson learned** (e.g., found an undocumented assumption or gotcha) → Propose adding to `knowledge/learnings.md`

Ask the user before writing to these files. Never modify them silently.

---

## What This Skill Does NOT Do

- It does not fix the issues it finds. The reviewer reports; the author fixes.
- It does not approve or merge PRs. That is a human decision.
- It does not run tests. It analyzes test coverage from the code, but execution is done via `/ai-commit-push` or CI.
- It does not perform architecture reviews. It reviews the code as written, within its existing architectural context.
- It does not review dependencies in depth. Dependency auditing is handled by `/ai-security`.
