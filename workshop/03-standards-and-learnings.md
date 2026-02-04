# Module 3: Standards & Learnings

## Overview

Understand how standards enforce consistency and how learnings accumulate knowledge across sessions.

---

## Standards

Standards files live in `standards/` and define the rules AI agents follow when generating or reviewing code.

### Structure

```
standards/
├── global.md         # Universal rules (all stacks)
├── dotnet.md         # .NET-specific conventions
├── typescript.md     # TypeScript/React conventions
├── python.md         # Python conventions
├── terraform.md      # Infrastructure as Code
├── security.md       # OWASP, secret scanning, compliance
├── quality-gates.md  # SonarQube thresholds, linter config
├── cicd.md           # GitHub Actions + Azure Pipelines
├── testing.md        # Cross-stack testing philosophy
└── api-design.md     # REST API conventions
```

### How Standards Are Used

When Claude executes a command like `/review` or `/test`:

1. It reads `CLAUDE.md` which lists all available standards.
2. It detects the stack from file extensions (`.cs` → dotnet, `.ts` → typescript).
3. It reads the relevant `standards/*.md` file.
4. It applies those rules to the code.

### Example: .NET Naming Convention

From `standards/dotnet.md`:

```markdown
## Naming Conventions
| Element | Convention | Example |
|---------|-----------|---------|
| Class | PascalCase | `UserService` |
| Interface | I + PascalCase | `IUserService` |
| Method | PascalCase + Async suffix | `GetUserAsync` |
| Private field | _camelCase | `_userRepository` |
| Parameter | camelCase | `userId` |
```

When Claude reviews a file, it checks these conventions and flags violations.

### Exercise: Read a Standard

Open any standard file and read through it:

```
Read standards/dotnet.md
```

Note how each section includes:
- **Rules** with clear do/don't guidance
- **Code examples** showing correct patterns
- **Anti-pattern tables** showing what NOT to do

---

## Learnings

Learnings are accumulated knowledge — patterns, gotchas, and tips discovered during development. They persist across AI sessions.

### Structure

```
learnings/
├── global.md         # Cross-stack learnings
├── dotnet.md         # .NET-specific learnings
├── typescript.md     # TypeScript learnings
└── terraform.md      # Terraform learnings
```

### How Learnings Work

1. **Discovery**: You encounter a pattern or gotcha during development.
2. **Record**: Use `/learn` to save it.
3. **Reuse**: Future AI sessions read `learnings/*.md` and apply the knowledge.

### Example Learning

```markdown
### Bind Requires Explicit Type Parameter

**Context:** Using Result pattern's Bind method in .NET
**Learning:** Always specify the type parameter explicitly: `Bind<T>()` not just `Bind()`
**Example:**
// Good
result.Bind<UserResponse>(user => MapToResponse(user))

// Bad - causes CS0411 compiler error
result.Bind(user => MapToResponse(user))
```

### Exercise: Record a Learning

```
/learn dotnet: When using HttpClient with DelegatingHandler, register the handler as Transient, not Scoped
```

This adds the learning to `learnings/dotnet.md` for future sessions.

---

## Key Takeaways

- Standards define the rules. Learnings capture experience.
- Both are plain markdown files — edit them directly.
- AI agents read both automatically when executing commands.
- Use `/learn` to grow the knowledge base over time.

## Next

→ [Module 4: Agents](04-agents.md)
