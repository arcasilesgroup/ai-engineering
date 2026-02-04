# Module 2: First Commands

## Overview

Learn the five core commands that form your daily development inner loop.

---

## Exercise 1: Make a Code Change

Make a small change to your project — add a comment, create a function, or fix a typo. This gives us something to commit.

---

## Exercise 2: Review Your Code (`/review`)

Before committing, review your own changes:

```
/review staged
```

Claude will analyze your staged changes against the project's standards and produce a report:

```markdown
## Code Review: Staged Changes

### Summary
[Assessment of the changes]

**Verdict:** APPROVE | REQUEST CHANGES

### Critical Issues (must fix)
- [ ] ...

### Suggestions (nice to have)
- [ ] ...
```

**What's happening under the hood:**
1. Claude reads `CLAUDE.md` for critical rules
2. Identifies the stack from file extensions
3. Reads the relevant `standards/*.md` file
4. Checks `learnings/*.md` for known patterns
5. Analyzes the code against 6 dimensions

---

## Exercise 3: Smart Commit (`/commit`)

```
/commit
```

This command:
1. **Scans for secrets** — Runs gitleaks on staged files. Blocks if secrets found.
2. **Analyzes changes** — Reads `git diff` to understand what changed.
3. **Generates commit message** — Follows Conventional Commits format.
4. **Creates the commit** — Atomic, logically grouped.

Example output:
```
feat(auth): add JWT token refresh endpoint
```

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

---

## Exercise 4: Generate Tests (`/test`)

Point it at a file to generate tests:

```
/test src/services/UserService.cs
```

Or run existing tests:

```
/test run
```

Claude will:
1. Detect your test framework (NUnit, Vitest, pytest)
2. Read the file to understand the public API
3. Generate tests covering happy path and error paths
4. Run the tests and report results

---

## Exercise 5: Create a PR (`/pr`)

```
/pr
```

This generates a well-structured pull request:

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

## Exercise 6: Fix Issues (`/fix`)

If tests or the build fails:

```
/fix tests
/fix build
/fix lint
```

Claude will:
1. Run the failing command
2. Read the error output
3. Identify the root cause
4. Apply targeted fixes
5. Re-run to verify

---

## Key Takeaways

- Commands follow a consistent pattern: analyze → act → verify
- Secret scanning happens automatically on `/commit`
- All commands reference `standards/*.md` for project conventions
- All commands check `learnings/*.md` for known patterns

## Next

→ [Module 3: Standards & Learnings](03-standards-and-learnings.md)
