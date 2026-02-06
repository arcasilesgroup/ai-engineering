# Global Standards

> Cross-stack rules applicable to all code regardless of technology.

## Core Principles

### 1. Security First

> See also: CLAUDE.md Critical Rules #2, standards/security.md Section 2

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

### Branching Strategy

Trunk-based development with short-lived feature branches. All work branches from the default branch and merges back via Pull Request.

```
default branch ──────────────────────────────────────────►
  │                              ▲
  └── feature/add-login ─────────┘  (PR + merge)
  │                              ▲
  └── fix/auth-timeout ──────────┘  (PR + merge)
  │                                             ▲
  └── release/v1.2.0 ───────────────────────────┘  (PR + merge)
```

**Rules:**
- Always branch from the default branch, unless explicitly told otherwise
- Always PR to the default branch, unless explicitly told otherwise
- Keep branches short-lived (< 1 week ideally, < 2 weeks maximum)
- One logical change per branch
- Use `/git branch` to create branches with proper naming and base

### Compliance Branches

Protected branches that require PRs, have policy governance, and are never auto-deleted:

| Pattern | Purpose |
|---------|---------|
| `main` / `master` | Production (default branch) |
| `develop` | Integration branch |
| `dev/*` | Development environment branches |
| `release/*` | Release preparation |
| `hotfix/*` | Production emergency fixes |

**Rules for compliance branches:**
- No direct push — always via Pull Request
- Never auto-deleted by cleanup tools or agents
- Health checks verify feature branches are merged into the appropriate compliance branch
- Branching from a compliance branch (e.g., `develop`, `release/v1.0`) is valid when explicitly required

### Branch Naming

```
feature/    # New functionality
fix/        # Bug fixes (alias: bugfix/)
bugfix/     # Bug fixes
hotfix/     # Production emergency fixes
release/    # Release preparation
chore/      # Maintenance tasks
docs/       # Documentation updates
```

**Format:** `<prefix>/<short-description>` or `<prefix>/<ticket-id>-<short-description>`

**Examples:**
```
feature/user-preferences
feature/GH-123-add-login
fix/AB#456-token-refresh
release/v1.2.0
hotfix/critical-auth-bypass
```

### Branch Lifecycle

1. **Create** — Branch from latest default branch (`/git branch feature/my-work`)
2. **Work** — Make commits following Conventional Commits
3. **Push** — Push to remote and create PR (`/ship pr`)
4. **Review** — Get PR reviewed and approved
5. **Merge** — Merge PR (squash or merge commit per team preference)
6. **Cleanup** — Delete branch locally and remotely (`/git cleanup`)

### Before Starting Work

Always synchronize your repository before beginning new work:

1. Fetch and prune remote references
2. Update the default branch locally
3. Clean up merged branches
4. Check for unpushed work and repository health

Use `/git` (runs sync + cleanup + health) or `/git sync` for a quick update.

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
- Target the default branch unless explicitly specified
- Link to related issues/work items (GitHub: `Closes #123`, Azure DevOps: `AB#456`)
- Include test coverage
- Request appropriate reviewers
- Auto-merge is enabled by default on PR creation (squash merge strategy)
- Use `--no-auto-merge` with `/ship pr` to create a PR without auto-merge
- Delete source branch after merge (handled automatically by platform or `git-hygiene` agent)

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
