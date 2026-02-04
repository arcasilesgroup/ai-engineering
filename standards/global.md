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

---

## Error Handling

### Do

- ✅ Use Result pattern where available (no exceptions for flow control)
- ✅ Return meaningful error messages to clients
- ✅ Log errors with context (correlation ID, user context)
- ✅ Map errors to appropriate HTTP status codes

### Don't

- ❌ Use exceptions for flow control
- ❌ Expose stack traces in production
- ❌ Silently swallow exceptions
- ❌ Return generic "something went wrong" messages

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
✅ Structured logging
   logger.LogInformation("Processed {Count} items in {Duration}ms", count, duration);

❌ String concatenation
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
