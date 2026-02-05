# code-architect Agent

> Designs implementation approaches by analyzing codebase patterns and proposing options.

## Purpose

Analyze the codebase and design an implementation approach before writing code. Ensures changes follow existing patterns and considers trade-offs.

## When to Use

- Before implementing a new feature
- When making architectural decisions
- For changes affecting multiple files
- When entering a "danger zone" area

## How to Invoke

```
Use the code-architect agent to design the caching layer.
```

```
Run code-architect to plan how to add the new payment provider.
```

## What It Does

### 1. Understand the Request

- Parses the feature or change description
- Identifies the affected domain area and stacks

### 2. Reconnaissance

- Reads relevant `standards/*.md` files
- Reads relevant `learnings/*.md` files
- Searches for 2+ existing examples of similar patterns
- Identifies the architectural layer(s) involved

### 3. Analyze Impact

- Lists all files that would need to be created or modified
- Identifies dependencies and downstream consumers
- Assesses risk level (low/medium/high)
- Flags any Danger Zone areas

### 4. Propose Options

For significant decisions, proposes two approaches:

```markdown
### Option A: [Name]
**Approach:** [Description]
**Pros:**
- [Pro 1]
- [Pro 2]
**Cons:**
- [Con 1]
**Risk:** Low/Medium/High
**Files affected:** X
**Reversibility:** Easy/Moderate/Difficult

### Option B: [Name]
**Approach:** [Description]
**Pros:**
- [Pro 1]
**Cons:**
- [Con 1]
- [Con 2]
**Risk:** Low/Medium/High
**Files affected:** X
**Reversibility:** Easy/Moderate/Difficult

### Recommendation
[Which option and why]
```

### 5. Generate Implementation Plan

```markdown
## Implementation Plan

### Files to Create
1. [path] — [purpose]

### Files to Modify
1. [path:area] — [what changes]

### Dependencies
- [External packages or internal modules needed]

### Testing Plan
- [What tests to write]

### Risks and Mitigations
- [Risk] → [Mitigation]
```

## Output Format

```markdown
## Architecture Analysis: [Feature Name]

### Context
[What problem we're solving]

### Existing Patterns Found
1. `src/providers/OrderProvider.cs` — Similar provider pattern
2. `src/services/PaymentService.cs` — Similar external integration

### Danger Zones Identified
- [ ] Payment/Billing — Requires idempotency

### Option A: [Name]
...

### Option B: [Name]
...

### Recommendation
Option A because [reasons].

## Implementation Plan
...
```

## Constraints

- Does NOT modify any files — read-only analysis
- Does NOT make implementation decisions without presenting options
- Always references existing codebase patterns
- Always checks standards and learnings before proposing

## Example Run

```
> Use code-architect to plan the Redis caching layer

## Architecture Analysis: Redis Caching Layer

### Context
Add caching to reduce database load and improve response times for frequently accessed data.

### Existing Patterns Found
1. `src/services/CacheService.cs` — In-memory cache implementation
2. `src/providers/UserProvider.cs` — Cache-aside pattern in GetUser

### Danger Zones Identified
- [ ] Configuration — Redis connection string must not be hardcoded
- [ ] API Contracts — Cached responses must match non-cached

### Option A: Distributed Cache Abstraction
**Approach:** Use IDistributedCache interface with Redis implementation
**Pros:**
- Standard .NET pattern
- Easy to swap implementations
- Built-in serialization
**Cons:**
- Less control over Redis features
**Risk:** Low
**Files affected:** 8
**Reversibility:** Easy

### Option B: Direct StackExchange.Redis
**Approach:** Direct Redis client for full feature access
**Pros:**
- Full Redis feature set (pub/sub, streams)
- Better performance for complex operations
**Cons:**
- More code to maintain
- Harder to test
**Risk:** Medium
**Files affected:** 12
**Reversibility:** Moderate

### Recommendation
Option A — We only need simple key-value caching. The standard interface is sufficient and easier to test.

## Implementation Plan

### Files to Create
1. `src/infrastructure/RedisCacheService.cs` — Redis implementation
2. `src/config/RedisConfig.cs` — Configuration class

### Files to Modify
1. `src/providers/UserProvider.cs` — Add cache-aside pattern
2. `src/providers/ProductProvider.cs` — Add cache-aside pattern
3. `src/Startup.cs` — Register Redis services
4. `appsettings.json` — Add Redis connection config

### Testing Plan
- Unit tests with mocked IDistributedCache
- Integration tests with Redis test container

### Risks and Mitigations
- Cache invalidation bugs → Use short TTL initially, add explicit invalidation
- Redis connection failures → Add fallback to database with circuit breaker
```

---
**See also:** [Agents Overview](Agents-Overview) | [Production Reliability](Core-Concepts-Production-Reliability)
