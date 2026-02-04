# Global Standards

> Cross-stack rules applicable to all code regardless of technology.

## Core Principles

### 1. Security First

- **Never hardcode secrets**, tokens, or credentials
- Use environment variables or secret managers (Azure Key Vault)
- Validate all inputs at system boundaries
- Follow principle of least privilege
- Log security events, never log sensitive data

### 2. Quality by Design

- Write tests alongside code, not after
- Prefer compile-time safety over runtime checks
- Use strong typing; avoid `any`, `dynamic`, `object`
- Document public APIs with examples
- Handle errors explicitly, never silently swallow

### 3. Consistency

- Follow existing patterns in the codebase
- Use project-specific naming conventions
- Maintain consistent error handling across layers
- One way to do things, not many

### 4. Maintainability

- Prefer explicit over implicit
- Keep functions/methods focused (Single Responsibility)
- Avoid deep nesting; use early returns (Guard Clauses)
- Write self-documenting code
- Comments explain "why", not "what"

---

## Universal Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Files (code) | PascalCase (.NET), kebab-case (TS/React) | `UserService.cs`, `user-service.ts` |
| Files (config) | kebab-case | `app-settings.json` |
| Directories | kebab-case or PascalCase (match project) | `src/`, `Controllers/` |
| Constants | UPPER_SNAKE_CASE or PascalCase | `MAX_RETRIES`, `DefaultTimeout` |
| Scripts | kebab-case with extension | `deploy-app.sh`, `setup-env.ps1` |

---

## Error Handling

### Do

- Use Result pattern where available (no exceptions for flow control)
- Return meaningful error messages to clients
- Log errors with context (correlation ID, user context)
- Map errors to appropriate HTTP status codes

### Don't

- Use exceptions for flow control
- Expose stack traces in production
- Silently swallow exceptions
- Return generic "something went wrong" messages

---

## Logging

### Levels

| Level | Use For | Example |
|-------|---------|---------|
| `Debug` | Development details | Variable values, flow tracing |
| `Information` | Business events | User logged in, order created |
| `Warning` | Recoverable issues | Retry attempted, cache miss |
| `Error` | Failures requiring attention | Service unavailable, validation failed |
| `Critical` | System-level failures | Database down, out of memory |

### Best Practices

```
Good: Structured logging
  logger.LogInformation("Processed {Count} items in {Duration}ms", count, duration);

Bad: String concatenation
  logger.LogInformation("Processed " + count + " items");
```

- Include correlation IDs for request tracing
- Never log sensitive data (passwords, tokens, PII)
- Use appropriate log levels

---

## Git Conventions

### Branch Naming

```
feature/    # New functionality
bugfix/     # Bug fixes
hotfix/     # Production emergency fixes
chore/      # Maintenance tasks
docs/       # Documentation updates
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples:**
```
feat(api): add endpoint for user preferences
fix(auth): resolve token refresh race condition
docs: update API documentation for v2 endpoints
```

### Pull Requests

- Clear, descriptive title
- Link to related issues
- Include test coverage
- Request appropriate reviewers

---

## Code Review Checklist

- [ ] Code follows project style guidelines
- [ ] Tests are included and passing
- [ ] No hardcoded secrets or credentials
- [ ] Error handling is appropriate
- [ ] Logging is meaningful and at correct levels
- [ ] Documentation is updated if needed
- [ ] No obvious security vulnerabilities
- [ ] Performance considerations addressed

---

## Scripting (Bash)

Every Bash script must start with strict mode and a usage comment:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Description: Deploy the application to the target environment
# Usage: ./deploy-app.sh <environment>
```

### Rules

- Always quote variables: `"${my_var}"` not `$my_var`
- Use `[[ ]]` for conditionals, not `[ ]`
- Prefer functions over inline logic for anything beyond trivial scripts
- Run `shellcheck` on all scripts before committing
- Use `readonly` for constants and `local` for function variables

### Good / Bad

```bash
# Good
deploy() {
  local -r target="${1:?Error: target environment required}"
  echo "Deploying to ${target}..."
}

# Bad
echo "Deploying to $1..."
```

---

## Scripting (PowerShell)

Every PowerShell script must use strict mode and a param block:

```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
    [Parameter(Mandatory)]
    [string]$Environment
)
```

### Rules

- Use `Write-Output` for data, not `Write-Host` (Write-Host bypasses the pipeline)
- Use `try/catch/finally` for error handling, not `$?` checks
- Use approved verbs for function names (`Get-`, `Set-`, `New-`, `Remove-`)
- Include comment-based help for every exported function

### Good / Bad

```powershell
# Good
function Get-DeploymentStatus {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$ServiceName
    )
    try {
        $status = Get-Service -Name $ServiceName
        Write-Output $status
    }
    catch {
        Write-Error "Failed to query service: $_"
    }
}

# Bad
function check($s) {
    Write-Host (Get-Service $s).Status
}
```

---

## YAML Conventions

### Formatting

- Use 2-space indentation (never tabs)
- Quote strings that contain special characters (`:`, `{`, `}`, `#`, `*`, `&`)
- Use anchors and aliases to avoid repetition

```yaml
# Good: anchor for shared config
defaults: &defaults
  timeout: 30
  retries: 3

service-a:
  <<: *defaults
  port: 8080

service-b:
  <<: *defaults
  port: 8081
```

### Rules

- One blank line between top-level blocks
- Keep files under 200 lines; split into includes when they grow
- Use comments to explain non-obvious values
- Boolean values: use `true` / `false`, not `yes` / `no`
- Validate with a linter (e.g., `yamllint`) before committing

---

## Documentation

### In-code Comments

Comments explain **why**, not **what**. The code already shows what it does.

```python
# Good: explains the business reason
# Retry up to 3 times because the upstream auth service
# occasionally drops connections during deployments.
for attempt in range(3):
    ...

# Bad: restates the code
# Loop 3 times
for attempt in range(3):
    ...
```

### Required Documentation

| Artifact | Location | Purpose |
|----------|----------|---------|
| README | Root of every service / package | Setup, usage, architecture overview |
| ADR | `docs/adr/` directory | Record architectural decisions and rationale |
| CHANGELOG | Root of every service / package | Track notable changes per release |

### Architecture Decision Records (ADRs)

Use the following template for every significant technical decision:

```
# ADR-NNNN: <Title>

## Status
Accepted | Superseded | Deprecated

## Context
What is the issue or requirement that motivates this decision?

## Decision
What is the change we are making?

## Consequences
What trade-offs and impacts does this decision introduce?
```

- Number ADRs sequentially (`ADR-0001`, `ADR-0002`)
- Never delete an ADR; mark it as Superseded and link to the replacement
- Keep each ADR focused on a single decision
