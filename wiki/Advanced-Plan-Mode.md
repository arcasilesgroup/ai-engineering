# Plan Mode

> Design implementation approaches before writing code.

## What Is Plan Mode?

Plan mode is a workflow where Claude explores the codebase and designs an implementation approach before writing any code. It's useful for:

- Multi-file changes
- Architectural decisions
- New features with unclear scope
- Refactoring existing code

## When to Use Plan Mode

| Scenario | Use Plan Mode? |
|----------|----------------|
| Simple bug fix | No |
| Adding a single endpoint | Maybe |
| New feature (3+ files) | Yes |
| Architectural change | Yes |
| Refactoring | Yes |
| Unclear requirements | Yes |

## How to Enter Plan Mode

Ask Claude to plan before implementing:

```
Help me add a caching layer to the API. Enter plan mode.
```

Or explicitly:

```
I need to implement user authentication. Don't write code yet -
first create a plan that we can review.
```

## Plan Mode Workflow

### 1. Explore

Claude explores the codebase:
- Reads relevant files
- Identifies existing patterns
- Checks standards and learnings

### 2. Design

Claude creates an implementation plan:
- Files to create/modify
- Patterns to follow
- Dependencies needed
- Testing approach

### 3. Present Options (High Stakes)

For significant decisions, Claude presents two options:

```markdown
### Option A: Use IDistributedCache
**Pros:** Standard .NET pattern, easy testing
**Cons:** Limited Redis features
**Risk:** Low
**Files:** 5

### Option B: Direct StackExchange.Redis
**Pros:** Full Redis feature set
**Cons:** More code, harder testing
**Risk:** Medium
**Files:** 8

**Recommendation:** Option A because we only need simple caching.
```

### 4. Await Approval

Claude waits for you to:
- Approve the plan
- Request modifications
- Choose between options

### 5. Implement

After approval, Claude implements the plan step by step.

## Example Plan

```markdown
## Implementation Plan: Redis Caching Layer

### Context
Add caching to reduce database load for frequently accessed data.

### Existing Patterns Found
1. `src/services/CacheService.cs` — In-memory cache
2. `src/providers/UserProvider.cs` — Cache-aside pattern

### Files to Create
1. `src/infrastructure/RedisCacheService.cs` — Redis implementation
2. `src/config/RedisConfig.cs` — Configuration class
3. `tests/infrastructure/RedisCacheServiceTests.cs` — Unit tests

### Files to Modify
1. `src/providers/UserProvider.cs` — Add cache-aside
2. `src/providers/ProductProvider.cs` — Add cache-aside
3. `src/Startup.cs` — Register Redis services
4. `appsettings.json` — Add Redis connection

### Dependencies
- Microsoft.Extensions.Caching.StackExchangeRedis

### Testing Plan
- Unit tests with mocked IDistributedCache
- Integration tests with Redis test container

### Risks
- Cache invalidation bugs → Use short TTL initially
- Redis failures → Circuit breaker pattern

### Steps
1. Create configuration class
2. Implement cache service
3. Register in DI
4. Add to UserProvider
5. Add to ProductProvider
6. Write tests
7. Update documentation

Shall I proceed with this plan?
```

## Plan Mode Tips

### Be Specific About Scope

```
# Good
Plan how to add JWT authentication with refresh tokens.
The user model already exists. Focus on AuthController and TokenService.

# Bad
Plan authentication.
```

### Request Reconnaissance

```
Before planning, search for existing authentication patterns in this codebase.
Check standards/security.md for requirements.
```

### Iterate on the Plan

```
The plan looks good, but:
1. Use sliding expiration instead of absolute
2. Add rate limiting to the refresh endpoint
Update the plan with these changes.
```

## Combining with Agents

Use `code-architect` agent for planning:

```
Run the code-architect agent to design the caching implementation.
```

The agent provides the same planning capabilities but runs autonomously.

## Exiting Plan Mode

Plan mode ends when:
- You approve the plan and Claude implements it
- You ask Claude to implement without further planning
- You cancel and start a new task

---
**See also:** [code-architect Agent](Agents-code-architect) | [Parallel Work](Advanced-Parallel-Work)
