# Documentation Skills

> Skills for generating and maintaining documentation.

## /document

**Generate or update documentation.**

```
/document src/services/UserService.cs    # Document a file
/document src/controllers/               # Document a directory
/document api                            # Generate API docs
```

### What It Generates

| Target | Output |
|--------|--------|
| Class/Service | XML docs, README section |
| Controller | API endpoint documentation |
| Directory | Module README with overview |
| API | OpenAPI/Swagger spec |

### Documentation Standards

Generated docs follow project conventions from `standards/global.md`:

- **XML docs** for public APIs (.NET)
- **JSDoc** for TypeScript functions
- **Docstrings** for Python
- **README** for modules/directories

### Example: Service Documentation

```csharp
/// <summary>
/// Manages user lifecycle including registration, authentication, and profile updates.
/// </summary>
/// <remarks>
/// <para>
/// This service follows the Result pattern for error handling.
/// All methods return <see cref="Result{T}"/> or <see cref="Result"/>.
/// </para>
/// <para>
/// Thread-safe: Yes (uses scoped dependencies)
/// </para>
/// </remarks>
public class UserService : IUserService
{
    /// <summary>
    /// Retrieves a user by their unique identifier.
    /// </summary>
    /// <param name="userId">The unique identifier of the user.</param>
    /// <returns>
    /// A result containing the user if found, or a NotFound error.
    /// </returns>
    /// <exception cref="ArgumentException">
    /// Thrown when <paramref name="userId"/> is empty.
    /// </exception>
    public async Task<Result<User>> GetUser(Guid userId)
```

---

## /create-adr

**Create an Architecture Decision Record.**

```
/create-adr "Use Redis for session storage"
/create-adr "Switch from REST to GraphQL"
```

### What's an ADR?

Architecture Decision Records document significant architectural decisions:
- **What** was decided
- **Why** it was decided
- **Alternatives** considered
- **Consequences** of the decision

### ADR Template

```markdown
# ADR-NNN: [Title]

**Status:** Proposed | Accepted | Deprecated | Superseded
**Date:** YYYY-MM-DD
**Deciders:** [Names]

## Context

[What is the issue that we're seeing that is motivating this decision?]

## Decision

[What is the change that we're proposing?]

## Alternatives Considered

### Option A: [Name]
- Pros: [list]
- Cons: [list]

### Option B: [Name]
- Pros: [list]
- Cons: [list]

## Consequences

### Positive
- [Consequence 1]

### Negative
- [Consequence 1]

### Risks
- [Risk 1] → [Mitigation]

## References
- [Link to relevant documentation]
```

### ADR Location

ADRs are stored in `context/decisions/`:

```
context/
└── decisions/
    ├── 001-use-result-pattern.md
    ├── 002-adopt-vertical-slice-architecture.md
    └── 003-use-redis-for-sessions.md
```

---

## /learn

**Record a learning for future sessions.**

```
/learn "Azure Service Bus requires sessions for ordered message processing"
/learn
```

### What Are Learnings?

Learnings are accumulated knowledge that helps Claude (and your team) avoid repeating mistakes. They're stored in `learnings/*.md`.

### Learning Structure

```markdown
## [Topic]

[Description of what was learned]

- **Discovered:** YYYY-MM-DD
- **Context:** [What triggered this learning]
- **Impact:** [What could go wrong without this knowledge]
```

### Example Learnings

**learnings/dotnet.md:**
```markdown
## Result Pattern - Never Access Value Without IsError Check

Always check `Result.IsError` before accessing `Result.Value`.
Accessing Value when IsError is true causes undefined behavior.

- Discovered: 2024-03-15
- Context: Production bug where null Value caused NullReferenceException
- Impact: Runtime crashes, data corruption

```csharp
// WRONG
var user = result.Value; // Might be null/undefined!

// CORRECT
if (result.IsError)
{
    return result.Errors;
}
var user = result.Value; // Safe
```

### Learnings by Stack

| File | Content |
|------|---------|
| `learnings/global.md` | Cross-cutting learnings |
| `learnings/dotnet.md` | .NET-specific learnings |
| `learnings/typescript.md` | TypeScript learnings |
| `learnings/terraform.md` | Terraform learnings |

### How Learnings Are Used

1. Claude reads learnings at session start
2. When working on related code, Claude references relevant learnings
3. `/review` skill checks code against known learnings
4. Team knowledge accumulates over time

---

## /blast-radius

**Analyze the impact of proposed changes.**

```
/blast-radius
/blast-radius src/services/UserService.cs
```

### What It Analyzes

1. **Direct dependencies** — What uses this code?
2. **Indirect dependencies** — What uses the things that use this code?
3. **Test coverage** — What tests cover this code?
4. **API surface** — Does this change the public API?
5. **Database** — Does this affect data models?

### Example Output

```markdown
## Blast Radius: UserService.cs

### Direct Dependencies (5 files)
- `UserController.cs` — calls GetUser, CreateUser
- `AuthService.cs` — calls ValidateUser
- `OrderService.cs` — calls GetUser
- `NotificationService.cs` — calls GetUserEmail
- `ReportService.cs` — calls GetUserStats

### Indirect Dependencies (12 files)
- All controllers that use OrderService
- Background jobs that use NotificationService

### Test Coverage
- `UserServiceTests.cs` — 94% coverage
- `UserControllerTests.cs` — 87% coverage
- `AuthServiceTests.cs` — 91% coverage

### Risk Assessment
- **API Change:** No (internal only)
- **Database Change:** No
- **Breaking Change:** No

**Recommendation:** Safe to proceed. Run full test suite after changes.
```

---
**See also:** [Daily Workflow Skills](Skills-Daily-Workflow) | [Standards Overview](Standards-Overview)
