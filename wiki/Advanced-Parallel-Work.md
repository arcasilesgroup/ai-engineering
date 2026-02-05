# Parallel Work

> Run multiple Claude Code instances simultaneously for maximum productivity.

## Overview

Running 5+ Claude Code instances in parallel is the single biggest productivity multiplier. Each instance works on a separate task while following the same standards.

## Setup

1. Open multiple terminal tabs/windows
2. Each instance reads `CLAUDE.md` and follows the same standards
3. Assign each instance a specific, independent task

## Example: Feature Development

```
Terminal 1: "Implement the UserService with GET and POST endpoints"
Terminal 2: "Write unit tests for the OrderProvider"
Terminal 3: "Update the API documentation for v2 endpoints"
Terminal 4: "Run verify-app agent to validate build, tests, and security"
Terminal 5: "Fix lint errors in the TypeScript frontend"
```

## Rules for Parallel Work

From `CLAUDE.md`:

1. **Separate files** — Each instance works on different files
2. **No overlap** — Never have two instances editing the same file
3. **Use branches** — If instances need overlapping areas, use git branches
4. **Coordinate** — Use CLAUDE.md or a shared plan file for coordination

## Coordination Patterns

### Pattern 1: File-Based Separation

Assign each instance to different directories:

```
Instance 1: src/services/
Instance 2: src/controllers/
Instance 3: src/providers/
Instance 4: tests/
Instance 5: docs/
```

### Pattern 2: Layer-Based Separation

Assign by architectural layer:

```
Instance 1: API layer (controllers, DTOs)
Instance 2: Business layer (services)
Instance 3: Data layer (providers, repositories)
Instance 4: Infrastructure (config, DI)
Instance 5: Tests and documentation
```

### Pattern 3: Feature-Based Separation

Each instance works on a complete feature slice:

```
Instance 1: User management (all layers)
Instance 2: Order processing (all layers)
Instance 3: Payment integration (all layers)
```

**Note:** This pattern requires careful coordination to avoid conflicts.

## Coordination via CLAUDE.local.md

Use `CLAUDE.local.md` to track what each instance is working on:

```markdown
## Parallel Work Session

### Instance 1 (Terminal Tab: "Services")
Working on: UserService, OrderService
Files: src/services/UserService.cs, src/services/OrderService.cs
Status: In progress

### Instance 2 (Terminal Tab: "Tests")
Working on: Unit tests for services
Files: tests/services/
Status: In progress

### Conflicts to Avoid
- Both instances need Startup.cs for DI registration
- Solution: Instance 1 handles all DI changes
```

## Merging Work

After parallel work completes:

1. **Verify each branch** — Run `verify-app` on each
2. **Merge sequentially** — Merge one at a time to main
3. **Resolve conflicts** — Use a single instance for conflict resolution
4. **Final verification** — Run `verify-app` after all merges

## Tips for Effective Parallel Work

### Do

- Assign clear, bounded tasks
- Use different git branches per instance
- Run `verify-app` after each task completes
- Keep a coordination document

### Don't

- Have two instances edit the same file
- Start dependent tasks in parallel
- Forget to merge and verify

## Example Session

```
# Terminal 1: API Development
$ claude
> Implement the OrderController with CRUD endpoints

# Terminal 2: Tests
$ claude
> Write unit tests for OrderService

# Terminal 3: Documentation
$ claude
> Update the API documentation for Order endpoints

# Terminal 4: Verification
$ claude
> Run verify-app agent on the entire codebase

# All complete, merge:
$ git checkout main
$ git merge feature/order-api
$ git merge feature/order-tests
$ git merge feature/order-docs
```

## Conflict Prevention

### Shared Files

Some files are touched by multiple features:
- `Startup.cs` / `Program.cs` (DI registration)
- `appsettings.json` (configuration)
- API documentation files

**Strategy:** Designate one instance as the "infrastructure" instance that handles all shared files.

### Database Migrations

Never create migrations in parallel. Migrations must be sequential.

**Strategy:** Create migrations in a final consolidation step after features are complete.

---
**See also:** [Plan Mode](Advanced-Plan-Mode) | [Agents Overview](Agents-Overview)
