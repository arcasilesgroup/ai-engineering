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

**Code review against standards.** For detailed review dimensions and output examples, see [Code Quality Skills - /review](Skills-Code-Quality#review).

```
/review staged
/review src/services/
/review feature-branch
```

---

## /test

**Generate and run tests.** For detailed test generation principles and examples, see [Code Quality Skills - /test](Skills-Code-Quality#test).

```
/test src/services/UserService.cs
/test run
/test coverage
```

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
4. **Checks tools** — Verifies gitleaks, CLI tools, pre-commit and pre-push hooks
5. **Reports status** — Shows what's working

### Example Output

```
## Framework Validation Report

**Status:** VALID
**Version:** 2.0.0

### Files
- [x] CLAUDE.md
- [x] .claude/settings.json
- [x] Skills: 23 found
- [x] Agents: 5 found
- [x] Hooks: 5 found (5 executable)
- [x] Standards: 10 found

### Platform
- [x] Platform: GitHub
- [x] CLI: gh installed
- [x] Auth: Authenticated

### Tools
- [x] gitleaks: installed
- [x] Pre-commit hook: installed
- [x] Pre-push hook: installed
- [x] Stack tools: configured

### Warnings
(none)

Framework is correctly installed.
```

---

## /fix

**Fix failing tests, lint errors, or build issues.** For detailed examples, see [Code Quality Skills - /fix](Skills-Code-Quality#fix).

```
/fix tests
/fix build
/fix lint
```

---
**See also:** [Code Quality Skills](Skills-Code-Quality) | [Skills Overview](Skills-Overview)
