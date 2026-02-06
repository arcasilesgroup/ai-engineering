# Copilot Integration

> Extend framework standards to GitHub Copilot users.

## Overview

While Claude Code gets full framework support (skills, agents, hooks), GitHub Copilot users can benefit from the standards through dedicated instruction files.

## How It Works

The framework includes Copilot-specific files:

| File | Purpose |
|------|---------|
| `.github/copilot-instructions.md` | Global instructions for Copilot |
| `.github/instructions/*.md` | File-pattern-specific instructions |

## copilot-instructions.md

**Location:** `.github/copilot-instructions.md`

This file provides global context to Copilot:

```markdown
# Project Instructions for GitHub Copilot

## Project Overview
[Brief description of the project]

## Technology Stack
- Backend: .NET 8, ASP.NET Core
- Frontend: React 18, TypeScript
- Infrastructure: Azure, Terraform

## Coding Standards

### .NET
- Use Result<T> pattern for error handling
- Never access Result.Value without checking IsError
- Use async/await throughout
- Constructor injection for DI

### TypeScript
- Functional components only
- TypeScript strict mode
- No any types

### Security
- Never hardcode secrets
- Validate all inputs
- Use parameterized queries

## Patterns
[Key patterns from your standards]

## Testing
- Minimum 80% coverage
- Test naming: MethodName_Scenario_ExpectedResult
```

## Pattern-Specific Instructions

**Location:** `.github/instructions/`

Create files that match patterns for specific guidance:

### For Controllers

**File:** `.github/instructions/controllers.md`

```markdown
---
applyTo: "**/Controllers/**/*.cs"
---

# Controller Standards

## Route Conventions
- Use attribute routing: [Route("api/v1/[controller]")]
- HTTP methods as attributes: [HttpGet], [HttpPost]

## Response Handling
- Return IActionResult or ActionResult<T>
- Map errors to appropriate HTTP status codes
- Never expose internal errors

## Example
```csharp
[HttpGet("{id}")]
public async Task<ActionResult<UserDto>> GetUser(Guid id)
{
    var result = await _userService.GetUser(id);

    if (result.IsError)
        return result.FirstError.ToActionResult();

    return Ok(result.Value);
}
```

### For Services

**File:** `.github/instructions/services.md`

```markdown
---
applyTo: "**/Services/**/*.cs"
---

# Service Standards

## Return Types
- Always return Result<T> or Result
- Never throw exceptions for flow control

## Error Handling
- Use Error.NotFound, Error.Validation, etc.
- Include descriptive error messages

## Example
```csharp
public async Task<Result<User>> GetUser(Guid id)
{
    var user = await _repository.GetAsync(id);

    if (user == null)
        return Error.NotFound($"User {id} not found");

    return user;
}
```

### For Tests

**File:** `.github/instructions/tests.md`

```markdown
---
applyTo: "**/Tests/**/*.cs"
---

# Test Standards

## Naming
- MethodName_Scenario_ExpectedResult
- Example: GetUser_WithInvalidId_ReturnsNotFound

## Structure
- Arrange, Act, Assert (AAA)
- One assertion per test (when practical)

## Mocking
- Use NSubstitute or Moq
- Mock at boundaries (repositories, external services)
```

## Claude Code vs Copilot

| Capability | Claude Code | Copilot |
|-----------|:-----------:|:-------:|
| Skills (`/ship`, `/review`, etc.) | Full | No |
| Agents (verify-app, etc.) | Full | No |
| Hooks (auto-format, guards) | Full | No |
| Terminal execution | Full | No |
| Standards enforcement | Active | Passive |
| Multi-file awareness | Full | Limited |

**Key difference:** Copilot uses instructions as suggestions; Claude Code actively enforces them.

## Best Practices

### Keep Instructions Focused

```markdown
# Good: Specific, actionable
Use Result<T> for all service method return types.
Check IsError before accessing Value.

# Bad: Too general
Follow best practices for error handling.
```

### Include Examples

```markdown
## Correct Pattern
```csharp
if (result.IsError)
    return result.FirstError;
var user = result.Value;
```

## Incorrect Pattern
```csharp
var user = result.Value; // Might fail!
```

### Reference Standards

```markdown
For full details, see:
- standards/dotnet.md
- standards/security.md
```

## Updating Copilot Instructions

When you update `standards/*.md`, also update:
1. `.github/copilot-instructions.md`
2. Relevant `.github/instructions/*.md` files

The `/document` skill can help generate these.

---
**See also:** [Standards Overview](Standards-Overview) | [GitHub Actions](CI-CD-GitHub-Actions)
