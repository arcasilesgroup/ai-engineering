# verify-app Agent

> The "finisher" — build, test, lint, security, and quality verification in one pass.

## Purpose

Verify the entire application in a single pass. Use this agent before creating PRs or after significant changes.

## When to Use

- Before creating a pull request
- After completing a feature
- Before merging to main
- As a final quality check

## How to Invoke

```
Run the verify-app agent.
```

```
Dispatch verify-app to check everything before I create the PR.
```

## What It Does

### 1. Detect Stacks

Checks for project files to determine which stacks are present:
- `.sln` or `.csproj` → .NET
- `package.json` → TypeScript/JavaScript
- `pyproject.toml` or `requirements.txt` → Python
- `*.tf` files → Terraform

### 2. Build

Runs the appropriate build command:

| Stack | Command |
|-------|---------|
| .NET | `dotnet build --no-restore` |
| TypeScript | `npm run build` or `npx tsc --noEmit` |
| Python | `python -m py_compile` on changed files |
| Terraform | `terraform validate` |

### 3. Tests with Coverage

Runs tests and collects coverage:

| Stack | Command |
|-------|---------|
| .NET | `dotnet test --no-build --collect:"XPlat Code Coverage"` |
| TypeScript | `npm test -- --coverage` |
| Python | `pytest --cov --cov-report=term-missing` |

### 4. Lint

Runs stack-appropriate linters:

| Stack | Command |
|-------|---------|
| .NET | `dotnet format --verify-no-changes` |
| TypeScript | `npx eslint . --ext .ts,.tsx` |
| Python | `ruff check .` |
| Terraform | `terraform fmt -check` |

### 5. Secret Scan

- Runs `gitleaks detect --source . --no-git --verbose` if available
- Falls back to pattern scanning for API keys, tokens, credentials

### 6. Dependency Audit

| Stack | Command |
|-------|---------|
| .NET | `dotnet list package --vulnerable` |
| TypeScript | `npm audit` |
| Python | `pip audit` |

### 7. Code Duplication Check

Scans for duplicated code blocks (> 10 identical lines).

## Output Format

```markdown
## Verification Report

**Verdict:** PASS | FAIL

### Results
| Check | Status | Details |
|-------|--------|---------|
| Build | PASS | Compiled successfully |
| Tests | PASS | 94 passed, 0 failed |
| Coverage | PASS | 84% (threshold: 80%) |
| Lint | PASS | No issues |
| Secrets | PASS | No findings |
| Dependencies | PASS | No vulnerabilities |
| Duplication | PASS | 1.8% (threshold: 3%) |

### Failures (if any)
1. **[check:file:line]** Description of the issue
```

## Constraints

- Does NOT modify source files
- Does NOT install or restore packages
- Does NOT skip any check — reports failures, doesn't hide them
- Reports failures with file paths and error messages

## Example Run

```
> Run verify-app

Detecting stacks...
- .NET detected (OrderService.sln)
- TypeScript detected (package.json)

Running build...
✓ dotnet build: Success
✓ npm run build: Success

Running tests...
✓ dotnet test: 67 passed, 0 failed
✓ npm test: 43 passed, 0 failed

Coverage: 86% (.NET), 82% (TypeScript)

Running lint...
✓ dotnet format: No changes needed
✓ eslint: No issues

Scanning for secrets...
✓ gitleaks: No findings

Auditing dependencies...
✓ dotnet list package: No vulnerabilities
✓ npm audit: No vulnerabilities

## Verification Report

**Verdict:** PASS

All checks passed. Ready for PR.
```

---
**See also:** [Agents Overview](Agents-Overview) | [Quality Gates](Standards-Quality-Gates)
