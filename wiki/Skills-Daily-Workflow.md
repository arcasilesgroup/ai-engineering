# Daily Workflow Skills

> The core skills you'll use every day: commit, review, test, and PR.

## /commit-push

**Smart commit with secret scanning and automatic push.**

```
/commit-push
```

### What It Does

1. **Scans for secrets** — Runs gitleaks on staged files. Blocks if secrets found.
2. **Analyzes changes** — Reads `git diff` to understand what changed.
3. **Generates commit message** — Follows Conventional Commits format.
4. **Creates the commit** — Atomic, logically grouped.
5. **Pushes to remote** — Pushes to origin with tracking.

### Conventional Commits Types

| Type | When |
|------|------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks |
| `ci` | CI/CD changes |

### Example Output

```
feat(auth): add JWT token refresh endpoint

- Add RefreshToken endpoint to AuthController
- Implement token rotation in TokenService
- Add integration tests for refresh flow
```

---

## /commit-push-pr

**Full cycle: commit + push + create PR.**

```
/commit-push-pr
```

### What It Does

1. **Commits** — Same as `/commit-push` (with secret scanning)
2. **Pushes** — Pushes to remote branch
3. **Creates PR** — Opens a pull request with structured description

### Multi-Platform Support

Works with both GitHub and Azure DevOps:

| Platform | CLI | PR Command |
|----------|-----|------------|
| GitHub | `gh` | `gh pr create` |
| Azure DevOps | `az` | `az repos pr create` |

The skill auto-detects your platform from the git remote URL.

---

## /pr

**Create a structured pull request.**

```
/pr
```

### What It Does

1. **Analyzes changes** — Reviews all commits on the branch
2. **Generates description** — Creates structured PR description
3. **Creates PR** — Opens on GitHub or Azure DevOps

### PR Structure

```markdown
## Summary
- [What changed and why]

## Changes
- [List of significant changes]

## Testing
- [ ] Unit tests pass
- [ ] Manual testing done

## Checklist
- [ ] Code follows project standards
- [ ] Tests included
- [ ] No secrets committed
```

---

## /review

**Code review against standards.**

```
/review staged
/review src/services/
/review feature-branch
```

### What It Does

1. **Reads standards** — Loads relevant `standards/*.md`
2. **Reads learnings** — Checks `learnings/*.md` for known patterns
3. **Analyzes code** — Reviews against 6 dimensions
4. **Reports findings** — APPROVE or REQUEST CHANGES

### Review Dimensions

1. **Correctness** — Does it do what it should?
2. **Security** — OWASP Top 10 issues?
3. **Performance** — Obvious inefficiencies?
4. **Maintainability** — Clear, documented, testable?
5. **Standards** — Follows project conventions?
6. **Testing** — Adequate coverage?

### Example Output

```markdown
## Code Review: Staged Changes

### Summary
Adding user authentication endpoint. Implementation follows existing patterns.

**Verdict:** APPROVE

### Critical Issues (must fix)
(none)

### Suggestions (nice to have)
- [ ] Consider adding rate limiting to prevent brute force
- [ ] Token expiry could be configurable via settings
```

---

## /test

**Generate and run tests.**

```
/test src/services/UserService.cs
/test run
/test coverage
```

### What It Does

1. **Detects framework** — NUnit, Vitest, pytest
2. **Reads the code** — Understands public API
3. **Generates tests** — Happy path + error paths
4. **Runs tests** — Reports results

### Test Generation Principles

- Tests edge cases and error conditions
- Uses existing test patterns from the codebase
- Names tests clearly: `MethodName_Scenario_ExpectedResult`
- Follows AAA pattern (Arrange, Act, Assert)

---

## /validate

**Validate framework installation.**

```
/validate
```

### What It Does

1. **Checks files** — Verifies all required files exist
2. **Validates config** — Ensures settings.json is valid
3. **Detects platform** — GitHub or Azure DevOps
4. **Checks tools** — Verifies gitleaks, CLI tools, and pre-push hook
5. **Reports status** — Shows what's working

### Example Output

```
## Framework Validation Report

**Status:** VALID
**Version:** 2.0.0

### Files
- [x] CLAUDE.md
- [x] .claude/settings.json
- [x] Skills: 21 found
- [x] Agents: 6 found
- [x] Hooks: 4 found (4 executable)
- [x] Standards: 10 found

### Platform
- [x] Platform: GitHub
- [x] CLI: gh installed
- [x] Auth: Authenticated

### Tools
- [x] gitleaks: installed
- [x] Pre-push hook: installed
- [x] Stack tools: configured

### Warnings
(none)

Framework is correctly installed.
```

---

## /fix

**Fix failing tests, lint errors, or build issues.**

```
/fix tests
/fix build
/fix lint
```

### What It Does

1. **Runs the failing command** — Captures error output
2. **Identifies root cause** — Analyzes the error
3. **Applies targeted fixes** — Makes minimal changes
4. **Re-runs to verify** — Confirms the fix worked

### Example

```
/fix tests
```

Output:
```
Found 2 failing tests in UserServiceTests.cs:
- GetUser_WithInvalidId_ThrowsException: Expected exception not thrown
- CreateUser_WithDuplicateEmail_ReturnsError: Result.IsError was false

Fixing...

1. GetUser_WithInvalidId: Added validation to throw ArgumentException
2. CreateUser_WithDuplicateEmail: Fixed email uniqueness check in provider

Re-running tests...
✓ All tests pass (47 passed, 0 failed)
```

---
**See also:** [Code Quality Skills](Skills-Code-Quality) | [Skills Overview](Skills-Overview)
