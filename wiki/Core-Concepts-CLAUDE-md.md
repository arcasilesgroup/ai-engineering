# Understanding CLAUDE.md

> The main entry point that AI agents read to understand your project.

## What Is CLAUDE.md?

`CLAUDE.md` is the master configuration file for Claude Code. When you open a project with Claude Code, it automatically reads this file to understand:

- Your project's identity and purpose
- Coding standards and rules
- Available skills and agents
- Critical rules that must never be broken

## Structure

The file is divided into two sections:

### Framework Section (Auto-updated)

```markdown
<!-- BEGIN:AI-FRAMEWORK:v2.0.0 -->
# AI Engineering Framework

## Identity
## Architecture
## Technology Stack
## Critical Rules
## Verification Protocol
## Skills
## Agents
<!-- END:AI-FRAMEWORK -->
```

This section is managed by the framework and updated via `install.sh --update`.

### Team Section (Your Content)

```markdown
<!-- BEGIN:TEAM -->
## Project Overview
{{PROJECT_DESCRIPTION}}

<!-- Add team-specific rules below -->
<!-- END:TEAM -->
```

This section is yours. It's never overwritten by framework updates.

## Key Sections Explained

### Identity

Establishes who Claude is when working in your project:

```markdown
## Identity

You are an expert software engineer. You write production-ready code
that follows established patterns, prioritizes security, and includes tests.
```

### Critical Rules

Things that must NEVER happen:

```markdown
## Critical Rules

**NEVER:**
1. Access `Result.Value` without checking `Result.IsError` first
2. Hardcode secrets, tokens, or credentials in code
3. Use exceptions for flow control in .NET code
4. Commit code without tests for new functionality

**ALWAYS:**
1. Validate inputs at system boundaries
2. Use structured logging (never string concatenation)
3. Follow existing patterns in the codebase
```

### Verification Protocol

Exact commands to verify code works:

```markdown
## Verification Protocol

### .NET
dotnet build --no-restore
dotnet test --no-build --verbosity normal
dotnet format --verify-no-changes

### TypeScript
npx tsc --noEmit
npm test
npx eslint .
```

### Skills and Agents

Lists what's available for use:

```markdown
## Skills
- `/commit` - Stage + conventional commit
- `/review` - Code review against standards
- `/test` - Generate and run tests

## Agents
- **verify-app** - Build + test + lint + security
- **code-architect** - Design before implementing
```

## Customizing CLAUDE.md

### Adding Team Rules

Add your rules in the TEAM section:

```markdown
<!-- BEGIN:TEAM -->
## Project: MyProject

## Custom Rules
- All API endpoints must log request/response
- Database queries must use parameterized queries
- Feature flags must be documented in context/features.md
<!-- END:TEAM -->
```

### Adding Danger Zones

Extend the danger zones for your project:

```markdown
## Additional Danger Zones
- **Stripe Integration** - Always use idempotency keys
- **Email Service** - Never send to real addresses in dev
```

## Migration Between Versions

When you run `install.sh --update`:

1. The framework section is replaced with the new version
2. Your team section is preserved exactly as-is
3. A backup is created before any changes

If you have an old CLAUDE.md without section markers, run:

```
/migrate-claude-md
```

---
**See also:** [Three-Layer Architecture](Core-Concepts-Three-Layer-Architecture) | [Updating](Installation-Updating)
